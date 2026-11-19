from src.syntax.generator import generate
from src.syntax.parser import RuleParser


def test_generated_sentences_are_accepted_by_grammar():
    parser = RuleParser()
    samples = generate()

    assert samples
    assert all(parser.parse(sentence).valid for sentence in samples)


def test_parser_extracts_slots_and_parse_tree():
    result = RuleParser().parse('L.O.2.5 là gì?')

    assert result.valid
    assert result.query_frame == 'ASK_LO_DESCRIPTION'
    assert result.slots == {'learning_outcome': ['L.O.2.5']}
    assert '(QUERY_FRAME ASK_LO_DESCRIPTION)' in result.tree


def test_parser_rejects_invalid_input():
    parser = RuleParser()

    for sentence in ('', '   ', 'Hôm nay ở TP.HCM có mưa không?', None):
        result = parser.parse(sentence)
        assert not result.valid
        assert result.tree is None
