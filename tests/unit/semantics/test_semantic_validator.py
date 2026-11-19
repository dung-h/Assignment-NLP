import pytest
from pathlib import Path
from src.contracts import SemanticQuery
from src.semantics.semantic_query_validator import (
    SemanticQueryValidator, InvalidSemanticQuery, ContractDefinitionError,
)


@pytest.fixture
def validator():
    return SemanticQueryValidator()


class TestValidatorBasic:
    def test_valid_course_credits(self, validator):
        q = SemanticQuery('GET_COURSE_INFO', {}, 'credits', 'VALUE')
        frame = validator.validate(q)
        assert frame == 'ASK_COURSE_ATTRIBUTE'

    def test_unknown_raises(self, validator):
        q = SemanticQuery('UNKNOWN', {}, None, 'VALUE')
        with pytest.raises(InvalidSemanticQuery):
            validator.validate(q)

    def test_invalid_type_raises(self, validator):
        with pytest.raises(InvalidSemanticQuery):
            validator.validate("not a query")


class TestValidatorFrames:
    def test_chapter_by_topic(self, validator):
        q = SemanticQuery('GET_TOPIC', {'topic': ['CFG']}, 'chapter', 'LIST')
        assert validator.validate(q) == 'ASK_CHAPTER_BY_TOPIC'

    def test_permission(self, validator):
        q = SemanticQuery('GET_RULE', {'regulation': ['LLM_RAG']}, 'permission', 'BOOLEAN')
        assert validator.validate(q) == 'ASK_PERMISSION'


class TestValidatorErrors:
    def test_no_matching_frame(self, validator):
        q = SemanticQuery('GET_COURSE_INFO', {'unknown': ['X']}, 'credits', 'VALUE')
        with pytest.raises(InvalidSemanticQuery):
            validator.validate(q)

    def test_extra_entity(self, validator):
        # credits không cần entity nào
        q = SemanticQuery('GET_COURSE_INFO', {'chapter': ['CH04']}, 'credits', 'VALUE')
        with pytest.raises(InvalidSemanticQuery):
            validator.validate(q)