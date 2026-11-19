import json
from pathlib import Path

import pytest

from src.answer.generator import AnswerGenerator
from src.contracts import SemanticQuery
from src.knowledge.loader import KnowledgeBase
from src.knowledge.query_engine import QueryEngine


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "contracts" / "mock_cases" / "person3.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
RETRIEVAL_CASES = [
    case for case in CASES if case.get("test_kind", "retrieval") == "retrieval"
]


@pytest.fixture(scope="module")
def knowledge_runtime():
    kb = KnowledgeBase()
    return kb, QueryEngine(kb), AnswerGenerator()


def test_shared_kb_cases_have_required_shape():
    assert [case["id"] for case in CASES] == [
        "K01", "K02", "K03", "K04", "K05", "K06",
        "K07", "K08", "K09", "K10", "K11", "K12",
        "K13", "K14", "K15", "K16",
    ]
    for case in CASES:
        required = {
            "id",
            "description",
            "input_semantic_query",
        }
        if case.get("test_kind", "retrieval") == "validation":
            required |= {"test_kind", "expected_error"}
        else:
            required.add("expected_retrieval")
        assert set(case) >= required
        assert set(case["input_semantic_query"]) == {
            "intent",
            "entities",
            "attribute",
            "answer_mode",
        }
        if case.get("test_kind", "retrieval") == "retrieval":
            assert set(case["expected_retrieval"]) == {
                "status",
                "values",
                "sources",
            }


def test_shared_kb_cases_match_retrieval_behavior(knowledge_runtime):
    _, query_engine, _ = knowledge_runtime
    case = CASES[0]
    query = SemanticQuery(**case["input_semantic_query"])
    assert query_engine.execute(query).to_dict() == case["expected_retrieval"]
