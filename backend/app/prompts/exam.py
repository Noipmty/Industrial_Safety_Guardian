"""考试出题与判分的提示词模板。

意图检测采用规则优先 + LLM 复核的方式，并处理否定句式。
题目生成产出结构化 JSON，由 Pydantic 校验。
主观题判分使用 RAG 检索到的参考依据 + rubric 评分。
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 考试意图检测（可识别否定句式）
# ---------------------------------------------------------------------------

# 用户想要出题时常见的表述。
_EXAM_TRIGGER_WORDS = (
    "出题", "出几道", "出几道题", "出一套", "考试", "考一考", "测验",
    "练习题", "做题", "来几道题", "生成试卷", "组卷", "考卷",
)

# 匹配数字变体的正则模式，如"出5道题"/"出10道"。
_EXAM_TRIGGER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"出\d+道题?"),
    re.compile(r"出\d+套"),
    re.compile(r"\d+道考题"),
)

# 否定前缀 —— 若出现在触发词之前，则意图被否定。
_NEGATION_PREFIXES = (
    "不要", "不用", "别", "无需", "不想", "暂时不", "先不",
    "no ", "don't ", "stop ", "not ",
)


def _has_trigger(text: str) -> tuple[bool, str]:
    """检查文本是否包含任何出题触发词或触发模式。"""
    for trigger in _EXAM_TRIGGER_WORDS:
        if trigger in text:
            return True, trigger
    for pattern in _EXAM_TRIGGER_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, match.group(0)
    return False, ""


def detect_exam_intent_rules(text: str) -> tuple[bool, str]:
    """基于规则的出题意图检测，并处理否定句式。

    返回 ``(is_exam_intent, reason)``。被否定的触发
    （如 ``"不要出题"``）会被显式判定为 ``False``。
    """
    has, trigger = _has_trigger(text)
    if not has:
        return False, ""
    # 检查否定：若否定前缀紧邻在触发词之前。
    for neg in _NEGATION_PREFIXES:
        if neg + trigger in text:
            return False, f"否定意图: {neg}{trigger}"
        # 同时检查正则匹配到的触发词。
        for pattern in _EXAM_TRIGGER_PATTERNS:
            if pattern.search(text) and neg in text:
                idx = text.find(trigger)
                before = text[max(0, idx - len(neg)) : idx]
                if before == neg:
                    return False, f"否定意图: {neg}{trigger}"
    return True, f"命中出题关键词: {trigger}"


_EXAM_INTENT_LLM_SYSTEM = """你是考试意图检测模块。判断用户输入是否要求生成考试/出题/做题。
特别注意：如果用户说"不要出题""别出题""不想考试"等否定句式，必须返回 is_exam_intent=false。
只输出 JSON：{"is_exam_intent": true/false, "reason": "一句话理由"}"""


# ---------------------------------------------------------------------------
# 题目生成
# ---------------------------------------------------------------------------

EXAM_GENERATE_SYSTEM = """你是工业安全生产考试命题专家。根据给定的岗位、题型和知识点，
生成结构化的考试题目。输出 JSON 数组，每道题格式如下：
{
  "question_type": "single|multiple|judge|short_answer",
  "stem": "题干文本",
  "options": ["选项A", "选项B", "选项C", "选项D"],
  "answer": "正确答案（single填选项字母如A，multiple填AB，judge填对/错，short_answer填参考答案）",
  "explanation": "解析说明",
  "knowledge_tags": ["知识点1", "知识点2"],
  "difficulty": 1-5的整数,
  "source_chunk_id": "来源chunk标识（如有）"
}
要求：
1. 题目内容基于钻井安全生产实际知识，不得编造虚假信息。
2. 选项要有迷惑性但不能有歧义。
3. 难度分布：约 40% 简单(1-2)，40% 中等(3)，20% 困难(4-5)。
4. 知识点覆盖尽量广泛，避免重复。
5. single 题必须有4个选项，multiple 题必须有4个选项，judge 题不需要 options。
6. short_answer 题不需要 options，answer 填参考答案要点。
只输出 JSON 数组，不要多余文字。"""


EXAM_GENERATE_USER = """## 出题要求
岗位: {position}
题型: {question_types}
题目数量: {num_questions}
题型分配（必须严格遵守）: {type_counts}
知识点标签: {knowledge_tags}

## 检索到的参考知识（出题依据）
{context}

请基于以上要求生成 {num_questions} 道题，每种题型的数量必须与"题型分配"完全一致，输出 JSON 数组。"""


# ---------------------------------------------------------------------------
# 质量检查
# ---------------------------------------------------------------------------

EXAM_QUALITY_CHECK_SYSTEM = """你是试卷质量审核员。检查生成的题目是否满足：
1. 知识点覆盖：知识点是否重复或遗漏严重。
2. 难度分布：是否符合 40% 简单 / 40% 中等 / 20% 困难 的近似分布。
3. 题型匹配：每道题的 question_type 是否在要求的题型列表内。
4. 答案完整性：single/multiple 题是否有4个选项且答案格式正确。
只输出 JSON：
{"passed": true/false, "issues": ["问题描述"], "suggestions": ["改进建议"]}"""


# ---------------------------------------------------------------------------
# 主观题判分
# ---------------------------------------------------------------------------

EXAM_GRADE_SUBJECTIVE_SYSTEM = """你是主观题评分专家。根据检索到的参考依据和评分标准（rubric），
对用户答案进行评分。输出 JSON：
{
  "score": 0-满分之间的数值,
  "max_score": 该题满分,
  "rubric_scores": {"评分维度1": 得分, "评分维度2": 得分},
  "reason": "评分理由（引用检索来源）",
  "reference_snippets": ["引用的检索片段1", "引用的检索片段2"]
}
评分原则：
1. 严格依据检索到的参考依据评分，不得凭空判断。
2. 关键知识点缺失则扣分，表述不清酌情扣分。
3. 给出具体、可操作的评分理由，标注引用编号。
只输出 JSON。"""


EXAM_GRADE_SUBJECTIVE_USER = """## 题目
{stem}

## 参考答案
{reference_answer}

## 用户答案
{user_answer}

## 检索到的参考依据
{context}

## 评分标准（Rubric）
{rubric}

满分: {max_score} 分。请按 rubric 逐维度评分并给出理由。"""
