"""Checks for missing KB data and evidence-grounded relations."""

import pytest
from shutil import copytree

from src.answer.generator import AnswerGenerationError, AnswerGenerator
from src.contracts import RetrievalResult, SemanticQuery
from src.knowledge.loader import ANNOTATIONS, DATA, KBValidationError, KnowledgeBase
from src.knowledge.query_engine import QueryEngine


@pytest.mark.parametrize(
    "query, expected",
    [
        (SemanticQuery("GET_INSTRUCTOR", {}, "name", "VALUE"), "giảng viên"),
        (SemanticQuery("GET_DEADLINE", {"assignment": ["BTL01"]}, "date", "VALUE"), "deadline"),
        (SemanticQuery("GET_RESOURCE", {"chapter": ["CH04"]}, "resource", "LIST"), "không tìm thấy"),
    ],
)
def test_not_found_produces_explanation_without_inventing_values(query, expected):
    kb = KnowledgeBase()
    retrieval = QueryEngine(kb).execute(query)
    assert retrieval.to_dict() == {"status": "NOT_FOUND", "values": [], "sources": []}
    assert expected in AnswerGenerator().generate(query, retrieval, kb).lower()


def test_boolean_with_multiple_values_must_not_silently_select_first():
    query = SemanticQuery("GET_RULE", {"regulation": ["LLM_RAG"]}, "permission", "BOOLEAN")
    with pytest.raises(AnswerGenerationError):
        AnswerGenerator().generate(query, RetrievalResult("FOUND", [True, False], ["test:policy"]))


def test_chapter_resource_query_joins_only_annotated_common_topics():
    kb = KnowledgeBase()
    # Synthetic data tests the algorithm, not a claim about the real dataset.
    kb.indexes.chapter_to_topics["CH03"] = ["CFG"]
    kb.resource_topic_annotations["RES05"] = {"topics": ["CFG"]}
    kb.indexes.topic_to_resources["CFG"] = ["RES05", "RES05"]
    query = SemanticQuery("GET_RESOURCE", {"chapter": ["CH03"]}, "resource", "LIST")
    result = QueryEngine(kb).execute(query)
    assert result.to_dict() == {
        "status": "FOUND",
        "values": ["Natural Language Processing with Python"],
        "sources": ["topics:CH03", "annotation:resource_topics:RES05", "resources:RES05"],
    }
    answer = AnswerGenerator().generate(query, result, kb)
    assert "liên quan theo chủ đề" in answer
    assert "không khẳng định" in answer


def test_chapter_query_ignores_unannotated_or_unknown_resources():
    kb = KnowledgeBase()
    kb.resource_topic_annotations.pop("RES05", None)
    kb.indexes.chapter_to_topics["CH03"] = ["CFG"]
    kb.indexes.topic_to_resources["CFG"] = ["RES05", "RES99"]
    query = SemanticQuery("GET_RESOURCE", {"chapter": ["CH03"]}, "resource", "LIST")
    assert QueryEngine(kb).execute(query).status == "NOT_FOUND"


def test_cfg_resource_has_external_annotation_provenance():
    kb = KnowledgeBase()
    query = SemanticQuery("GET_RESOURCE", {"topic": ["CFG"]}, "resource", "LIST")
    result = QueryEngine(kb).execute(query)
    assert result.to_dict() == {
        "status": "FOUND",
        "values": ["Natural Language Processing with Python"],
        "sources": ["annotation:resource_topics:RES05", "resources:RES05"],
    }
    assert kb.resource_topic_annotations["RES05"]["evidence"]["url"] == "https://www.nltk.org/book_1ed/ch08.html"


def test_lo_chapter_and_related_content_use_reviewable_mapping():
    kb = KnowledgeBase()
    engine = QueryEngine(kb)
    chapter = SemanticQuery("GET_LO", {"learning_outcome": ["LO4.2"]}, "chapter", "LIST")
    result = engine.execute(chapter)
    assert result.to_dict() == {
        "status": "FOUND", "values": ["CH12"],
        "sources": ["course_info:LO4.2", "topics:CH12", "annotation:lo_chapters:LO4.2_CH12"],
    }
    assert "đối chiếu tham khảo" in AnswerGenerator().generate(chapter, result, kb)
    content = SemanticQuery("GET_LO", {"learning_outcome": ["LO4.2"]}, "related_content", "LIST")
    related = engine.execute(content)
    assert related.status == "FOUND"
    assert related.values[0].startswith("CH12:")
    assert "discourse context" in related.values[0]
    assert related.sources == result.sources
    assert ".. Nguồn:" not in AnswerGenerator().generate(content, related, kb)


def test_lo_without_reviewable_mapping_stays_not_found():
    kb = KnowledgeBase()
    query = SemanticQuery("GET_LO", {"learning_outcome": ["LO2.5"]}, "chapter", "LIST")
    assert QueryEngine(kb).execute(query).status == "NOT_FOUND"


def test_stale_lo_annotation_is_rejected(tmp_path):
    import yaml

    copytree(DATA, tmp_path / "raw")
    copytree(ANNOTATIONS, tmp_path / "annotations")
    annotation_file = tmp_path / "annotations" / "lo_chapters.yaml"
    annotation = yaml.safe_load(annotation_file.read_text(encoding="utf-8"))
    annotation["mappings"][0]["basis"]["chapter_keyword"] = "not a chapter keyword"
    annotation_file.write_text(yaml.safe_dump(annotation, allow_unicode=True), encoding="utf-8")
    with pytest.raises(KBValidationError, match="invalid evidence"):
        KnowledgeBase(data_root=tmp_path / "raw", annotation_root=tmp_path / "annotations")
