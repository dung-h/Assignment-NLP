import json
from pathlib import Path

import pytest

from src.contracts import SemanticQuery
from src.semantics.semantic_query_validator import (
    ContractDefinitionError,
    InvalidSemanticQuery,
    SemanticQueryValidator,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "mock_cases" / "person3.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
RETRIEVAL_CASES = [
    case for case in CASES if case.get("test_kind", "retrieval") == "retrieval"
]


@pytest.fixture(scope="module")
def validator():
    return SemanticQueryValidator()


@pytest.mark.parametrize("case", RETRIEVAL_CASES, ids=[case["id"] for case in RETRIEVAL_CASES])
def test_retrieval_queries_match_exactly_one_query_frame(case, validator):
    query = SemanticQuery(**case["input_semantic_query"])
    assert validator.validate(query)


def test_unknown_entity_id_is_not_a_contract_error(validator):
    query = SemanticQuery(
        "GET_TOPIC",
        {"chapter": ["CH99"]},
        "summary",
        "VALUE",
    )
    assert validator.validate(query) == "ASK_CHAPTER_CONTENT"


def test_unsupported_attribute_is_an_invalid_semantic_query(validator):
    query = SemanticQuery(
        "GET_SCHEDULE",
        {"week": ["WEEK_03"]},
        "unsupported_attribute",
        "VALUE",
    )
    with pytest.raises(InvalidSemanticQuery):
        validator.validate(query)


def test_unknown_intent_does_not_enter_retrieval(validator):
    query = SemanticQuery("UNKNOWN", {}, None, "VALUE")
    with pytest.raises(InvalidSemanticQuery):
        validator.validate(query)


def test_contract_definition_rejects_duplicate_matching_frames(tmp_path):
    contract = tmp_path / "query_frames.yaml"
    contract.write_text(
        """version: 1
frames:
  FIRST: {intent: GET_TOPIC, required: [topic], optional: [], attribute: chapter, answer_mode: LIST}
  SECOND: {intent: GET_TOPIC, required: [topic], optional: [], attribute: chapter, answer_mode: LIST}
""",
        encoding="utf-8",
    )
    validator = SemanticQueryValidator(contract)
    query = SemanticQuery("GET_TOPIC", {"topic": ["CFG"]}, "chapter", "LIST")
    with pytest.raises(ContractDefinitionError):
        validator.validate(query)
