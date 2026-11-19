import json
from pathlib import Path

import pytest

from src.answer.generator import AnswerGenerationError, AnswerGenerator
from src.contracts import RetrievalResult, SemanticQuery
from src.knowledge.loader import KnowledgeBase
from src.knowledge.query_engine import QueryEngine


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "contracts" / "mock_cases" / "person3.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
CASES = [
    case for case in CASES if case.get("test_kind", "retrieval") == "retrieval"
]


@pytest.fixture(scope="module")
def knowledge_runtime():
    kb = KnowledgeBase()
    return kb, QueryEngine(kb), AnswerGenerator()


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_answer_matches_frozen_case(case, knowledge_runtime):
    kb, query_engine, answer_generator = knowledge_runtime
    query = SemanticQuery(**case["input_semantic_query"])
    retrieval = query_engine.execute(query)
    answer = answer_generator.generate(query, retrieval, kb)

    if "expected_answer_exact" in case:
        assert answer == case["expected_answer_exact"]
    else:
        for fact in case["answer_must_contain"]:
            assert fact in answer


def test_found_answers_do_not_use_not_found_message(knowledge_runtime):
    kb, query_engine, answer_generator = knowledge_runtime
    for case in CASES:
        if case["expected_retrieval"]["status"] != "FOUND":
            continue
        query = SemanticQuery(**case["input_semantic_query"])
        retrieval = query_engine.execute(query)
        answer = answer_generator.generate(query, retrieval, kb).lower()
        assert "không tìm thấy" not in answer


def test_chapter_display_uses_retrieved_id_without_expanding_relations(knowledge_runtime):
    kb, _, answer_generator = knowledge_runtime
    query = SemanticQuery(
        intent="GET_TOPIC",
        entities={"topic": ["CFG"]},
        attribute="chapter",
        answer_mode="LIST",
    )
    retrieval = RetrievalResult("FOUND", ["CH03"], ["topics:CH03"])

    answer = answer_generator.generate(query, retrieval, kb)

    assert "CH03" in answer
    assert "Chương 3" in answer
    assert "CH06" not in answer
    assert "WEEK_04" not in answer


def test_boolean_false_is_rendered_as_no(knowledge_runtime):
    kb, _, answer_generator = knowledge_runtime
    query = SemanticQuery(
        intent="GET_RULE",
        entities={"regulation": ["ASSIGNMENT_SHARING"]},
        attribute="permission",
        answer_mode="BOOLEAN",
    )
    retrieval = RetrievalResult(
        "FOUND", [False], ["regulations:ASSIGNMENT_SHARING"]
    )

    answer = answer_generator.generate(query, retrieval, kb)

    assert answer.startswith("Không.")
    assert "regulations:ASSIGNMENT_SHARING" in answer


def test_boolean_template_does_not_coerce_non_boolean_values(knowledge_runtime):
    kb, _, answer_generator = knowledge_runtime
    query = SemanticQuery(
        intent="GET_RULE",
        entities={"regulation": ["LLM_RAG"]},
        attribute="permission",
        answer_mode="BOOLEAN",
    )

    with pytest.raises(AnswerGenerationError):
        answer_generator.generate(
            query,
            RetrievalResult("FOUND", [1], ["regulations:LLM_RAG"]),
            kb,
        )


def test_zero_is_a_valid_found_value(knowledge_runtime):
    kb, _, answer_generator = knowledge_runtime
    query = SemanticQuery(
        intent="GET_COURSE_INFO",
        entities={"course": ["CO3085"]},
        attribute="credits",
        answer_mode="VALUE",
    )
    retrieval = RetrievalResult("FOUND", [0], ["course_info:CO3085"])

    answer = answer_generator.generate(query, retrieval, kb)

    assert "0 tín chỉ" in answer
    assert "không tìm thấy" not in answer.lower()


def test_summary_ending_in_period_is_not_double_punctuated(knowledge_runtime):
    kb, _, answer_generator = knowledge_runtime
    query = SemanticQuery(
        intent="GET_TOPIC",
        entities={"chapter": ["CH04"]},
        attribute="summary",
        answer_mode="VALUE",
    )
    retrieval = RetrievalResult("FOUND", ["A grounded summary."], ["topics:CH04"])

    answer = answer_generator.generate(query, retrieval, kb)

    assert "summary.." not in answer
    assert "A grounded summary. Nguồn:" in answer


def test_unknown_is_not_rendered_by_answer_layer(knowledge_runtime):
    kb, _, answer_generator = knowledge_runtime
    query = SemanticQuery(intent="UNKNOWN", entities={}, attribute=None)
    retrieval = RetrievalResult("NOT_FOUND", [], [])

    with pytest.raises(AnswerGenerationError):
        answer_generator.generate(query, retrieval, kb)


def test_missing_found_value_is_rejected(knowledge_runtime):
    kb, _, answer_generator = knowledge_runtime
    query = SemanticQuery(
        intent="GET_COURSE_INFO",
        entities={"course": ["CO3085"]},
        attribute="credits",
        answer_mode="VALUE",
    )

    with pytest.raises(AnswerGenerationError):
        answer_generator.generate(
            query,
            RetrievalResult("FOUND", [""], ["course_info:CO3085"]),
            kb,
        )


@pytest.mark.parametrize(
    "intent,entities,attribute,heading",
    [
        ("GET_SCHEDULE", {"week": ["WEEK_03"]}, "topics", "Nội dung tuần 3"),
        ("GET_TOPIC", {"chapter": ["CH03"]}, "topics", "Nội dung chương 3"),
        ("GET_ASSIGNMENT", {"assignment_part": ["BTL_PART_1"]}, "outputs", "Các tệp đầu ra"),
        ("GET_ASSIGNMENT", {"assignment": ["BTL01"]}, "requirements", "Yêu cầu bài tập lớn"),
        ("GET_COURSE_INFO", {"course": ["CO3085"]}, "parts", "Các phần của môn học"),
        ("GET_RESOURCE", {"topic": ["CFG"]}, "resource", "Tài liệu phù hợp"),
    ],
)
def test_list_answers_are_readable_and_keep_every_value(intent, entities, attribute, heading):
    query = SemanticQuery(intent=intent, entities=entities, attribute=attribute, answer_mode="LIST")
    retrieval = RetrievalResult("FOUND", ["Nội dung A", "Nội dung B"], ["sample:SOURCE"])

    answer = AnswerGenerator().generate(query, retrieval)

    assert answer == f"{heading}:\n\n- Nội dung A\n- Nội dung B\n\nNguồn: sample:SOURCE."


def test_list_heading_does_not_attribute_multiple_weeks_to_only_one():
    query = SemanticQuery("GET_SCHEDULE", {"week": ["WEEK_03", "WEEK_04"]}, "topics", "LIST")
    answer = AnswerGenerator().generate(query, RetrievalResult("FOUND", ["A", "B"], ["schedule:WEEK_03", "schedule:WEEK_04"]))
    assert answer.startswith("Nội dung học:")
    assert "Nội dung tuần 3" not in answer
