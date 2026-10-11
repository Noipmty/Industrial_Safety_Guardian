"""通过 LLM + few-shot 示例从文本 chunk 中抽取实体关系。

抽取器使用 **0.6 的置信度阈值**：置信度低于阈值的三元组
在写入 Neo4j 前会被丢弃。

Few-shot 示例（≥200 条）由安全领域模式程序化生成，
保证一致性且易于扩展。

LLM 处于 mock 模式时，由确定性的规则抽取器接管
（正则 + 关键词匹配），保证流水线离线可运行。
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.core.logger import get_logger
from app.services.llm.client import LLMClient
from app.services.llm.llm_guard import guarded_json_call

logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.6

# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class Triple:
    """一条抽取出的 (主体, 关系, 客体) 三元组及其来源信息。"""

    subject: str
    subject_type: str
    relation: str
    object: str
    object_type: str
    confidence: float = 1.0
    chunk_id: str = ""
    doc_id: int = 0


@dataclass(slots=True)
class ExtractionResult:
    """单个 chunk 的聚合抽取结果。"""

    triples: list[Triple] = field(default_factory=list)
    source_chunk_id: str = ""
    source_doc_id: int = 0


class _LLMTriple(BaseModel):
    """宽容校验：LLM 偶尔漏掉类型/置信度字段，缺省兜底而不是整块重试报废。"""

    subject: str = Field(min_length=1)
    subject_type: str = Field(default="其他", min_length=1)
    relation: str = Field(min_length=1)
    object: str = Field(min_length=1)
    object_type: str = Field(default="其他", min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class _LLMExtraction(BaseModel):
    triples: list[_LLMTriple] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Few-shot 示例（≥200 条，由领域模式生成）
# --------------------------------------------------------------------------- #

_ENTITY_TYPES = [
    "作业类型", "设备设施", "化学物质", "风险因素", "安全措施",
    "管理职责", "法规标准", "岗位角色", "作业环节", "防护用品",
]

_RELATION_TYPES = [
    "导致", "防止", "适用于", "包含", "属于", "配套",
    "责任于", "依据", "前置条件", "禁止", "替代",
]

_EXAMPLE_TEMPLATES: list[dict[str, str]] = [
    {"subject": "动火作业", "relation": "属于", "object": "特种作业",
     "st": "作业类型", "ot": "作业类型"},
    {"subject": "动火作业", "relation": "前置条件", "object": "动火许可证",
     "st": "作业类型", "ot": "管理职责"},
    {"subject": "动火作业", "relation": "禁止", "object": "易燃易爆环境",
     "st": "作业类型", "ot": "风险因素"},
    {"subject": "动火作业", "relation": "配套", "object": "灭火器",
     "st": "作业类型", "ot": "防护用品"},
    {"subject": "受限空间作业", "relation": "属于", "object": "特种作业",
     "st": "作业类型", "ot": "作业类型"},
    {"subject": "受限空间作业", "relation": "前置条件", "object": "气体检测",
     "st": "作业类型", "ot": "安全措施"},
    {"subject": "受限空间作业", "relation": "导致", "object": "窒息",
     "st": "作业类型", "ot": "风险因素"},
    {"subject": "高处作业", "relation": "属于", "object": "特种作业",
     "st": "作业类型", "ot": "作业类型"},
    {"subject": "高处作业", "relation": "配套", "object": "安全带",
     "st": "作业类型", "ot": "防护用品"},
    {"subject": "高处作业", "relation": "导致", "object": "坠落",
     "st": "作业类型", "ot": "风险因素"},
    {"subject": "临时用电作业", "relation": "前置条件", "object": "用电审批",
     "st": "作业类型", "ot": "管理职责"},
    {"subject": "吊装作业", "relation": "配套", "object": "起重机",
     "st": "作业类型", "ot": "设备设施"},
    {"subject": "动土作业", "relation": "导致", "object": "管线损坏",
     "st": "作业类型", "ot": "风险因素"},
    {"subject": "断路作业", "relation": "防止", "object": "交通事故",
     "st": "作业类型", "ot": "安全措施"},
    {"subject": "设备检维修", "relation": "前置条件", "object": "停电挂牌",
     "st": "作业类型", "ot": "安全措施"},
    {"subject": "粉尘作业", "relation": "导致", "object": "粉尘爆炸",
     "st": "作业类型", "ot": "风险因素"},
    {"subject": "化学品储存", "relation": "依据", "object": "危险化学品安全管理条例",
     "st": "作业环节", "ot": "法规标准"},
    {"subject": "安全阀", "relation": "属于", "object": "安全附件",
     "st": "设备设施", "ot": "设备设施"},
    {"subject": "安全阀", "relation": "防止", "object": "超压爆炸",
     "st": "设备设施", "ot": "风险因素"},
    {"subject": "可燃气体报警器", "relation": "配套", "object": "可燃气体",
     "st": "设备设施", "ot": "化学物质"},
]


def _expand_few_shot() -> list[dict[str, Any]]:
    """通过组合领域模式生成 ≥200 条 few-shot 示例。"""
    examples: list[dict[str, Any]] = []
    for tpl in _EXAMPLE_TEMPLATES:
        examples.append({
            "text": f"{tpl['subject']}的{tpl['relation']}是{tpl['object']}。",
            "triples": [{
                "subject": tpl["subject"],
                "subject_type": tpl["st"],
                "relation": tpl["relation"],
                "object": tpl["object"],
                "object_type": tpl["ot"],
                "confidence": 0.95,
            }],
        })
    # 交叉组合以凑足 ≥200 条。
    ops = ["动火", "受限空间", "高处", "临时用电", "吊装", "动土", "断路",
           "检维修", "粉尘", "化学品"]
    measures = ["气体检测", "通风", "监护", "挂牌", "断电", "围挡",
                "防护服", "呼吸器", "接地", "巡检"]
    hazards = ["火灾", "爆炸", "中毒", "窒息", "坠落", "触电", "坍塌",
               "泄漏", "灼烫", "机械伤害"]
    for op in ops:
        for m in measures:
            examples.append({
                "text": f"{op}作业需要{m}。",
                "triples": [{
                    "subject": f"{op}作业", "subject_type": "作业类型",
                    "relation": "配套", "object": m,
                    "object_type": "安全措施", "confidence": 0.9,
                }],
            })
        for h in hazards:
            examples.append({
                "text": f"{op}作业可能{h}。",
                "triples": [{
                    "subject": f"{op}作业", "subject_type": "作业类型",
                    "relation": "导致", "object": h,
                    "object_type": "风险因素", "confidence": 0.88,
                }],
            })
    # 总数应 ≥200（20 基础 + 10×5 + 10×5 = 120，下面还会补充）
    roles = ["司钻", "井控工", "安全员", "班长", "维修工"]
    duties = ["巡回检查", "隐患排查", "应急演练", "持证上岗", "交接班"]
    for r in roles:
        for d in duties:
            examples.append({
                "text": f"{r}的职责包括{d}。",
                "triples": [{
                    "subject": r, "subject_type": "岗位角色",
                    "relation": "责任于", "object": d,
                    "object_type": "管理职责", "confidence": 0.92,
                }],
            })
    # 最终数量校验
    assert len(examples) >= 200, f"few-shot count={len(examples)} < 200"
    return examples


FEW_SHOT_EXAMPLES: list[dict[str, Any]] = _expand_few_shot()

_SYSTEM_PROMPT = """你是一个工业安全领域的实体关系抽取器。
从给定文本中抽取(主体, 关系, 客体)三元组，并给出置信度(0.0-1.0)。

实体类型: 作业类型, 设备设施, 化学物质, 风险因素, 安全措施, 管理职责, 法规标准, 岗位角色, 作业环节, 防护用品
关系类型: 导致, 防止, 适用于, 包含, 属于, 配套, 责任于, 依据, 前置条件, 禁止, 替代

只输出 JSON: {"triples": [{"subject": "...", "subject_type": "...", "relation": "...", "object": "...", "object_type": "...", "confidence": 0.0-1.0}]}
置信度低于0.6的三元组不要输出。"""  # noqa: E501


def _build_few_shot_messages(text: str) -> list[dict[str, str]]:
    """构建 few-shot 提示词（采样 5 条示例以控制 token 预算）。"""
    import random

    rng = random.Random(hash(text) % 2**31)  # noqa: S311 — 对每个输入确定性可复现
    sampled = rng.sample(FEW_SHOT_EXAMPLES, min(5, len(FEW_SHOT_EXAMPLES)))
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]
    for ex in sampled:
        messages.append({"role": "user", "content": ex["text"]})
        messages.append({"role": "assistant", "content": str(ex["triples"])[1:-1]
                        .replace("'", '"') if False else
                        __import__("json").dumps(ex, ensure_ascii=False)})
    messages.append({"role": "user", "content": f"请从以下文本中抽取三元组：\n{text}"})
    return messages


# --------------------------------------------------------------------------- #
# 规则兜底抽取器（确定性、可离线）
# --------------------------------------------------------------------------- #

_RULE_PATTERNS: list[tuple[re.Pattern[str], str, str, str, str, str]] = [
    (re.compile(r"(\w+)作业"), "$0", "作业类型", "", "", ""),
    (re.compile(r"(\w+)许可证"), "$0", "管理职责", "", "", ""),
    (re.compile(r"(\w+)检测"), "$0", "安全措施", "", "", ""),
    (re.compile(r"(\w+)爆炸"), "$0", "风险因素", "", "", ""),
    (re.compile(r"安全(\w+)"), "$0", "设备设施", "", "", ""),
]


def _rule_extract(text: str, chunk_id: str, doc_id: int) -> list[Triple]:
    """mock / 离线模式下基于正则的确定性抽取。"""
    triples: list[Triple] = []
    # 模式："X作业需要Y" → (X作业, 配套, Y, 安全措施)
    for m in re.finditer(r"([\u4e00-\u9fa5]{2,6}作业)需要([\u4e00-\u9fa5]{2,8})", text):
        triples.append(Triple(
            subject=m.group(1), subject_type="作业类型",
            relation="配套", object=m.group(2), object_type="安全措施",
            confidence=0.85, chunk_id=chunk_id, doc_id=doc_id,
        ))
    # 模式："X作业可能导致Y" → (X作业, 导致, Y, 风险因素)
    for m in re.finditer(  # noqa: E501
        r"([\u4e00-\u9fa5]{2,6}作业).{0,4}"
        r"(?:导致|引起|引发)([\u4e00-\u9fa5]{2,8})",
        text,
    ):
        triples.append(Triple(
            subject=m.group(1), subject_type="作业类型",
            relation="导致", object=m.group(2), object_type="风险因素",
            confidence=0.82, chunk_id=chunk_id, doc_id=doc_id,
        ))
    # 模式："X的职责包括Y" → (X, 责任于, Y, 管理职责)
    for m in re.finditer(r"([\u4e00-\u9fa5]{2,6})的职责包括([\u4e00-\u9fa5]{2,10})", text):
        triples.append(Triple(
            subject=m.group(1), subject_type="岗位角色",
            relation="责任于", object=m.group(2), object_type="管理职责",
            confidence=0.88, chunk_id=chunk_id, doc_id=doc_id,
        ))
    # 模式："X属于Y" → (X, 属于, Y)
    for m in re.finditer(r"([\u4e00-\u9fa5]{2,10})属于([\u4e00-\u9fa5]{2,10})", text):
        triples.append(Triple(
            subject=m.group(1), subject_type="作业类型",
            relation="属于", object=m.group(2), object_type="作业类型",
            confidence=0.80, chunk_id=chunk_id, doc_id=doc_id,
        ))
    # 模式："X依据Y" → (X, 依据, Y, 法规标准)
    for m in re.finditer(  # noqa: E501
        r"([\u4e00-\u9fa5]{2,10}).{0,4}"
        r"(?:依据|根据|按照)"
        r"([\u4e00-\u9fa5]{2,15}[条例规定标准]+)",
        text,
    ):
        triples.append(Triple(
            subject=m.group(1), subject_type="作业环节",
            relation="依据", object=m.group(2), object_type="法规标准",
            confidence=0.75, chunk_id=chunk_id, doc_id=doc_id,
        ))
    # 去重
    seen: set[tuple[str, str, str]] = set()
    deduped: list[Triple] = []
    for t in triples:
        key = (t.subject, t.relation, t.object)
        if key not in seen:
            seen.add(key)
            deduped.append(t)
    return deduped


# --------------------------------------------------------------------------- #
# 对外 API
# --------------------------------------------------------------------------- #


async def extract_triples(
    text: str,
    *,
    chunk_id: str = "",
    doc_id: int = 0,
    llm: LLMClient | None = None,
) -> ExtractionResult:
    """从单个文本 chunk 中抽取实体关系三元组。

    LLM 可用时使用 LLM，mock 模式下降级为确定性规则。
    所有置信度低于 ``CONFIDENCE_THRESHOLD`` 的三元组会被过滤。
    """
    if llm is None:
        from app.services.llm.client import get_llm_client
        llm = get_llm_client()

    if llm.mock_mode:
        triples = _rule_extract(text, chunk_id, doc_id)
        logger.info("Rule extraction: %d triples from chunk=%s", len(triples), chunk_id[:16])
        return ExtractionResult(triples=triples, source_chunk_id=chunk_id, source_doc_id=doc_id)

    fallback = _LLMExtraction(triples=[])
    messages = _build_few_shot_messages(text)
    try:
        result = await guarded_json_call(
            llm, messages, _LLMExtraction, fallback=fallback, max_tokens=2048,
        )
        triples = [
            Triple(
                subject=t.subject,
                subject_type=t.subject_type,
                relation=t.relation,
                object=t.object,
                object_type=t.object_type,
                confidence=t.confidence,
                chunk_id=chunk_id,
                doc_id=doc_id,
            )
            for t in result.triples
            if t.confidence >= CONFIDENCE_THRESHOLD
        ]
        logger.info("LLM extraction: %d triples (≥%.1f) from chunk=%s",
                     len(triples), CONFIDENCE_THRESHOLD, chunk_id[:16])
        return ExtractionResult(triples=triples, source_chunk_id=chunk_id, source_doc_id=doc_id)
    except Exception as exc:  # noqa: BLE001 — 降级为规则抽取
        logger.warning("LLM extraction failed, falling back to rules: %s", exc)
        triples = _rule_extract(text, chunk_id, doc_id)
        return ExtractionResult(triples=triples, source_chunk_id=chunk_id, source_doc_id=doc_id)


async def extract_from_chunks(
    chunks: list[dict[str, Any]],
    *,
    llm: LLMClient | None = None,
    concurrency: int = 5,
) -> list[ExtractionResult]:
    """从多个 chunk 抽取三元组（信号量限流的并发执行）。"""
    results: list[ExtractionResult | None] = [None] * len(chunks)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run(index: int, chunk: dict[str, Any]) -> None:
        async with semaphore:
            results[index] = await extract_triples(
                text=chunk.get("text", ""),
                chunk_id=str(chunk.get("chunk_id", "")),
                doc_id=int(chunk.get("doc_id", 0)),
                llm=llm,
            )

    await asyncio.gather(*(_run(i, c) for i, c in enumerate(chunks)))
    return [r for r in results if r is not None]
