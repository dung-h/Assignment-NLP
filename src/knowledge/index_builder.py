"""Build deterministic reverse indexes from canonical KB records."""

from collections.abc import Iterable
import re

from src.semantics.normalizer import TOPIC_ALIASES, fold

from .models import KnowledgeBase


def _append_unique(mapping: dict[str, list[str]], key: str, value: str) -> None:
    values = mapping.setdefault(key, [])
    if value not in values:
        values.append(value)


def _topic_ids(terms: Iterable[str]) -> list[str]:
    """Resolve controlled aliases as phrases, preferring the longest alias.

    Source fields contain phrases such as ``parsing with features`` and
    ``probabilistic context-free grammar``.  Matching a controlled alias at
    word boundaries is still deterministic ingestion logic; choosing the
    longest match prevents PCFG from also being classified as CFG.
    """

    aliases = {fold(alias): topic_id for alias, topic_id in TOPIC_ALIASES.items()}
    ordered_aliases = sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True)
    result: list[str] = []
    for term in terms:
        normalized = fold(str(term))
        for alias, topic_id in ordered_aliases:
            if not re.search(
                rf"(?:^|\s){re.escape(alias)}(?:$|\s)",
                normalized,
            ):
                continue
            if topic_id not in result:
                result.append(topic_id)
            break
    return result


def _exact_topic_ids(terms: Iterable[str]) -> list[str]:
    """Resolve only fields explicitly tagged with a canonical keyword."""

    aliases = {fold(alias): topic_id for alias, topic_id in TOPIC_ALIASES.items()}
    result: list[str] = []
    for term in terms:
        topic_id = aliases.get(fold(str(term)))
        if topic_id and topic_id not in result:
            result.append(topic_id)
    return result


def _part_label(value: object) -> str:
    normalized = fold(str(value or ""))
    return re.sub(r"^part\s+(?:i{1,3}|iv|[1-4])\s*-\s*", "", normalized)


def build_indexes(kb: KnowledgeBase) -> KnowledgeBase:
    """Populate reverse relations from the canonical collections.

    The raw chapter/week/assignment records remain the primary data.  This
    function may be called again after a reload and always rebuilds indexes
    from scratch.
    """

    indexes = kb.indexes
    indexes.chapter_to_topics.clear()
    indexes.topic_to_chapters.clear()
    indexes.chapter_to_weeks.clear()
    indexes.topic_to_weeks.clear()
    indexes.course_part_to_chapters.clear()
    indexes.topic_to_resources.clear()
    kb.topics.clear()

    for chapter_id, chapter in kb.chapters.items():
        terms = [*chapter.get("keywords", []), *chapter.get("subtopics", [])]
        for topic_id in _topic_ids(terms):
            _append_unique(indexes.chapter_to_topics, chapter_id, topic_id)
            kb.topics.setdefault(topic_id, {"id": topic_id, "aliases": []})
        for topic_id in _exact_topic_ids(chapter.get("keywords", [])):
            _append_unique(indexes.topic_to_chapters, topic_id, chapter_id)

    # Preserve the v0 rule used by the frozen mocks: an exact chapter keyword
    # is the primary coverage for a topic.  Subtopic/content matches are used
    # only when that topic has no exact keyword anywhere in the KB.
    keyword_topics = set(indexes.topic_to_chapters)
    for chapter_id, topic_ids in indexes.chapter_to_topics.items():
        for topic_id in topic_ids:
            if topic_id not in keyword_topics:
                _append_unique(indexes.topic_to_chapters, topic_id, chapter_id)

    for week_id, week in kb.weeks.items():
        for chapter_id in week.get("chapter_ids", []):
            _append_unique(indexes.chapter_to_weeks, chapter_id, week_id)
        for topic_id in _topic_ids(week.get("topics", [])):
            _append_unique(indexes.topic_to_weeks, topic_id, week_id)
            kb.topics.setdefault(topic_id, {"id": topic_id, "aliases": []})

    part_labels = {
        part_id: _part_label(part.get("name"))
        for part_id, part in kb.course_parts.items()
    }
    for chapter_id, chapter in kb.chapters.items():
        chapter_part = fold(str(chapter.get("part") or ""))
        if not chapter_part:
            continue
        for part_id, part_label in part_labels.items():
            if part_label and chapter_part == part_label:
                _append_unique(indexes.course_part_to_chapters, part_id, chapter_id)

    for resource_id, annotation in kb.resource_topic_annotations.items():
        for topic_id in annotation.get("topics", []):
            _append_unique(indexes.topic_to_resources, topic_id, resource_id)
            kb.topics.setdefault(topic_id, {"id": topic_id, "aliases": []})

    return kb
