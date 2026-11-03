"""Internal models for the single-course knowledge base.

The project keeps the supplied text files as the source of truth.  These
models are runtime containers populated by ``loader.py``; they are not a
second hand-maintained database.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KBIndexes:
    """Programmatically derived relations used by retrieval handlers."""

    chapter_to_topics: dict[str, list[str]] = field(default_factory=dict)
    topic_to_chapters: dict[str, list[str]] = field(default_factory=dict)
    chapter_to_weeks: dict[str, list[str]] = field(default_factory=dict)
    topic_to_weeks: dict[str, list[str]] = field(default_factory=dict)
    course_part_to_chapters: dict[str, list[str]] = field(default_factory=dict)
    topic_to_resources: dict[str, list[str]] = field(default_factory=dict)
    assignment_part_to_topics: dict[str, list[str]] = field(default_factory=dict)
    topic_to_assignment_parts: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class KnowledgeBase:
    """Canonical, in-memory representation for the CO3085 sample KB.

    Records intentionally remain dictionary-shaped in v0 so existing query
    handlers can inspect them easily.  Collections are keyed by canonical
    IDs, while ``indexes`` contains only derived reverse relations.
    """

    courses: dict[str, dict[str, Any]] = field(default_factory=dict)
    course_parts: dict[str, dict[str, Any]] = field(default_factory=dict)
    weeks: dict[str, dict[str, Any]] = field(default_factory=dict)
    chapters: dict[str, dict[str, Any]] = field(default_factory=dict)
    topics: dict[str, dict[str, Any]] = field(default_factory=dict)
    assignments: dict[str, dict[str, Any]] = field(default_factory=dict)
    assignment_parts: dict[str, dict[str, Any]] = field(default_factory=dict)
    deadlines: dict[str, dict[str, Any]] = field(default_factory=dict)
    resources: dict[str, dict[str, Any]] = field(default_factory=dict)
    resource_topic_annotations: dict[str, dict[str, Any]] = field(default_factory=dict)
    regulations: dict[str, dict[str, Any]] = field(default_factory=dict)
    learning_outcomes: dict[str, dict[str, Any]] = field(default_factory=dict)
    exams: dict[str, dict[str, Any]] = field(default_factory=dict)
    instructors: dict[str, dict[str, Any]] = field(default_factory=dict)
    indexes: KBIndexes = field(default_factory=KBIndexes)
    default_course_id: str = "CO3085"

    @property
    def course(self) -> dict[str, Any]:
        """Compatibility view for the v0 single-course API."""

        return self.courses.get(self.default_course_id, {})

    @property
    def los(self) -> dict[str, dict[str, Any]]:
        """Compatibility alias for existing handlers/tests."""

        return self.learning_outcomes
