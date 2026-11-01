from pathlib import Path
import re, yaml
from nltk.tree import Tree
from src.contracts import ParserResult

ROOT = Path(__file__).resolve().parents[2]

class RuleParser:
    def __init__(self, grammar_path=None):
        grammar_path = grammar_path or ROOT/'data/grammar/grammar_v1.yaml'
        self.spec = yaml.safe_load(Path(grammar_path).read_text(encoding='utf-8'))
        self.rules = [
            (rule, [re.compile(pattern) for pattern in rule.get('patterns', [])])
            for rule in self.spec.get('rules', [])
        ]

    @staticmethod
    def _split_values(slot, raw):
        raw = raw.strip(' ?.,')
        if slot == 'chapter':
            nums = re.findall(r'(?i)chương\s*(\d+)', raw)
            return [f'Chương {n}' for n in nums] if nums else [raw]
        return [x.strip() for x in re.split(r'\s+(?:và|hoặc)\s+|\s*,\s*', raw) if x.strip()]

    def parse(self, sentence: str) -> ParserResult:
        if not isinstance(sentence, str):
            return ParserResult(False, None, None, {}, None)
        s = sentence.strip()
        if not s:
            return ParserResult(False, None, None, {}, None)
        for rule, patterns in self.rules:
            for pattern in patterns:
                m = pattern.search(s)
                if not m: continue
                slots={}
                for k,v in m.groupdict().items():
                    if v is not None and k != 'attr':
                        slots[k]=self._split_values(k,v)
                if m.groupdict().get('attr'):
                    slots['attribute_cue']=[m.group('attr')]
                children=[]
                for k, vals in slots.items():
                    children.append(Tree(k.upper(), vals))
                tree=Tree('S',[Tree('SENTENCE_TYPE',[rule['sentence_type']]),Tree('QUERY_FRAME',[rule['frame']]),*children])
                return ParserResult(True, rule['sentence_type'], rule['frame'], slots, tree.pformat(margin=120))
        return ParserResult(False,None,None,{},None)
