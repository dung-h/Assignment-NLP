from src.contracts import SemanticQuery, ContextState
from .normalizer import canonical, fold
import re
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
CONTEXT_TYPES = [
    'assignment_part', 'learning_outcome', 'chapter', 'topic',
    'week', 'assignment', 'exam', 'regulation', 'resource',
]
def attribute_from_cue(frame, cue):
    c = fold(cue or '')
    if not c:
        return None

    if frame == 'ASK_COURSE_ATTRIBUTE':
        # Check cue dài/cụ thể TRƯỚC, cue ngắn/chung SAU
        if 'ten tieng anh' in c or 'english name' in c: return 'name_en'
        if 'tin chi' in c or 'credits' in c: return 'credits'
        if 'ects' in c: return 'ects'
        if 'khoa' in c or 'department' in c: return 'department'
        if 'gio tu hoc' in c or 'self study' in c: return 'self_study_hours'
        if 'tong gio' in c or 'total hours' in c: return 'total_course_hours'
        if 'gio ly thuyet' in c or 'lecture hours' in c: return 'lecture_hours'
        if 'gio bai tap' in c or 'assignment hours' in c: return 'major_assignment_hours'
        if 'hoc ky' in c or 'semester' in c: return 'semester'
        if 'loai mon' in c or 'course type' in c: return 'course_type'
        if 'hinh thuc' in c or 'format' in c: return 'format'
        if 'mo ta' in c or 'description' in c: return 'description'
        if 'danh gia' in c or 'assessment' in c: return 'assessment'
        if 'phan' in c or 'parts' in c: return 'parts'
        if 'ten' in c or 'goi la' in c or 'name' in c: return 'name'

    if frame == 'ASK_EXAM_ATTRIBUTE':
        if 'phut' in c or 'thoi luong' in c or 'duration' in c: return 'duration'
        if 'hinh thuc' in c or 'format' in c: return 'format'
        if 'phan tram' in c or 'chiem' in c or 'trong so' in c or 'weight' in c: return 'weight'

    if frame == 'ASK_INSTRUCTOR_ATTRIBUTE':
        if 'email' in c: return 'email'
        if 'van phong' in c or 'phong' in c or 'office' in c: return 'office'
        if 'ten' in c or 'name' in c: return 'name'
        return 'name'  # fallback

    if frame == 'ASK_RESOURCE_ATTRIBUTE':
        if 'tac gia' in c or 'author' in c: return 'authors'   # ← authors, không author
        if 'nam' in c or 'year' in c: return 'year'
        if 'nha xuat ban' in c or 'publisher' in c: return 'publisher'
        if 'su dung' in c or 'usage' in c: return 'usage'
        if 'tai lieu' in c or 'resource' in c: return 'resource'
        return 'title'  # fallback

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
        f = fold(raw)

        # 1. "chương sau" / "chương tiếp theo"
        if any(k in f for k in ['chuong sau', 'chuong tiep', 'chuong ke tiep']):
            return self._shift_entity(context, 'chapter', +1)
        # "chương trước"
        if any(k in f for k in ['chuong truoc', 'chuong truoc do']):
            return self._shift_entity(context, 'chapter', -1)
        # "tuần sau"
        if any(k in f for k in ['tuan sau', 'tuan tiep']):
            return self._shift_entity(context, 'week', +1)
        # "tuần trước"
        if any(k in f for k in ['tuan truoc']):
            return self._shift_entity(context, 'week', -1)
        # "phần sau" / "phần trước"
        if any(k in f for k in ['phan sau', 'phan tiep']):
            return self._shift_entity(context, 'assignment_part', +1)
        if any(k in f for k in ['phan truoc']):
            return self._shift_entity(context, 'assignment_part', -1)

        # 2. Tham chiếu chung ("nó", "phần này", "cái đó")
        for preferred in ['assignment_part', 'learning_outcome', 'chapter', 'topic', 'week', 'assignment']:
            hit = next((x for x in context.focus_entities if x['type'] == preferred), None)
            if hit:
                return hit
        return context.focus_entities[0] if context.focus_entities else None


    def _shift_entity(self, context, entity_type, delta):
        """Dịch entity theo delta (ví dụ chapter +1)."""
        current = next((x for x in context.focus_entities if x['type'] == entity_type), None)
        if not current:
            return None
        entity_id = current['id']
        # Parse số từ ID
        m = re.search(r'(\d+)$', entity_id)
        if not m:
            return None
        number = int(m.group(1)) + delta
        if number < 1:
            return None
        # Format lại ID
        prefix = entity_id[:m.start()]
        if entity_type == 'chapter':
            new_id = f'CH{number:02d}'
        elif entity_type == 'week':
            new_id = f'WEEK_{number:02d}'
        elif entity_type == 'assignment_part':
            new_id = f'BTL_PART_{number}'
        else:
            new_id = f'{prefix}{number}'
        return {'type': entity_type, 'id': new_id}

    

    def _update_context(self, q, context):
        """Cập nhật context với focus mới, giữ entity cũ cùng type."""
        new_focus = []
        for typ in CONTEXT_TYPES:
            for eid in q.entities.get(typ, []):
                new_focus.append({'type': typ, 'id': eid})

        if not new_focus:
            # Query không có entity → giữ context cũ
            return context

        # Merge: giữ entity cũ cùng type với entity mới
        merged = list(new_focus)
        new_types = {e['type'] for e in new_focus}
        for old in context.focus_entities:
            if old['type'] not in new_types:
                merged.append(old)

        return ContextState(merged)


