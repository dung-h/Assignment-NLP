"""Regression coverage for source-derived assignment component relations."""

import pytest

from src.answer.generator import AnswerGenerator
from src.contracts import SemanticQuery
from src.knowledge.index_builder import build_indexes
from src.knowledge.loader import KnowledgeBase
from src.knowledge.query_engine import QueryEngine


def component_query(topics, **entities):
    return SemanticQuery(
        "GET_ASSIGNMENT",
        {"topic": topics, **entities},
        "contains_component",
        "BOOLEAN",
    )


@pytest.fixture
def kb():
    return KnowledgeBase()


def test_question_answering_component_is_found_from_part_ii_source(kb):
    assert kb.assignment_parts["BTL_PART_2"]["title"] == "Semantic Interpretation and QA"
    query = component_query(["QUESTION_ANSWERING"], assignment=["BTL01"])
    assert QueryEngine(kb).execute(query).to_dict() == {
        "status": "FOUND",
        "values": [True],
        "sources": ["assignments:BTL01"],
    }


@pytest.mark.parametrize(
    ("topics", "part", "value"),
    [
        (["QUESTION_ANSWERING"], "BTL_PART_2", True),
        (["QUESTION_ANSWERING"], "BTL_PART_1", False),
        (["PARSING"], "BTL_PART_1", True),
        (["PARSING"], "BTL_PART_2", False),
        (["PARSING", "QUESTION_ANSWERING"], "BTL_PART_1", False),
    ],
)
def test_component_lookup_respects_explicit_part_and_tracks_its_source(kb, topics, part, value):
    query = component_query(topics, assignment_part=[part])
    assert QueryEngine(kb).execute(query).to_dict() == {
        "status": "FOUND",
        "values": [value],
        "sources": [f"assignments:{part}"],
    }


def test_all_requested_components_must_exist_in_selected_assignment(kb):
    query = component_query(["PARSING", "QUESTION_ANSWERING"], assignment=["BTL01"])
    assert QueryEngine(kb).execute(query).to_dict() == {
        "status": "FOUND",
        "values": [True],
        "sources": ["assignments:BTL01"],
    }


def test_optional_rag_extension_is_not_a_component_of_the_four_loaded_parts(kb):
    query = component_query(["RAG"], assignment=["BTL01"])
    assert QueryEngine(kb).execute(query).to_dict() == {
        "status": "FOUND",
        "values": [False],
        "sources": ["assignments:BTL01"],
    }


@pytest.mark.parametrize(
    "entities",
    [
        {"assignment": ["BTL99"]},
        {"assignment_part": ["BTL_PART_99"]},
        {"assignment": ["BTL99"], "assignment_part": ["BTL_PART_2"]},
        {"assignment": ["BTL01", "BTL99"]},
    ],
)
def test_missing_targets_do_not_create_false_with_a_fabricated_source(kb, entities):
    result = QueryEngine(kb).execute(component_query(["QUESTION_ANSWERING"], **entities))
    assert result.to_dict() == {"status": "NOT_FOUND", "values": [], "sources": []}


def test_assignment_with_no_parts_returns_not_found(kb):
    kb.assignments["BTL01"]["parts"] = []
    result = QueryEngine(kb).execute(component_query(["QUESTION_ANSWERING"]))
    assert result.to_dict() == {"status": "NOT_FOUND", "values": [], "sources": []}


def test_component_indexes_link_topics_to_parts_without_hardcoded_part_numbers(kb):
    assert "PARSING" in kb.indexes.assignment_part_to_topics["BTL_PART_1"]
    assert "QUESTION_ANSWERING" in kb.indexes.assignment_part_to_topics["BTL_PART_2"]
    assert kb.indexes.topic_to_assignment_parts["QUESTION_ANSWERING"] == ["BTL_PART_2"]


def test_ingestion_recognizes_multiple_components_and_prefers_longer_aliases(kb):
    kb.assignment_parts["BTL_PART_4"]["title"] = "Parser, QA (probabilistic context-free grammar)"
    build_indexes(kb)
    topics = kb.indexes.assignment_part_to_topics["BTL_PART_4"]
    assert set(topics) == {"PARSING", "QUESTION_ANSWERING", "PCFG"}
    assert "CFG" not in topics
    assert kb.indexes.topic_to_assignment_parts["QUESTION_ANSWERING"] == [
        "BTL_PART_2", "BTL_PART_4"
    ]


def test_component_matching_uses_word_boundaries_and_only_content_fields(kb):
    part = kb.assignment_parts["BTL_PART_4"]
    part["title"] = "Squad and reparsers"
    part["outputs"] = ["output/QA.txt", "output/parser.txt"]
    part["debug_note"] = "question answering"
    build_indexes(kb)
    query = component_query(["QUESTION_ANSWERING"], assignment_part=["BTL_PART_4"])
    assert QueryEngine(kb).execute(query).values == [False]
    assert kb.indexes.assignment_part_to_topics["BTL_PART_4"] == []


def test_component_relation_can_come_from_a_requirement(kb):
    kb.assignment_parts["BTL_PART_4"]["requirements"] = ["Triển khai hỏi đáp (QA)."]
    build_indexes(kb)
    query = component_query(["QUESTION_ANSWERING"], assignment_part=["BTL_PART_4"])
    assert QueryEngine(kb).execute(query).values == [True]


def test_rebuilding_indexes_removes_stale_component_relations(kb):
    part = kb.assignment_parts["BTL_PART_2"]
    part["title"] = "Semantic Interpretation"
    build_indexes(kb)
    assert "QUESTION_ANSWERING" not in kb.indexes.assignment_part_to_topics["BTL_PART_2"]
    assert "QUESTION_ANSWERING" not in kb.indexes.topic_to_assignment_parts
    query = component_query(["QUESTION_ANSWERING"], assignment=["BTL01"])
    assert QueryEngine(kb).execute(query).values == [False]


def test_query_engine_uses_component_index_not_runtime_text_search(kb):
    kb.assignment_parts["BTL_PART_2"]["title"] = "Changed display text"
    query = component_query(["QUESTION_ANSWERING"], assignment=["BTL01"])
    assert QueryEngine(kb).execute(query).values == [True]


def test_answer_says_yes_for_the_grounded_question_answering_component(kb):
    query = component_query(["QUESTION_ANSWERING"], assignment=["BTL01"])
    result = QueryEngine(kb).execute(query)
    answer = AnswerGenerator().generate(query, result, kb)
    assert answer.startswith("Có.")
    assert "assignments:BTL01" in answer
