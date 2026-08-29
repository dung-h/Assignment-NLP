from src.syntax.parser import RuleParser
from src.semantics.semantic_mapper import SemanticMapper
from src.knowledge.loader import KnowledgeBase
from src.knowledge.query_engine import QueryEngine
from src.answer.generator import AnswerGenerator, OUT_OF_SCOPE_ANSWER
from src.contracts import ContextState, RetrievalResult

class CourseAssistant:
    def __init__(self):
        self.parser=RuleParser(); self.mapper=SemanticMapper(); self.kb=KnowledgeBase(); self.query=QueryEngine(self.kb); self.answerer=AnswerGenerator(); self.context=ContextState()
    def reset_context(self): self.context=ContextState()
    def ask(self,text):
        p=self.parser.parse(text)
        s,self.context=self.mapper.map(p,self.context)
        # UNKNOWN is a semantic-layer result and must not cross into the
        # Person 3 retrieval or answer-rendering boundary.  Keep an empty
        # result only for the output envelope.
        if s.intent == 'UNKNOWN':
            r=RetrievalResult('NOT_FOUND',[],[])
            a=OUT_OF_SCOPE_ANSWER
        else:
            r=self.query.execute(s)
            a=self.answerer.generate(s,r,self.kb)
        return {'input':text,'person_1_parser_result':p.to_dict(),'person_2_semantic_query':s.to_dict(),'context_state':self.context.to_dict(),'person_3_retrieval_result':r.to_dict(),'answer':a}
