"""Resolve grounded assignment-part focus for the integration shell.

This service consumes canonical queries/results only. It leaves semantic
normalization in Person 2 and uses the same derived relations as retrieval.
"""

from src.contracts import ContextState


def assignment_focus(query, retrieval, kb, context):
    if query.intent != 'GET_ASSIGNMENT' or query.attribute != 'contains_component':
        return context
    # A new component question supersedes earlier assignment-part focus.
    focus = [item for item in context.focus_entities if item['type'] != 'assignment_part']
    if retrieval.status != 'FOUND' or retrieval.values != [True] or type(retrieval.values[0]) is not bool:
        return ContextState(focus)
    assignments = query.entities.get('assignment') or ['BTL01']
    topics = query.entities.get('topic', [])
    selected = query.entities.get('assignment_part')
    candidates = [
        part_id for part_id, record in kb.assignment_parts.items()
        if record.get('assignment_id') in assignments
        and (selected is None or part_id in selected)
        and topics
        and all(topic in kb.indexes.assignment_part_to_topics.get(part_id, []) for topic in topics)
    ]
    if len(candidates) == 1:
        focus.insert(0, {'type': 'assignment_part', 'id': candidates[0]})
    return ContextState(focus)
