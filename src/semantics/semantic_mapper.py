import re
from copy import deepcopy

from src.contracts import SemanticQuery, ContextState
from .normalizer import canonical, fold
from .semantic_query_validator import InvalidSemanticQuery, SemanticQueryValidator


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

    if frame == 'ASK_EXAM_ATTRIBUTE':
        if 'phut' in c or 'thoi luong' in c or 'duration' in c: return 'duration'
        if 'hinh thuc' in c or 'format' in c: return 'format'
        if 'phan tram' in c or 'chiem' in c or 'trong so' in c or 'weight' in c: return 'weight'

    if frame == 'ASK_INSTRUCTOR_ATTRIBUTE':
        if 'email' in c: return 'email'
        if 'van phong' in c or 'phong' in c or 'office' in c: return 'office'
        if 'ten' in c or 'name' in c: return 'name'

    if frame == 'ASK_RESOURCE_ATTRIBUTE':
        if 'tac gia' in c or 'author' in c: return 'authors'   # ← authors, không author
        if 'nam' in c or 'year' in c: return 'year'
        if 'nha xuat ban' in c or 'publisher' in c: return 'publisher'
        if 'su dung' in c or 'usage' in c: return 'usage'

    return None


class SemanticMapper:
    def __init__(self, validator=None):
        self.validator = validator or SemanticQueryValidator()

    @staticmethod
    def _unknown(context):
        return SemanticQuery('UNKNOWN', {}, None, 'VALUE'), context

    def map(self, parsed, context=None, previous_query=None):
        context = context if context is not None else ContextState()
        if not parsed.valid:
            return self._unknown(context)

        if parsed.query_frame is None:
            return self._inherit_ellipsis(parsed, context, previous_query)

        # Intent, attribute and mode have one source of truth: the shared YAML.
        spec = self.validator.frames.get(parsed.query_frame)
        if spec is None:
            return self._unknown(context)
        attr = spec.get('attribute')
        if 'attributes' in spec:
            cue = (parsed.slots.get('attribute_cue') or [''])[0]
            attr = attribute_from_cue(parsed.query_frame, cue)

        entities = {}
        for slot, vals in parsed.slots.items():
            if slot in {'attribute_cue', 'reference'}:
                continue
            if not isinstance(vals, list) or any(not isinstance(v, str) for v in vals):
                return self._unknown(context)
            entities[slot] = [canonical(slot, v) for v in vals]

        allowed_types = set(spec.get('required', [])) | set(spec.get('optional', []))
        references = parsed.slots.get('reference', [])
        if 'reference' in parsed.slots and not references:
            return self._unknown(context)
        for raw in references:
            resolved = self._resolve_reference(raw, context, allowed_types)
            if resolved is None:
                # An unresolved reference must not become an unfiltered KB query.
                return self._unknown(context)
            values = entities.setdefault(resolved['type'], [])
            if resolved['id'] not in values:
                values.append(resolved['id'])

        q = SemanticQuery(spec['intent'], entities, attr, spec.get('answer_mode', 'VALUE'))
        try:
            if self.validator.validate(q) != parsed.query_frame:
                return self._unknown(context)
        except InvalidSemanticQuery:
            return self._unknown(context)

        context = self._update_context(q, context)
        return q, context

    def _inherit_ellipsis(self, parsed, context, previous):
        # A syntactic ellipsis contains a reference but no invented predicate.
        references = parsed.slots.get('reference', [])
        if previous is None or previous.intent == 'UNKNOWN' or len(references) != 1:
            return self._unknown(context)
        if 'chapter' not in previous.entities:
            return self._unknown(context)
        resolved = self._resolve_reference(references[0], context, {'chapter'})
        if resolved is None:
            return self._unknown(context)
        query = deepcopy(previous)
        query.entities['chapter'] = [resolved['id']]
        try:
            self.validator.validate(query)
        except InvalidSemanticQuery:
            return self._unknown(context)
        return query, self._update_context(query, context)

    def _resolve_reference(self, raw, context, allowed_types=None):
        f = fold(raw)
        relative_cues = [
            ('chapter', +1, ['chuong sau', 'chuong tiep', 'chuong ke tiep']),
            ('chapter', -1, ['chuong truoc']),
            ('week', +1, ['tuan sau', 'tuan tiep']),
            ('week', -1, ['tuan truoc']),
            ('assignment_part', +1, ['phan sau', 'phan tiep']),
            ('assignment_part', -1, ['phan truoc']),
        ]
        for entity_type, delta, cues in relative_cues:
            if any(cue in f for cue in cues):
                if allowed_types is not None and entity_type not in allowed_types:
                    return None
                return self._shift_entity(context, entity_type, delta)

        # A named type can refer back to its last focus after a topic switch.
        for entity_type, cue in [('chapter', 'chuong'), ('week', 'tuan'), ('assignment_part', 'phan')]:
            if re.search(rf'\b{cue}\b', f):
                if allowed_types is not None and entity_type not in allowed_types:
                    return None
                return self._focus_of_type(context, entity_type)

        # An untyped pronoun refers to the current focus, not an older entity
        # selected only because its type happens to fit the new QueryFrame.
        if not context.focus_entities:
            return None
        entity_type = context.focus_entities[0]['type']
        if allowed_types is not None and entity_type not in allowed_types:
            return None
        return self._focus_of_type(context, entity_type)

    @staticmethod
    def _focus_of_type(context, entity_type):
        hits = {entity['id']: entity for entity in context.focus_entities if entity['type'] == entity_type}
        # "This chapter" is ambiguous after a query about multiple chapters.
        return next(iter(hits.values())) if len(hits) == 1 else None

    def _shift_entity(self, context, entity_type, delta):
        """Dịch entity theo delta (ví dụ chapter +1)."""
        current = self._focus_of_type(context, entity_type)
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
        """Put current focus first; retain other types for named references."""
        new_focus = []
        for typ in CONTEXT_TYPES:
            for eid in dict.fromkeys(q.entities.get(typ, [])):
                new_focus.append({'type': typ, 'id': eid})

        if not new_focus:
            # Query không có entity → giữ context cũ
            return context

        # History stays behind new focus; a newer entity replaces its own type.
        merged = list(new_focus)
        new_types = {e['type'] for e in new_focus}
        for old in context.focus_entities:
            if old['type'] not in new_types:
                merged.append(old)

        return ContextState(merged)
