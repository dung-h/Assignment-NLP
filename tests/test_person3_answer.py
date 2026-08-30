import json
from pathlib import Path

import pytest

from src.answer.generator import AnswerGenerationError, AnswerGenerator
from src.contracts import RetrievalResult, SemanticQuery
from src.knowledge.loader import KnowledgeBase
from src.knowledge.query_engine import QueryEngine


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "mock_cases" / "person3.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
CASES = [
    case for case in CASES if case.get("test_kind", "retrieval") == "retrieval"
]


@pytest.fixture(scope="module")
def person3_runtime():
    kb = KnowledgeBase()
    return kb, QueryEngine(kb), AnswerGenerator()


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_answer_matches_frozen_case(case, person3_runtime):
    kb, query_engine, answer_generator = person3_runtime
    query = SemanticQuery(**case["input_semantic_query"])
    retrieval = query_engine.execute(query)
    answer = answer_generator.generate(query, retrieval, kb)

    if "expected_answer_exact" in case:
        assert answer == case["expected_answer_exact"]
    else:
        for fact in case["answer_must_contain"]:
            assert fact in answer


def test_found_answers_do_not_use_not_found_message(person3_runtime):
    kb, query_engine, answer_generator = person3_runtime
    for case in CASES:
        if case["expected_retrieval"]["status"] != "FOUND":
            continue
        query = SemanticQuery(**case["input_semantic_query"])
        retrieval = query_engine.execute(query)
        answer = answer_generator.generate(query, retrieval, kb).lower()
        assert "không tìm thấy" not in answer


def test_chapter_display_uses_retrieved_id_without_expanding_relations(person3_runtime):
    kb, _, answer_generator = person3_runtime
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


def test_boolean_false_is_rendered_as_no(person3_runtime):
    kb, _, answer_generator = person3_runtime
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


def test_boolean_template_does_not_coerce_non_boolean_values(person3_runtime):
    kb, _, answer_generator = person3_runtime
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


def test_zero_is_a_valid_found_value(person3_runtime):
    kb, _, answer_generator = person3_runtime
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


def test_unknown_is_not_rendered_by_person3(person3_runtime):
    kb, _, answer_generator = person3_runtime
    query = SemanticQuery(intent="UNKNOWN", entities={}, attribute=None)
    retrieval = RetrievalResult("NOT_FOUND", [], [])

    with pytest.raises(AnswerGenerationError):
        answer_generator.generate(query, retrieval, kb)


def test_missing_found_value_is_rejected(person3_runtime):
    kb, _, answer_generator = person3_runtime
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
