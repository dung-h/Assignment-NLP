from pathlib import Path
from shutil import copytree

import pytest

from src.knowledge.loader import KnowledgeBase, KnowledgeBaseLoader
from src.knowledge.loader import KBValidationError


ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = ROOT / "data" / "raw"
ANNOTATION_DATA = ROOT / "data" / "annotations"


def test_loader_has_expected_course_and_schedule_inventory():
    kb = KnowledgeBase()

    assert kb.course["course_id"] == "CO3085"
    assert kb.course["credits"] == 3
    assert len(kb.weeks) == 15
    assert len(kb.chapters) == 12


def test_loader_has_assignment_resources_and_learning_outcomes():
    kb = KnowledgeBase()

    assert kb.assignments["BTL01"]["team_size"] == "3-4 students"
    assert kb.assignment_parts["BTL_PART_1"]["outputs"] == [
        "output/grammar.txt",
        "output/samples.txt",
        "output/parse-results.txt",
    ]
    assert kb.resources["RES02"]["title"] == "Introduction to Natural Language Processing"
    assert kb.los["LO2.5"]["description"] == (
        "Kiến thức xác suất để giải quyết nhập nhằng từ ở mức câu."
    )


def test_missing_sample_domains_remain_empty():
    kb = KnowledgeBase()

    assert kb.instructors == {}
    assert not hasattr(kb, "deadlines") or kb.deadlines == {}


def test_loader_builds_deterministic_derived_indexes():
    kb = KnowledgeBase()

    assert kb.indexes.topic_to_chapters["CFG"] == ["CH03"]
    assert kb.indexes.topic_to_chapters["PCFG"] == ["CH03", "CH06"]
    assert kb.indexes.chapter_to_weeks["CH04"] == ["WEEK_04", "WEEK_05"]
    assert kb.indexes.topic_to_weeks["PCFG"] == ["WEEK_03", "WEEK_07"]
    assert kb.indexes.course_part_to_chapters["COURSE_PART_1"] == [
        "CH02", "CH03", "CH04", "CH05", "CH06"
    ]
    assert "PARSING" in kb.indexes.chapter_to_topics["CH04"]
    assert kb.indexes.topic_to_resources["STATISTICAL_NLP"] == ["RES02", "RES04"]


def test_loader_omits_missing_optional_fields_and_keeps_exam_relation(tmp_path):
    data_root = tmp_path / "raw"
    copytree(RAW_DATA, data_root)
    copytree(ANNOTATION_DATA, tmp_path / "annotations")
    course_info = data_root / "course_info.txt"
    course_info.write_text(
        course_info.read_text(encoding="utf-8").replace("ects: 6\n", ""),
        encoding="utf-8",
    )

    kb = KnowledgeBaseLoader(data_root).load()

    assert "ects" not in kb.course
    assert "exams" not in kb.course
    assert kb.course["exam_ids"] == ["MIDTERM", "FINAL"]
    assert "activity" not in kb.weeks["WEEK_01"]
    assert "milestone" not in kb.weeks["WEEK_01"]
    assert "author" not in kb.resources["RES01"]
    assert "publisher" not in kb.resources["RES01"]
    assert kb.exams["MIDTERM"]["duration"] == 60


def test_loader_rejects_missing_required_course_id(tmp_path):
    data_root = tmp_path / "raw"
    copytree(RAW_DATA, data_root)
    copytree(ANNOTATION_DATA, tmp_path / "annotations")
    course_info = data_root / "course_info.txt"
    course_info.write_text(
        course_info.read_text(encoding="utf-8").replace(
            "course_id: CO3085", "course_id:"
        ),
        encoding="utf-8",
    )

    with pytest.raises(KBValidationError, match="missing course_id"):
        KnowledgeBaseLoader(data_root).load()


def test_loader_materializes_structured_regulation_and_learning_outcome_records():
    kb = KnowledgeBase()

    llm_rule = kb.regulations["LLM_RAG"]
    assert llm_rule["id"] == "LLM_RAG"
    assert llm_rule["permission"] is True
    assert "LLM/RAG" in llm_rule["text"]
    assert kb.regulations["ASSIGNMENT_SHARING"]["permission"] is False
    assert "permission" not in kb.regulations["AI_USAGE"]
    assert kb.learning_outcomes["LO2.5"]["id"] == "LO2.5"
    assert kb.resource_topic_annotations["RES02"]["annotation_type"] == "TEAM_DERIVED"
    assert kb.resource_topic_annotations["RES02"]["basis"]["field"] == "usage"


def test_loader_rejects_annotation_for_unknown_resource(tmp_path):
    data_root = tmp_path / "raw"
    copytree(RAW_DATA, data_root)
    annotation_root = tmp_path / "annotations"
    copytree(ANNOTATION_DATA, annotation_root)
    annotation_file = annotation_root / "resource_topics.yaml"
    annotation_file.write_text(
        annotation_file.read_text(encoding="utf-8").replace("RES04:", "RES99:"),
        encoding="utf-8",
    )

    with pytest.raises(KBValidationError, match="unknown resource ID 'RES99'"):
        KnowledgeBaseLoader(data_root).load()


def test_loader_rejects_stale_annotation_provenance(tmp_path):
    data_root = tmp_path / "raw"
    copytree(RAW_DATA, data_root)
    annotation_root = tmp_path / "annotations"
    copytree(ANNOTATION_DATA, annotation_root)
    resources = data_root / "resources.txt"
    resources.write_text(
        resources.read_text(encoding="utf-8").replace(
            "usage: statistical NLP", "usage: changed usage"
        ),
        encoding="utf-8",
    )

    with pytest.raises(KBValidationError, match="provenance does not match"):
        KnowledgeBaseLoader(data_root).load()
