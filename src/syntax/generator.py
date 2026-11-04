"""Bounded, deterministic generation from executable productions."""

from itertools import zip_longest
from .grammar import PhraseGrammar


def generate(limit=10000, grammar_path=None):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError('limit must be a non-negative integer')
    limit = min(limit, 10000)
    if limit == 0:
        return []
    grammar = PhraseGrammar(grammar_path)
    iterators = [grammar.examples(branch) for rule, branch, _, _ in grammar.rules if rule['frame'] is not None]
    result, seen = [], set()
    for batch in zip_longest(*iterators):
        for sentence in batch:
            if sentence is None or sentence.casefold() in seen:
                continue
            seen.add(sentence.casefold())
            result.append(sentence)
            if len(result) >= limit:
                return result
    return result
