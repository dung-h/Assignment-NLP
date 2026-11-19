"""Mutation tests for the evaluator, independent of the production pipeline."""

from copy import deepcopy

import pytest
import yaml

from src.evaluation.gold import GoldCase, evaluate_case, load_gold_cases, summarize


def case():
    return GoldCase('MUTATION', 'test', 'regression', 'independent', {
        'parser': {'valid': True, 'query_frame': 'ASK_PERMISSION', 'sentence_type': 'YES_NO_QUESTION',
                   'slots': {'regulation': ['dùng LLM/RAG']}, 'tree': 'non_empty'},
        'semantic': {'intent': 'GET_RULE', 'entities': {'regulation': ['LLM_RAG']},
                     'attribute': 'permission', 'answer_mode': 'BOOLEAN'},
        'retrieval': {'status': 'FOUND', 'values': [True], 'sources': ['regulations:LLM_RAG']},
        'answer': {'contains': ['Có.'], 'exact': 'Có. Nguồn: regulations:LLM_RAG.'},
    }, ['data/raw/regulations.txt'])


def response():
    return {
        'person_1_parser_result': {'valid': True, 'query_frame': 'ASK_PERMISSION',
            'sentence_type': 'YES_NO_QUESTION', 'slots': {'regulation': ['dùng LLM/RAG']},
            'tree': '(S (SENTENCE_TYPE YES_NO_QUESTION) (QUERY_FRAME ASK_PERMISSION) (REGULATION dùng LLM/RAG))'},
        'person_2_semantic_query': deepcopy(case().expected['semantic']),
        'person_3_retrieval_result': deepcopy(case().expected['retrieval']),
        'answer': 'Có. Nguồn: regulations:LLM_RAG.',
    }


class FakeAssistant:
    def __init__(self, output):
        self.output = output

    def ask(self, query):
        return self.output


@pytest.mark.parametrize('value', [1, 'true', False, None])
def test_boolean_type_corruption_is_a_retrieval_failure(value):
    output = response()
    output['person_3_retrieval_result']['values'] = [value]
    assert not evaluate_case(FakeAssistant(output), case()).layer_ok['retrieval']


@pytest.mark.parametrize('mutation', ['extra_value', 'wrong_source', 'extra_source', 'bad_tree', 'extra_claim'])
def test_corrupted_output_cannot_pass(mutation):
    output = response()
    if mutation == 'extra_value':
        output['person_3_retrieval_result']['values'].append(False)
    elif mutation == 'wrong_source':
        output['person_3_retrieval_result']['sources'] = ['regulations:AI_USAGE']
    elif mutation == 'extra_source':
        output['person_3_retrieval_result']['sources'].append('invented:source')
    elif mutation == 'bad_tree':
        output['person_1_parser_result']['tree'] = 'not a tree'
    else:
        output['answer'] += ' Deadline là ngày mai.'
    assert not evaluate_case(FakeAssistant(output), case()).passed


def test_pipeline_exception_preserves_denominator_without_fabricating_layer_scores():
    class BrokenAssistant:
        def ask(self, query):
            raise RuntimeError('failed after parsing')
    result = evaluate_case(BrokenAssistant(), case())
    assert not result.passed
    assert all(value is None for value in result.layer_ok.values())
    assert summarize([result])['total'] == 1


def test_empty_oracle_is_rejected(tmp_path):
    path = tmp_path / 'gold.yaml'
    path.write_text(yaml.safe_dump({'version': 1, 'scope_frames': [], 'cases': [{
        'id': 'EMPTY', 'query': 'test', 'split': 'regression', 'group': 'independent',
        'provenance': ['data/raw/topics.txt'], 'expected': {},
    }]}), encoding='utf-8')
    with pytest.raises(ValueError):
        load_gold_cases(path)
