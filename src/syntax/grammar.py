"""Executable acyclic phrase productions, with regex at lexical leaves."""

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import re
import unicodedata
import yaml
from nltk.tree import Tree

DEFAULT_GRAMMAR = Path(__file__).resolve().parents[2] / 'data/grammar/grammar_v1.yaml'


@dataclass(frozen=True)
class Branch:
    symbol: str
    children: tuple


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


class PhraseGrammar:
    def __init__(self, path=None):
        self.spec = yaml.safe_load(Path(path or DEFAULT_GRAMMAR).read_text(encoding='utf-8'))
        self.lexicon = self.spec.get('lexicon', {})
        self.productions = self.spec.get('productions', {})
        if self.spec.get('start') != 'S' or not self.lexicon or not self.productions:
            raise ValueError('Grammar requires start S, lexicon and productions')
        for name, entry in self.lexicon.items():
            examples = entry.get('examples', [])
            if not examples or any(not isinstance(item, str) or not item for item in examples):
                raise ValueError(f'{name}: lexical examples must be non-empty strings')
            pattern = re.compile(entry['pattern'], re.IGNORECASE)
            if any(pattern.fullmatch(normalize(example)) is None for example in examples):
                raise ValueError(f'{name}: lexical example does not match its pattern')
        self.rules = []
        for rule in self.spec['rules']:
            for branch in self.expand(rule['production']):
                leaves = []
                expression = self._compile(branch, leaves)
                self.rules.append((rule, branch, leaves, re.compile(expression + r'[?.]?', re.IGNORECASE)))

    def expand(self, symbol, stack=()):
        if symbol not in self.productions:
            if symbol not in self.lexicon and symbol.isupper():
                raise ValueError(f'Undefined grammar symbol {symbol}')
            yield symbol
            return
        if symbol in stack:
            raise ValueError(f'Recursive production is outside the finite grammar: {symbol}')
        for sequence in self.productions[symbol]:
            if not isinstance(sequence, list) or not sequence:
                raise ValueError(f'{symbol}: production must be a non-empty sequence')
            choices = [list(self.expand(child, (*stack, symbol))) for child in sequence]
            for children in product(*choices):
                yield Branch(symbol, children)

    def _compile(self, node, leaves):
        if isinstance(node, Branch):
            return r'\s+'.join(self._compile(child, leaves) for child in node.children)
        name = f'leaf_{len(leaves)}'
        leaves.append((node, name))
        pattern = self.lexicon[node]['pattern'] if node in self.lexicon else re.escape(node).replace(r'\ ', r'\s+')
        return f'(?P<{name}>{pattern})'

    def tree(self, branch, leaves, match, split_values):
        iterator, slots = iter(leaves), {}

        def walk(node):
            if isinstance(node, Branch):
                return Tree(node.symbol, [walk(child) for child in node.children])
            symbol, group = next(iterator)
            raw = match.group(group)
            slot = self.lexicon.get(symbol, {}).get('slot')
            if slot:
                values = split_values(slot, raw)
                slots.setdefault(slot, []).extend(values)
                return Tree(slot.upper(), values)
            return Tree(symbol if symbol in self.lexicon else 'LITERAL', raw.split())

        return_tree = walk(branch)
        return return_tree, slots

    def examples(self, branch):
        def leaves(node):
            if isinstance(node, Branch):
                for child in node.children:
                    yield from leaves(child)
            else:
                yield self.lexicon[node]['examples'] if node in self.lexicon else [node]
        for parts in product(*leaves(branch)):
            yield ' '.join(parts) + '?'
