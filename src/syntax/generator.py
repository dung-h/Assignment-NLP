from pathlib import Path

from .parser import RuleParser


ROOT = Path(__file__).resolve().parents[2]

TEMPLATES = (
    'Môn NLP có bao nhiêu tín chỉ?',
    'Tuần 3 học gì?',
    'Chương 4 học vào tuần nào?',
    'Chương nào nói về CFG?',
    'Chương 12 nói về gì?',
    'Bài tập lớn có phần parser không?',
    'Có được dùng LLM/RAG không?',
    'Tài liệu tham khảo về statistical NLP là gì?',
    'L.O.2.5 là gì?',
    'Ai dạy môn NLP?',
)


def generate(limit=10000, grammar_path=None):
    """Return valid example sentences accepted by the configured grammar."""
    parser = RuleParser(grammar_path or ROOT / 'data' / 'grammar' / 'grammar_v1.yaml')
    samples = [sentence for sentence in TEMPLATES if parser.parse(sentence).valid]
    if len(samples) != len(TEMPLATES):
        raise ValueError('The sentence generator contains samples rejected by the grammar')
    return samples[:limit]
