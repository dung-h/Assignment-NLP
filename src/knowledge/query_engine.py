"""Contract-driven retrieval over the canonical in-memory knowledge base."""

from __future__ import annotations

from src.contracts import RetrievalResult
from src.semantics.semantic_query_validator import SemanticQueryValidator


class QueryHandlerNotImplemented(RuntimeError):
    """A valid QueryFrame has no corresponding intent handler."""


class QueryEngine:
    def __init__(self, kb, validator=None):
        self.kb = kb
        self.validator = validator or SemanticQueryValidator()

    def execute(self, q):
        self.validator.validate(q)
        handler = getattr(self, f"_handle_{q.intent.lower()}", None)
        if not callable(handler):
            raise QueryHandlerNotImplemented(
                f"No handler for valid intent {q.intent!r}"
            )
        return handler(q)

    @staticmethod
    def _not_found() -> RetrievalResult:
        return RetrievalResult("NOT_FOUND", [], [])

    @staticmethod
    def _unique(values):
        return list(dict.fromkeys(values))

    def _found(self, values, sources) -> RetrievalResult:
        values = values if isinstance(values, list) else [values]
        values = [value for value in values if value is not None]
        if not values:
            return self._not_found()
        return RetrievalResult("FOUND", values, sources)

    def _handle_get_course_info(self, q):
        if "exam" in q.entities:
            values = []
            sources = []
            for exam_id in q.entities["exam"]:
                exam = self.kb.exams.get(exam_id)
                if not exam or q.attribute not in exam:
                    continue
                value = exam[q.attribute]
                if value is None:
                    continue
                values.append(value)
                sources.append(exam.get("source", "course_info:CO3085"))
            return self._found(values, sources)

        course = self.kb.course
        value = course.get(q.attribute)
        return self._found(
            value,
            [f"course_info:{course['course_id']}"] if value is not None else [],
        )

    def _handle_get_schedule(self, q):
        if "week" in q.entities:
            values = []
            sources = []
            for week_id in q.entities["week"]:
                week = self.kb.weeks.get(week_id)
                if not week or q.attribute not in week:
                    continue
                value = week[q.attribute]
                if isinstance(value, list):
                    values.extend(value)
                elif value is not None:
                    values.append(value)
                if value is not None:
                    sources.append(f"schedule:{week_id}")
            return self._found(values, sources)

        if q.attribute == "week" and "chapter" in q.entities:
            values = []
            for chapter_id in q.entities["chapter"]:
                values.extend(
                    self.kb.indexes.chapter_to_weeks.get(chapter_id, [])
                )
            values = self._unique(values)
            return self._found(values, [f"schedule:{value}" for value in values])

        if q.attribute == "week" and "topic" in q.entities:
            values = []
            for topic_id in q.entities["topic"]:
                values.extend(self.kb.indexes.topic_to_weeks.get(topic_id, []))
            values = self._unique(values)
            return self._found(values, [f"schedule:{value}" for value in values])

        # ASK_MILESTONE_WEEK has no required entity.  Returning only weeks
        # whose source record explicitly contains a milestone is safe.  A
        # future assignment/deadline filter needs an explicit relation in KB.
        if q.attribute == "week":
            optional_filters = set(q.entities) & {"assignment", "assignment_part", "deadline"}
            if optional_filters:
                return self._not_found()
            values = [
                week_id
                for week_id, week in self.kb.weeks.items()
                if week.get("milestone") is not None
            ]
            return self._found(values, [f"schedule:{value}" for value in values])

        return self._not_found()

    def _handle_get_topic(self, q):
        if q.attribute == "chapter" and "topic" in q.entities:
            values = []
            for topic_id in q.entities["topic"]:
                values.extend(
                    self.kb.indexes.topic_to_chapters.get(topic_id, [])
                )
            values = self._unique(values)
            return self._found(values, [f"topics:{value}" for value in values])

        if q.attribute == "chapter" and "course_part" in q.entities:
            values = []
            for part_id in q.entities["course_part"]:
                values.extend(
                    self.kb.indexes.course_part_to_chapters.get(part_id, [])
                )
            values = self._unique(values)
            return self._found(values, [f"topics:{value}" for value in values])

        if "chapter" in q.entities:
            values = []
            sources = []
            for chapter_id in q.entities["chapter"]:
                chapter = self.kb.chapters.get(chapter_id)
                if not chapter:
                    continue
                if q.attribute in {"summary", "title", "part"}:
                    value = chapter.get(q.attribute)
                    if value is not None:
                        values.append(value)
                elif q.attribute == "topics":
                    values.extend(chapter.get("subtopics", []))
                elif q.attribute == "contains_topic" and "topic" in q.entities:
                    value = all(
                        topic_id in self.kb.indexes.chapter_to_topics.get(chapter_id, [])
                        for topic_id in q.entities["topic"]
                    )
                    values.append(value)
                if q.attribute in {"summary", "title", "part", "topics", "contains_topic"}:
                    sources.append(f"topics:{chapter_id}")
            return self._found(values, sources)

        return self._not_found()

    def _handle_get_assignment(self, q):
        assignment_ids = q.entities.get("assignment") or ["BTL01"]
        assignment_parts = q.entities.get("assignment_part", [])

        if q.attribute in {"goal", "team_size", "parts"}:
            values = []
            sources = []
            for assignment_id in assignment_ids:
                assignment = self.kb.assignments.get(assignment_id)
                if not assignment or q.attribute not in assignment:
                    continue
                values.append(assignment[q.attribute])
                sources.append(f"assignments:{assignment_id}")
            return self._found(values, sources)

        if q.attribute in {"title", "requirements", "outputs"}:
            part_ids = assignment_parts
            if not part_ids:
                part_ids = []
                for assignment_id in assignment_ids:
                    part_ids.extend(
                        self.kb.assignments.get(assignment_id, {}).get("parts", [])
                    )

            values = []
            sources = []
            for part_id in part_ids:
                part = self.kb.assignment_parts.get(part_id)
                if not part or q.attribute not in part:
                    continue
                value = part[q.attribute]
                if isinstance(value, list):
                    values.extend(value)
                else:
                    values.append(value)
                sources.append(f"assignments:{part_id}")
            return self._found(values, sources)

        if q.attribute == "contains_component" and "topic" in q.entities:
            return self._assignment_contains_component(q, assignment_ids, assignment_parts)

        return self._not_found()

    def _assignment_contains_component(self, q, assignment_ids, assignment_parts):
        # A nonexistent target is missing data, not a grounded negative.
        if any(identifier not in self.kb.assignments for identifier in assignment_ids):
            return self._not_found()

        selected_parts = self._unique(assignment_parts or [
            part_id
            for assignment_id in assignment_ids
            for part_id in self.kb.assignments[assignment_id].get("parts", [])
        ])
        if not selected_parts:
            return self._not_found()

        components: set[str] = set()
        for part_id in selected_parts:
            part = self.kb.assignment_parts.get(part_id)
            if not part or part_id not in self.kb.indexes.assignment_part_to_topics:
                return self._not_found()
            parent_id = part.get("assignment_id")
            if (
                parent_id not in assignment_ids
                or part_id not in self.kb.assignments[parent_id].get("parts", [])
            ):
                return self._not_found()
            components.update(self.kb.indexes.assignment_part_to_topics[part_id])

        value = all(topic_id in components for topic_id in q.entities["topic"])
        source_ids = selected_parts if assignment_parts else self._unique(assignment_ids)
        return self._found(value, [f"assignments:{identifier}" for identifier in source_ids])

    def _handle_get_deadline(self, q):
        identifiers = []
        for key in ("deadline", "assignment", "assignment_part"):
            identifiers.extend(q.entities.get(key, []))

        values = []
        sources = []
        for identifier in identifiers:
            deadline = self.kb.deadlines.get(identifier)
            if not deadline or q.attribute not in deadline:
                continue
            value = deadline[q.attribute]
            if value is not None:
                values.append(value)
                sources.append(deadline.get("source", f"deadlines:{identifier}"))
        return self._found(values, sources)

    def _handle_get_rule(self, q):
        values = []
        sources = []
        for regulation_id in q.entities.get("regulation", []):
            regulation = self.kb.regulations.get(regulation_id)
            if not regulation:
                continue
            field = "text" if q.attribute == "policy_text" else q.attribute
            value = regulation.get(field)
            if value is None:
                continue
            values.append(value)
            sources.append(
                regulation.get("source", f"regulations:{regulation_id}")
            )
        return self._found(values, sources)

    def _handle_get_resource(self, q):
        topics = q.entities.get("topic", [])
        if topics:
            resource_ids = []
            for topic_id in topics:
                resource_ids.extend(
                    self.kb.indexes.topic_to_resources.get(topic_id, [])
                )
            resource_ids = self._unique(resource_ids)
            return self._resource_titles(resource_ids)

        # There is no chapter-resource relation in the current source data.
        # Returning every resource would fabricate a relation.
        if "chapter" in q.entities:
            return self._not_found()

        if "resource" in q.entities:
            return self._resource_attributes(q)

        return self._not_found()

    def _resource_titles(self, resource_ids):
        values = []
        sources = []
        for resource_id in resource_ids:
            resource = self.kb.resources.get(resource_id)
            if not resource or resource.get("title") is None:
                continue
            values.append(resource["title"])
            sources.append(resource.get("source", f"resources:{resource_id}"))
        return self._found(values, sources)

    def _resource_attributes(self, q):
        values = []
        sources = []
        for resource_id in q.entities["resource"]:
            resource = self.kb.resources.get(resource_id)
            if not resource or q.attribute not in resource:
                continue
            value = resource[q.attribute]
            if value is None:
                continue
            values.append(value)
            sources.append(resource.get("source", f"resources:{resource_id}"))
        return self._found(values, sources)

    def _handle_get_instructor(self, q):
        instructor_ids = q.entities.get("instructor", [])
        records = (
            ((instructor_id, self.kb.instructors.get(instructor_id)) for instructor_id in instructor_ids)
            if instructor_ids
            else self.kb.instructors.items()
        )
        values = []
        sources = []
        for instructor_id, instructor in records:
            if not instructor or q.attribute not in instructor:
                continue
            value = instructor[q.attribute]
            if value is None:
                continue
            values.append(value)
            sources.append(instructor.get("source", f"instructors:{instructor_id}"))
        return self._found(values, sources)

    def _handle_get_lo(self, q):
        values = []
        sources = []
        for outcome_id in q.entities.get("learning_outcome", []):
            outcome = self.kb.learning_outcomes.get(outcome_id)
            if not outcome:
                continue
            value = outcome.get(q.attribute)
            if value is None:
                continue
            values.extend(value if isinstance(value, list) else [value])
            sources.append(outcome.get("source", f"course_info:{outcome_id}"))
        return self._found(values, sources)
