import json
from pathlib import Path

import pytest

from src.contracts import SemanticQuery
from src.knowledge.loader import KnowledgeBase
from src.knowledge.query_engine import QueryEngine, QueryHandlerNotImplemented
from src.semantics.semantic_query_validator import InvalidSemanticQuery


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "mock_cases" / "person3.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
RETRIEVAL_CASES = [
    case for case in CASES if case.get("test_kind", "retrieval") == "retrieval"
]
VALIDATION_CASES = [
    case for case in CASES if case.get("test_kind") == "validation"
]


@pytest.fixture(scope="module")
def query_engine():
    return QueryEngine(KnowledgeBase())


@pytest.mark.parametrize("case", RETRIEVAL_CASES, ids=[case["id"] for case in RETRIEVAL_CASES])
def test_query_engine_matches_frozen_retrieval(case, query_engine):
    query = SemanticQuery(**case["input_semantic_query"])
    result = query_engine.execute(query)
    assert result.to_dict() == case["expected_retrieval"]


def test_not_found_result_is_empty_and_source_free(query_engine):
    query = SemanticQuery(
        "GET_TOPIC",
        {"chapter": ["CH404"]},
        "summary",
        "VALUE",
    )
    assert query_engine.execute(query).to_dict() == {
        "status": "NOT_FOUND",
        "values": [],
        "sources": [],
    }


def test_resource_by_chapter_does_not_invent_a_relation(query_engine):
    query = SemanticQuery(
        "GET_RESOURCE",
        {"chapter": ["CH03"]},
        "resource",
        "LIST",
    )
    assert query_engine.execute(query).to_dict() == {
        "status": "NOT_FOUND",
        "values": [],
        "sources": [],
    }


def test_resource_topic_lookup_uses_annotation_index_not_usage_text(query_engine):
    query_engine.kb.resources["RES02"]["usage"] = "unrelated text"
    query = SemanticQuery(
        "GET_RESOURCE",
        {"topic": ["STATISTICAL_NLP"]},
        "resource",
        "LIST",
    )
    assert query_engine.execute(query).to_dict() == {
        "status": "FOUND",
        "values": [
            "Introduction to Natural Language Processing",
            "Foundation of Statistical Natural Language Processing",
        ],
        "sources": ["resources:RES02", "resources:RES04"],
    }


def test_lo_chapter_lookup_does_not_use_a_hardcoded_relation(query_engine):
    query = SemanticQuery(
        "GET_LO",
        {"learning_outcome": ["LO2.5"]},
        "chapter",
        "LIST",
    )
    assert query_engine.execute(query).to_dict() == {
        "status": "NOT_FOUND",
        "values": [],
        "sources": [],
    }


def test_valid_query_without_handler_is_not_reported_as_not_found(query_engine):
    query_engine._handle_get_topic = None
    query = SemanticQuery(
        "GET_TOPIC",
        {"chapter": ["CH03"]},
        "summary",
        "VALUE",
    )
    with pytest.raises(QueryHandlerNotImplemented):
        query_engine.execute(query)


@pytest.mark.parametrize("case", VALIDATION_CASES, ids=[case["id"] for case in VALIDATION_CASES])
def test_invalid_semantic_query_is_rejected_before_retrieval(case, query_engine):
    query = SemanticQuery(**case["input_semantic_query"])
    with pytest.raises(InvalidSemanticQuery):
        query_engine.execute(query)
