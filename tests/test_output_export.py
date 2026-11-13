import json
from pathlib import Path

from src.output_export import export_outputs


def test_export_keeps_intermediate_outputs_aligned_with_inputs(tmp_path):
    (tmp_path / 'input').mkdir()
    (tmp_path / 'data' / 'grammar').mkdir(parents=True)
    (tmp_path / 'input' / 'sentences.txt').write_text(
        'Môn NLP có bao nhiêu tín chỉ?\nTuần 3 học gì?\n', encoding='utf-8'
    )
    grammar = Path(__file__).resolve().parents[1] / 'data' / 'grammar' / 'grammar_v1.yaml'
    (tmp_path / 'data' / 'grammar' / 'grammar_v1.yaml').write_text(
        grammar.read_text(encoding='utf-8'), encoding='utf-8'
    )

    assert export_outputs(tmp_path) == 2
    output = tmp_path / 'output'
    for name in ('semantic.txt', 'intent-entity.txt', 'query.txt', 'retrieval.txt', 'answer.txt'):
        assert len((output / name).read_text(encoding='utf-8').splitlines()) == 2
    answers = (output / 'answer.txt').read_text(encoding='utf-8').splitlines()
    assert '3 tín chỉ' in answers[0]
    assert 'context-free grammar' in answers[1] and 'schedule:WEEK_03' in answers[1]
    assert len(json.loads((output / 'dialogue.txt').read_text(encoding='utf-8'))) == 3
