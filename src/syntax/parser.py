"""Recognize complete utterances and export their phrase derivation."""

import re
from nltk.tree import Tree
from src.contracts import ParserResult
from .grammar import PhraseGrammar, normalize


class RuleParser:
    def __init__(self, grammar_path=None):
        self.grammar = PhraseGrammar(grammar_path)
        self.spec = self.grammar.spec

    @staticmethod
    def _split_values(slot, raw):
        raw = raw.strip(' ?.,')
        if slot == 'chapter':
            nums = re.findall(r'(?i)chương\s*(\d+)', raw)
            return [f'Chương {n}' for n in nums] if nums else [raw]
        return [item.strip() for item in re.split(r'\s+(?:và|hoặc)\s+|\s*,\s*', raw) if item.strip()]

    def parse(self, sentence):
        if not isinstance(sentence, str) or not sentence.strip():
            return ParserResult(False, None, None, {}, None)
        text = normalize(sentence)
        for rule, branch, leaves, pattern in self.grammar.rules:
            match = pattern.fullmatch(text)
            if match is None:
                continue
            derivation, slots = self.grammar.tree(branch, leaves, match, self._split_values)
            metadata = [Tree('SENTENCE_TYPE', [rule['sentence_type']])]
            if rule['frame'] is not None:
                metadata.append(Tree('QUERY_FRAME', [rule['frame']]))
            tree = Tree('S', [*metadata, derivation])
            return ParserResult(True, rule['sentence_type'], rule['frame'], slots, tree.pformat(margin=120))
        return ParserResult(False, None, None, {}, None)
