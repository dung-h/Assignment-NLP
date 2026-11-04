"""Check the exported submission artifacts against their input and grammar."""

from pathlib import Path
import json
import sys
import argparse
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nltk.tree import Tree
from src.syntax.parser import RuleParser
from src.evaluation.gold import load_gold_cases


def verify():
    output = ROOT / 'output'
    queries = [line for line in (ROOT / 'input/sentences.txt').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert (output / 'grammar.txt').read_text(encoding='utf-8') == (ROOT / 'data/grammar/grammar_v1.yaml').read_text(encoding='utf-8')
    samples = (output / 'samples.txt').read_text(encoding='utf-8').splitlines()
    parser = RuleParser()
    assert 0 < len(samples) <= 10000
    assert len(samples) == len(set(item.casefold() for item in samples))
    assert all(parser.parse(item).valid for item in samples)
    trees = (output / 'parse-results.txt').read_text(encoding='utf-8').strip().split('\n\n')
    assert len(trees) == len(queries)
    for query, tree in zip(queries, trees):
        parsed = parser.parse(query)
        assert (tree == '()') is (not parsed.valid)
        if parsed.valid:
            assert Tree.fromstring(tree).label() == 'S'
    for name in ('semantic.txt', 'intent-entity.txt', 'query.txt', 'retrieval.txt', 'answer.txt'):
        assert len((output / name).read_text(encoding='utf-8').splitlines()) == len(queries), name
    results = [json.loads(line) for line in (output / 'retrieval.txt').read_text(encoding='utf-8').splitlines()]
    answers = (output / 'answer.txt').read_text(encoding='utf-8').splitlines()
    for result, answer in zip(results, answers):
        assert isinstance(result['values'], list) and isinstance(result['sources'], list)
        if result['status'] == 'FOUND':
            assert result['values'] and result['sources']
            assert all(source in answer for source in result['sources'])
        else:
            assert result == {'status': 'NOT_FOUND', 'values': [], 'sources': []}
    dialogues = json.loads((output / 'dialogue.txt').read_text(encoding='utf-8'))
    assert dialogues and all(len(turns) >= 2 for turns in dialogues)
    _, cases = load_gold_cases()
    traces = json.loads((output / 'gold_results.json').read_text(encoding='utf-8'))
    assert {row['id'] for row in traces} == {case.case_id for case in cases}
    assert all(row['passed'] for row in traces), 'Gold evaluation contains failed cases'
    print(f'Verified {len(queries)} inputs, {len(samples)} generated sentences, {len(cases)} gold turns and {len(dialogues)} dialogues.')


if __name__ == '__main__':
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--regenerate', action='store_true', help='Run all exporters in this environment before checking artifacts')
    args = arguments.parse_args()
    if args.regenerate:
        for script, extra in (
            ('export_required_outputs.py', []), ('run_samples.py', []),
            ('evaluate_gold.py', ['--strict']),
        ):
            subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *extra], cwd=ROOT, check=True)
    verify()
