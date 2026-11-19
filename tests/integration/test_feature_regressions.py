"""Acceptance checks for the remaining assignment requirements."""

import pytest
from nltk.tree import Tree

from src.assistant import CourseAssistant
from src.semantics.normalizer import canonical
from src.syntax.generator import generate
from src.syntax.parser import RuleParser
from src.knowledge.index_builder import build_indexes


@pytest.mark.parametrize('number,title', [
    ('I', 'Grammar and Parser'), ('II', 'Semantic Interpretation and QA'),
    ('III', 'Local Discourse Context'), ('IV', 'Evaluation'),
])
def test_assignment_part_is_not_swallowed_by_generic_assignment(number, title):
    result = CourseAssistant().ask(f'Phần {number} của bài tập lớn là gì?')
    assert result['person_1_parser_result']['query_frame'] == 'ASK_ASSIGNMENT_PART_INFO'
    assert result['person_3_retrieval_result']['values'] == [title]


@pytest.mark.parametrize('number,expected', [('I', 1), ('II', 2), ('III', 3), ('IV', 4)])
def test_roman_part_id(number, expected):
    assert canonical('assignment_part', f'Phần {number}') == f'BTL_PART_{expected}'


def test_ellipsis_inherits_topic_predicate_and_moves_to_next_chapter():
    bot = CourseAssistant()
    bot.ask('Chương 11 có hỏi đáp không?')
    response = bot.ask('Còn chương sau?')
    assert response['person_2_semantic_query'] == {
        'intent': 'GET_TOPIC', 'entities': {'chapter': ['CH12'], 'topic': ['QUESTION_ANSWERING']},
        'attribute': 'contains_topic', 'answer_mode': 'BOOLEAN',
    }
    assert response['person_3_retrieval_result'] == {
        'status': 'FOUND', 'values': [False], 'sources': ['topics:CH12'],
    }


def test_ellipsis_has_no_invented_predicate_after_reset():
    bot = CourseAssistant()
    bot.ask('Chương 11 có hỏi đáp không?')
    bot.reset_context()
    assert bot.ask('Còn chương sau?')['person_2_semantic_query']['intent'] == 'UNKNOWN'


def test_component_reference_uses_unique_assignment_part_from_kb():
    bot = CourseAssistant()
    bot.ask('Bài tập lớn có phần parser không?')
    response = bot.ask('Phần này cần xuất file gì?')
    assert response['person_2_semantic_query']['entities'] == {'assignment_part': ['BTL_PART_1']}
    assert response['person_3_retrieval_result']['values'] == [
        'output/grammar.txt', 'output/samples.txt', 'output/parse-results.txt',
    ]


def test_false_component_does_not_reuse_an_old_part():
    bot = CourseAssistant()
    bot.ask('Phần I của bài tập lớn là gì?')
    bot.ask('BTL có phần RAG không?')
    assert bot.ask('Phần này cần xuất file gì?')['person_2_semantic_query']['intent'] == 'UNKNOWN'


def test_ambiguous_component_parts_do_not_pick_the_first_match():
    bot = CourseAssistant()
    bot.kb.assignment_parts['BTL_PART_4']['requirements'].append('xây dựng parser')
    build_indexes(bot.kb)
    bot.ask('Bài tập lớn có phần parser không?')
    assert bot.ask('Phần này cần xuất file gì?')['person_2_semantic_query']['intent'] == 'UNKNOWN'


def test_ellipsis_does_not_inherit_across_an_unrelated_question():
    bot = CourseAssistant()
    bot.ask('Chương 11 có hỏi đáp không?')
    bot.ask('Môn NLP có bao nhiêu tín chỉ?')
    assert bot.ask('Còn chương sau?')['person_2_semantic_query']['intent'] == 'UNKNOWN'


def test_generation_uses_lexical_examples_from_the_selected_grammar(tmp_path):
    import yaml
    from src.syntax.grammar import DEFAULT_GRAMMAR
    spec = yaml.safe_load(DEFAULT_GRAMMAR.read_text(encoding='utf-8'))
    spec['lexicon']['COURSE']['examples'] = ['CO3085']
    path = tmp_path / 'grammar.yaml'
    path.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding='utf-8')
    questions = generate(10000, grammar_path=path)
    assert len(questions) == len(set(item.casefold() for item in questions))
    parser = RuleParser(path)
    assert all(parser.parse(item).valid for item in questions)
    assert all(parser.parse(item).slots.get('course', ['CO3085']) == ['CO3085'] for item in questions)


def test_generator_detects_recursive_grammar(tmp_path):
    import yaml
    from src.syntax.grammar import DEFAULT_GRAMMAR
    spec = yaml.safe_load(DEFAULT_GRAMMAR.read_text(encoding='utf-8'))
    spec['productions']['CREDIT_QUERY'] = [['CREDIT_QUERY']]
    path = tmp_path / 'recursive.yaml'
    path.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding='utf-8')
    with pytest.raises(ValueError, match='Recursive'):
        generate(grammar_path=path)


@pytest.mark.parametrize('text', [
    'Chương nào nói về CFG? rồi dự báo thời tiết',
    'Dự báo thời tiết và môn NLP có bao nhiêu tín chỉ?',
])
def test_parser_does_not_accept_valid_substring_inside_unrelated_input(text):
    assert not RuleParser().parse(text).valid


def test_parser_tree_has_grammar_derivation():
    result = RuleParser().parse('Môn NLP có bao nhiêu tín chỉ?')
    tree = Tree.fromstring(result.tree)
    assert any(node.label() == 'CREDIT_QUERY' for node in tree.subtrees())


def test_generator_expands_more_than_fixed_examples_and_respects_limit():
    assert len(generate(80)) == 80
    assert generate(0) == []
    assert generate(10) == generate(10)
    with pytest.raises(ValueError):
        generate(-1)
