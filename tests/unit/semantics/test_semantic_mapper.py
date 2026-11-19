import pytest
from src.contracts import ParserResult, ContextState, SemanticQuery
from src.semantics.semantic_mapper import SemanticMapper, attribute_from_cue


def make_parsed(frame, slots=None, valid=True):
    return ParserResult(
        valid=valid,
        sentence_type="WH_QUESTION" if valid else None,
        query_frame=frame if valid else None,
        slots=slots or {},
        tree="(S ...)" if valid else None,
    )


class TestAttributeFromCue:
    def test_course_credits(self):
        assert attribute_from_cue('ASK_COURSE_ATTRIBUTE', 'tín chỉ') == 'credits'

    def test_course_department(self):
        assert attribute_from_cue('ASK_COURSE_ATTRIBUTE', 'khoa') == 'department'

    def test_exam_duration(self):
        assert attribute_from_cue('ASK_EXAM_ATTRIBUTE', 'phút') == 'duration'

    def test_no_cue(self):
        assert attribute_from_cue('ASK_COURSE_ATTRIBUTE', '') is None


class TestSemanticMapperBasic:
    def setup_method(self):
        self.mapper = SemanticMapper()

    def test_invalid_parsed_returns_unknown(self):
        parsed = make_parsed(None, valid=False)
        q, ctx = self.mapper.map(parsed)
        assert q.intent == 'UNKNOWN'

    def test_course_credits(self):
        parsed = make_parsed('ASK_COURSE_ATTRIBUTE', {'attribute_cue': ['tín chỉ']})
        q, ctx = self.mapper.map(parsed)
        assert q.intent == 'GET_COURSE_INFO'
        assert q.attribute == 'credits'
        assert q.answer_mode == 'VALUE'
        assert q.entities == {}

    def test_chapter_by_topic(self):
        parsed = make_parsed('ASK_CHAPTER_BY_TOPIC', {'topic': ['CFG']})
        q, ctx = self.mapper.map(parsed)
        assert q.intent == 'GET_TOPIC'
        assert q.attribute == 'chapter'
        assert q.answer_mode == 'LIST'
        assert q.entities == {'topic': ['CFG']}


class TestSemanticMapperReference:
    def setup_method(self):
        self.mapper = SemanticMapper()

    def test_chapter_sau(self):
        ctx = ContextState([{'type': 'chapter', 'id': 'CH04'}])
        parsed = make_parsed('ASK_CHAPTER_CONTENT', {'reference': ['chương sau']})
        q, new_ctx = self.mapper.map(parsed, ctx)
        assert q.entities == {'chapter': ['CH05']}

    def test_reference_no_context(self):
        ctx = ContextState([])
        parsed = make_parsed('ASK_CHAPTER_CONTENT', {'reference': ['nó']})
        q, new_ctx = self.mapper.map(parsed, ctx)
        assert q.entities == {}


class TestContextUpdate:
    def setup_method(self):
        self.mapper = SemanticMapper()

    def test_context_updated_with_entity(self):
        parsed = make_parsed('ASK_CHAPTER_CONTENT', {'chapter': ['Chương 4']})
        q, ctx = self.mapper.map(parsed)
        assert ctx.focus_entities == [{'type': 'chapter', 'id': 'CH04'}]

    def test_context_kept_when_no_entity(self):
        old_ctx = ContextState([{'type': 'chapter', 'id': 'CH04'}])
        parsed = make_parsed('ASK_COURSE_ATTRIBUTE', {'attribute_cue': ['tín chỉ']})
        q, ctx = self.mapper.map(parsed, old_ctx)
        assert ctx.focus_entities == [{'type': 'chapter', 'id': 'CH04'}]