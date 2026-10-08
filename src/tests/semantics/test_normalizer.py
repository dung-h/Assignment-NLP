import pytest
from src.semantics.normalizer import fold, canonical


class TestFold:
    def test_lowercase(self):
        assert fold("NLP") == "nlp"

    def test_strip(self):
        assert fold("  NLP  ") == "nlp"

    def test_remove_diacritics(self):
        assert fold("hỏi đáp") == "hoi đap"
        assert fold("tín chỉ") == "tin chi"

    def test_collapse_whitespace(self):
        assert fold("a   b") == "a b"

    def test_empty(self):
        assert fold("") == ""


class TestCanonicalCourse:
    def test_nlp_variants(self):
        assert canonical('course', 'NLP') == 'CO3085'
        assert canonical('course', 'môn NLP') == 'CO3085'
        assert canonical('course', 'CO3085') == 'CO3085'

    def test_unknown_course(self):
        assert canonical('course', 'PHY101') == 'PHY101'


class TestCanonicalWeek:
    def test_vietnamese(self):
        assert canonical('week', 'tuần 3') == 'WEEK_03'
        assert canonical('week', 'Tuần 12') == 'WEEK_12'

    def test_number_only(self):
        assert canonical('week', '3') == 'WEEK_03'

    def test_no_number(self):
        assert canonical('week', 'tuần sau') == 'tuần sau'


class TestCanonicalChapter:
    def test_vietnamese(self):
        assert canonical('chapter', 'chương 4') == 'CH04'
        assert canonical('chapter', 'Chương 12') == 'CH12'


class TestCanonicalAssignment:
    def test_btl(self):
        assert canonical('assignment', 'bài tập lớn') == 'BTL01'
        assert canonical('assignment', 'BTL') == 'BTL01'


class TestCanonicalAssignmentPart:
    def test_roman(self):
        assert canonical('assignment_part', 'phần I') == 'BTL_PART_1'
        assert canonical('assignment_part', 'phần III') == 'BTL_PART_3'

    def test_arabic(self):
        assert canonical('assignment_part', 'phần 2') == 'BTL_PART_2'

    def test_invalid_returns_value(self):
        # Sau khi fix bug, không còn trả None
        result = canonical('assignment_part', 'phần nào đó')
        assert result is not None


class TestCanonicalTopic:
    def test_alias(self):
        assert canonical('topic', 'CFG') == 'CFG'
        assert canonical('topic', 'context-free grammar') == 'CFG'
        assert canonical('topic', 'hỏi đáp') == 'QUESTION_ANSWERING'
        assert canonical('topic', 'parsing') == 'PARSING'

    def test_fallback(self):
        assert canonical('topic', 'some new topic') == 'SOME_NEW_TOPIC'


class TestCanonicalRegulation:
    def test_alias(self):
        assert canonical('regulation', 'LLM/RAG') == 'LLM_RAG'
        assert canonical('regulation', 'dùng LLM/RAG') == 'LLM_RAG'

    def test_no_false_positive(self):
        # 'ai' không nên match trong 'fair use'
        result = canonical('regulation', 'fair use')
        assert result != 'AI_USAGE'


class TestCanonicalLearningOutcome:
    def test_formats(self):
        assert canonical('learning_outcome', 'LO2.5') == 'LO2.5'
        assert canonical('learning_outcome', 'L.O.2.5') == 'LO2.5'
        assert canonical('learning_outcome', '2.5') == 'LO2.5'
