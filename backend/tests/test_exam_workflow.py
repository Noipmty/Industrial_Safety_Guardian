"""考试工作流测试：意图识别、组卷、判卷（离线）。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.prompts.exam import detect_exam_intent_rules
from app.workflows.exam_generate.nodes import (
    ExamGenContext,
    GeneratedQuestion,
    _mock_generate,
)
from app.workflows.exam_grade.nodes import (
    ExamGradeContext,
    _exact_match,
    _mock_grade,
)

# ---------------------------------------------------------------------------
# 意图识别（支持否定词）
# ---------------------------------------------------------------------------


class TestExamIntentDetection:
    """基于规则的考试意图识别，支持否定处理。"""

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("给我出5道题", True),
            ("出一套井控考试", True),
            ("练习题做几道", True),
            ("不要出题", False),
            ("别出题了", False),
            ("不想考试", False),
            ("暂时不要出题", False),
            ("今天天气怎么样", False),
            ("帮我查一下井控参数", False),
        ],
    )
    def test_rules(self, query: str, expected: bool) -> None:
        is_intent, _ = detect_exam_intent_rules(query)
        assert is_intent == expected

    def test_negation_must_be_false(self) -> None:
        """“不要出题”应被识别为否定，而非意图。"""
        is_intent, reason = detect_exam_intent_rules("不要出题")
        assert is_intent is False
        assert "否定" in reason

    def test_no_trigger_word(self) -> None:
        is_intent, reason = detect_exam_intent_rules("钻井液密度是多少")
        assert is_intent is False
        assert reason == ""


# ---------------------------------------------------------------------------
# 精确匹配（客观题判分）
# ---------------------------------------------------------------------------


class TestExactMatch:
    """客观题答案的归一化与匹配。"""

    @pytest.mark.parametrize(
        "user,correct,qtype,expected",
        [
            ("A", "A", "single", True),
            ("a", "A", "single", True),
            (" B ", "B", "single", True),
            ("A", "B", "single", False),
            ("AB", "BA", "multiple", True),
            ("ABC", "ACB", "multiple", True),
            ("AB", "ABC", "multiple", False),
            ("对", "对", "judge", True),
            ("T", "对", "judge", True),
            ("true", "对", "judge", True),
            ("错", "F", "judge", True),
            ("对", "错", "judge", False),
        ],
    )
    def test_match(
        self, user: str, correct: str, qtype: str, expected: bool
    ) -> None:
        assert _exact_match(user, correct, qtype) == expected


# ---------------------------------------------------------------------------
# mock 组卷
# ---------------------------------------------------------------------------


class TestMockGenerate:
    """确定性的兜底组卷。"""

    def test_generates_correct_count(self) -> None:
        qs = _mock_generate(["single", "multiple"], 5, "司钻")
        assert len(qs) == 5
        assert all(isinstance(q, GeneratedQuestion) for q in qs)

    def test_all_types_when_filter_matches(self) -> None:
        qs = _mock_generate(["single"], 3, "司钻")
        assert all(q.question_type == "single" for q in qs)

    def test_fallback_when_no_type_match(self) -> None:
        qs = _mock_generate(["nonexistent"], 2, "司钻")
        assert len(qs) == 2

    def test_question_has_required_fields(self) -> None:
        qs = _mock_generate(["single"], 1, "司钻")
        q = qs[0]
        assert q.stem
        assert q.answer
        assert q.options is not None
        assert len(q.options) == 4
        assert 1 <= q.difficulty <= 5


# ---------------------------------------------------------------------------
# mock 主观题判分
# ---------------------------------------------------------------------------


class TestMockGrade:
    """主观题判分的关键词重叠兜底。"""

    def test_empty_answer_zero(self) -> None:
        score, reason = _mock_grade("", "参考答案", 20.0)
        assert score == 0.0
        assert "未作答" in reason

    def test_full_overlap(self) -> None:
        score, _ = _mock_grade("参考答案", "参考答案", 20.0)
        assert score == 20.0

    def test_partial_overlap(self) -> None:
        score, _ = _mock_grade("部分答案", "参考答案内容", 20.0)
        assert 0 < score < 20.0

    def test_score_within_max(self) -> None:
        score, _ = _mock_grade("参考答案", "参考答案", 10.0)
        assert score <= 10.0


# ---------------------------------------------------------------------------
# 工作流集成（mock LLM + mock 检索）
# ---------------------------------------------------------------------------


def _make_mock_llm() -> MagicMock:
    """创建处于 mock_mode 的 mock LLM 客户端。"""
    llm = MagicMock()
    llm.mock_mode = True
    return llm


def _make_mock_search() -> MagicMock:
    """创建返回空命中结果的 mock 混合检索工具。"""
    tool = MagicMock()
    tool.run = AsyncMock(return_value=[])
    return tool


class TestExamGenerateWorkflow:
    """集成测试：完整组卷图（mock 模式）。"""

    @pytest.mark.asyncio
    async def test_intent_confirmed_passthrough(self) -> None:
        """API 已确认的意图应直接通过 intent_detect。"""
        llm = _make_mock_llm()
        search = _make_mock_search()
        session_factory = MagicMock()

        ctx = ExamGenContext(
            llm=llm, search_tool=search, session_factory=session_factory
        )
        from app.workflows.exam_generate.nodes import make_intent_detect_node

        node = make_intent_detect_node(ctx)
        result = await node({
            "intent_confirmed": True,
            "raw_query": "",
        })
        assert result["is_exam_intent"] is True
        assert "API confirmed" in result["intent_reason"]

    @pytest.mark.asyncio
    async def test_negation_short_circuits(self) -> None:
        """“不要出题”应将 is_exam_intent 设为 False。"""
        llm = _make_mock_llm()
        search = _make_mock_search()
        session_factory = MagicMock()

        ctx = ExamGenContext(
            llm=llm, search_tool=search, session_factory=session_factory
        )
        from app.workflows.exam_generate.nodes import (
            make_intent_detect_node,
            route_after_intent,
        )

        node = make_intent_detect_node(ctx)
        result = await node({
            "raw_query": "不要出题",
            "intent_confirmed": False,
        })
        assert result["is_exam_intent"] is False
        assert route_after_intent(result) == "__end__"


class TestExamGradeWorkflow:
    """集成测试：判卷节点（mock 模式）。"""

    @pytest.mark.asyncio
    async def test_objective_grading(self) -> None:
        """单选/多选/判断题的精确匹配判分。"""
        llm = _make_mock_llm()
        search = _make_mock_search()
        ctx = ExamGradeContext(llm=llm, search_tool=search)

        from app.workflows.exam_grade.nodes import make_grade_objective_node

        node = make_grade_objective_node(ctx)
        result = await node({
            "questions": [
                {"id": 1, "question_type": "single", "answer": "A", "stem": "q1"},
                {"id": 2, "question_type": "multiple", "answer": "ABC", "stem": "q2"},
                {"id": 3, "question_type": "judge", "answer": "对", "stem": "q3"},
                {"id": 4, "question_type": "short_answer", "answer": "ans", "stem": "q4"},
            ],
            "answers": [
                {"question_id": 1, "user_answer": "A"},
                {"question_id": 2, "user_answer": "CBA"},
                {"question_id": 3, "user_answer": "对"},
                {"question_id": 4, "user_answer": "ans"},
            ],
            "question_scores": {"1": 5.0, "2": 10.0, "3": 5.0, "4": 20.0},
        })
        graded = result["graded_answers"]
        # 客观题节点跳过 short_answer。
        assert len(graded) == 3
        assert graded[0]["score"] == 5.0  # 单选正确
        assert graded[1]["score"] == 10.0  # 多选正确（与顺序无关）
        assert graded[2]["score"] == 5.0  # 判断正确

    @pytest.mark.asyncio
    async def test_subjective_grading_mock(self) -> None:
        """主观题判分使用 mock 关键词重叠兜底。"""
        llm = _make_mock_llm()
        search = _make_mock_search()
        ctx = ExamGradeContext(llm=llm, search_tool=search)

        from app.workflows.exam_grade.nodes import make_grade_subjective_node

        node = make_grade_subjective_node(ctx)
        result = await node({
            "questions": [
                {
                    "id": 1,
                    "question_type": "short_answer",
                    "stem": "井控职责",
                    "answer": "监控井控参数发现溢流",
                    "knowledge_tags": ["井控"],
                },
            ],
            "answers": [{"question_id": 1, "user_answer": "监控井控参数发现溢流"}],
            "question_scores": {"1": 20.0},
            "graded_answers": [],
        })
        graded = result["graded_answers"]
        assert len(graded) == 1
        assert graded[0]["score"] > 0
        assert "mock" in graded[0]["grading_detail"] or "评分" in graded[0]["grading_detail"]
        assert "weak_points" in result
        assert "strong_points" in result

    @pytest.mark.asyncio
    async def test_wrong_answer_zero_score(self) -> None:
        """客观题答错得 0 分。"""
        llm = _make_mock_llm()
        search = _make_mock_search()
        ctx = ExamGradeContext(llm=llm, search_tool=search)

        from app.workflows.exam_grade.nodes import make_grade_objective_node

        node = make_grade_objective_node(ctx)
        result = await node({
            "questions": [
                {"id": 1, "question_type": "single", "answer": "A", "stem": "q"},
            ],
            "answers": [{"question_id": 1, "user_answer": "B"}],
            "question_scores": {"1": 5.0},
        })
        assert result["graded_answers"][0]["score"] == 0.0
