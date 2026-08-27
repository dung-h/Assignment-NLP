from src.assistant import CourseAssistant

def test_credit():
    o=CourseAssistant().ask('Môn NLP có bao nhiêu tín chỉ?')
    assert o['person_1_parser_result']['valid']
    assert o['person_2_semantic_query']['intent']=='GET_COURSE_INFO'
    assert o['person_3_retrieval_result']['values']==[3]

def test_cfg():
    o=CourseAssistant().ask('Chương nào nói về CFG?')
    assert 'CH03' in o['person_3_retrieval_result']['values']

def test_rule():
    o=CourseAssistant().ask('Có được dùng LLM/RAG không?')
    assert o['person_2_semantic_query']['intent']=='GET_RULE'
    assert o['person_3_retrieval_result']['status']=='FOUND'

def test_missing_instructor_not_unknown():
    o=CourseAssistant().ask('Ai dạy môn NLP?')
    assert o['person_2_semantic_query']['intent']=='GET_INSTRUCTOR'
    assert o['person_3_retrieval_result']['status']=='NOT_FOUND'

def test_context_pronoun():
    b=CourseAssistant(); b.ask('Chương 4 nói về gì?'); o=b.ask('Nó có liên quan đến parsing không?')
    assert o['person_2_semantic_query']['entities']['chapter']==['CH04']

def test_unknown():
    o=CourseAssistant().ask('Hôm nay ở TP.HCM có mưa không?')
    assert o['person_2_semantic_query']['intent']=='UNKNOWN'

def test_ui_builds():
    from app import build_ui
    ui=build_ui(CourseAssistant())
    assert ui is not None
