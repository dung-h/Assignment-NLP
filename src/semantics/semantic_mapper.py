from src.contracts import SemanticQuery, ContextState
from .normalizer import canonical, fold

FRAME_MAP = {
 'ASK_COURSE_ATTRIBUTE': ('GET_COURSE_INFO',None,'VALUE'),
 'ASK_COURSE_PARTS': ('GET_COURSE_INFO','parts','LIST'),
 'ASK_EXAM_ATTRIBUTE': ('GET_COURSE_INFO',None,'VALUE'),
 'ASK_INSTRUCTOR': ('GET_INSTRUCTOR','name','LIST'),
 'ASK_INSTRUCTOR_ATTRIBUTE': ('GET_INSTRUCTOR',None,'VALUE'),
 'ASK_WEEK_CONTENT': ('GET_SCHEDULE','topics','LIST'),
 'ASK_WEEK_OF_CHAPTER': ('GET_SCHEDULE','week','LIST'),
 'ASK_WEEK_OF_TOPIC': ('GET_SCHEDULE','week','LIST'),
 'ASK_WEEK_ACTIVITY': ('GET_SCHEDULE','activity','VALUE'),
 'ASK_WEEK_MILESTONE': ('GET_SCHEDULE','milestone','VALUE'),
 'ASK_MILESTONE_WEEK': ('GET_SCHEDULE','week','LIST'),
 'ASK_CHAPTER_CONTENT': ('GET_TOPIC','summary','VALUE'),
 'ASK_CHAPTER_TITLE': ('GET_TOPIC','title','VALUE'),
 'ASK_CHAPTER_BY_TOPIC': ('GET_TOPIC','chapter','LIST'),
 'ASK_TOPIC_OF_CHAPTER': ('GET_TOPIC','topics','LIST'),
 'ASK_TOPIC_EXISTENCE_IN_CHAPTER': ('GET_TOPIC','contains_topic','BOOLEAN'),
 'ASK_PART_OF_CHAPTER': ('GET_TOPIC','part','VALUE'),
 'ASK_CHAPTERS_OF_PART': ('GET_TOPIC','chapter','LIST'),
 'ASK_ASSIGNMENT_INFO': ('GET_ASSIGNMENT','goal','VALUE'),
 'ASK_ASSIGNMENT_PARTS': ('GET_ASSIGNMENT','parts','LIST'),
 'ASK_ASSIGNMENT_PART_INFO': ('GET_ASSIGNMENT','title','VALUE'),
 'ASK_ASSIGNMENT_REQUIREMENTS': ('GET_ASSIGNMENT','requirements','LIST'),
 'ASK_ASSIGNMENT_OUTPUTS': ('GET_ASSIGNMENT','outputs','LIST'),
 'ASK_ASSIGNMENT_COMPONENT_EXISTENCE': ('GET_ASSIGNMENT','contains_component','BOOLEAN'),
 'ASK_ASSIGNMENT_TEAM_SIZE': ('GET_ASSIGNMENT','team_size','VALUE'),
 'ASK_ASSIGNMENT_DEADLINE': ('GET_DEADLINE','date','VALUE'),
 'ASK_ASSIGNMENT_PART_DEADLINE': ('GET_DEADLINE','date','VALUE'),
 'ASK_DEADLINE_INFO': ('GET_DEADLINE','date','VALUE'),
 'ASK_RESOURCE_BY_TOPIC': ('GET_RESOURCE','resource','LIST'),
 'ASK_RESOURCE_BY_CHAPTER': ('GET_RESOURCE','resource','LIST'),
 'ASK_RESOURCE_ATTRIBUTE': ('GET_RESOURCE',None,'VALUE'),
 'ASK_REGULATION': ('GET_RULE','policy_text','VALUE'),
 'ASK_PERMISSION': ('GET_RULE','permission','BOOLEAN'),
 'ASK_LO_DESCRIPTION': ('GET_LO','description','VALUE'),
 'ASK_LO_RELATED_CONTENT': ('GET_LO','related_content','LIST'),
 'ASK_CHAPTER_BY_LO': ('GET_LO','chapter','LIST'),
}

def attribute_from_cue(frame,cue):
    c=fold(cue or '')
    if frame=='ASK_COURSE_ATTRIBUTE':
        if 'tin chi' in c: return 'credits'
        if 'khoa' in c: return 'department'
        if 'gio tu hoc' in c: return 'self_study_hours'
    if frame=='ASK_EXAM_ATTRIBUTE':
        if 'phut' in c: return 'duration'
        if 'hinh thuc' in c: return 'format'
        if 'phan tram' in c or 'chiem' in c: return 'weight'
    return None

class SemanticMapper:
    def map(self, parsed, context=None):
        context=context or ContextState()
        if not parsed.valid:
            return SemanticQuery('UNKNOWN',{},None,'VALUE'), context
        intent, attr, mode = FRAME_MAP[parsed.query_frame]
        cue=(parsed.slots.get('attribute_cue') or [''])[0]
        attr=attribute_from_cue(parsed.query_frame,cue) or attr
        entities={}
        for slot, vals in parsed.slots.items():
            if slot=='attribute_cue': continue
            if slot=='reference':
                resolved=self._resolve_reference(vals[0],context)
                if resolved:
                    entities.setdefault(resolved['type'],[]).append(resolved['id'])
                continue
            entities[slot]=[canonical(slot,v) for v in vals]
        q=SemanticQuery(intent,entities,attr,mode)
        context=self._update_context(q,context)
        return q, context

    def _resolve_reference(self, raw, context):
        f=fold(raw)
        if 'chuong sau' in f:
            ch=next((x for x in context.focus_entities if x['type']=='chapter'),None)
            if ch and ch['id'].startswith('CH'):
                return {'type':'chapter','id':f"CH{int(ch['id'][2:])+1:02d}"}
        for preferred in ['assignment_part','learning_outcome','chapter','topic']:
            hit=next((x for x in context.focus_entities if x['type']==preferred),None)
            if hit: return hit
        return context.focus_entities[0] if context.focus_entities else None

    def _update_context(self,q,context):
        focus=[]
        for typ in ['assignment_part','learning_outcome','chapter','topic','assignment']:
            for eid in q.entities.get(typ,[]): focus.append({'type':typ,'id':eid})
        if focus: context=ContextState(focus)
        return context
