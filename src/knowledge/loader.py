"""Deterministic loader for the supplied semi-structured KB files.

This module parses data sections, not natural-language user questions.  It
therefore produces canonical records rather than syntactic parse trees.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

import yaml

from .index_builder import build_indexes
from .models import KnowledgeBase as KnowledgeBaseModel


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "raw"
ANNOTATIONS = ROOT / "data" / "annotations"


class KBValidationError(ValueError):
    """Raised when source data cannot form a valid canonical KB."""


def _match_value(line: str, key: str) -> str | None:
    match = re.match(rf"^\s*{re.escape(key)}:\s*(.*?)\s*$", line, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _first_value(lines: list[str], key: str) -> str | None:
    for line in lines:
        value = _match_value(line, key)
        if value is not None:
            return value
    return None


def _is_key(line: str, keys: Iterable[str]) -> bool:
    return any(
        re.match(rf"^\s*{re.escape(key)}(?::\s*$|\s*$)", line, re.IGNORECASE)
        for key in keys
    )


def _block(lines: list[str], key: str, stop_keys: Iterable[str]) -> list[str]:
    """Return lines after ``key:`` until another known section starts."""

    start = next(
        (index for index, line in enumerate(lines) if _is_key(line, [key])),
        None,
    )
    if start is None:
        return []
    stops = list(stop_keys)
    result: list[str] = []
    for line in lines[start + 1 :]:
        if _is_key(line, stops):
            break
        result.append(line.rstrip())
    return result


def _clean_lines(lines: Iterable[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip()]


def _put_if_present(record: dict[str, object], key: str, value: object) -> None:
    """Keep absent source fields absent from canonical records."""

    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    record[key] = value


def _permission_from_text(text: str) -> bool | None:
    """Parse explicit sample-policy permission phrases during ingestion.

    QueryEngine retrieves this structured value and never interprets policy
    prose at query time.  Policies without an explicit permission phrase do
    not receive a synthetic boolean field.
    """

    normalized = text.casefold()
    if re.search(r"\bkhông\s+được\b|\bcấm\b", normalized):
        return False
    if re.search(r"\bđược\s+phép\b|\bnếu\s+được\s+sử\s+dụng\b", normalized):
        return True
    return None


def _as_number(value: str | None, key: str, source: Path) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", value)
    if not match:
        raise KBValidationError(f"{source.name}: field '{key}' is not numeric")
    return int(match.group())


class KnowledgeBaseLoader:
    """Parse all raw files into a supplied canonical KB container."""

    COURSE_SECTIONS = [
        "course_description",
        "main_parts",
        "learning_outcomes",
        "detailed_learning_outcomes",
        "assessment",
        "exam_format",
    ]

    REGULATION_KEYS = [
        "attendance",
        "academic_integrity",
        "AI_usage",
        "source_code",
        "assignment_sharing",
        "external_libraries",
        "LLM_RAG",
        "OUT_OF_SCOPE",
    ]

    def __init__(
        self,
        data_root: str | Path = DATA,
        annotation_root: str | Path | None = None,
    ):
        self.data_root = Path(data_root)
        self.annotation_root = Path(annotation_root) if annotation_root else (
            ANNOTATIONS if self.data_root == DATA else self.data_root.parent / "annotations"
        )

    def load(self) -> KnowledgeBaseModel:
        kb = KnowledgeBaseModel()
        return self.load_into(kb)

    def load_into(self, kb: KnowledgeBaseModel) -> KnowledgeBaseModel:
        for collection_name in (
            "courses",
            "course_parts",
            "weeks",
            "chapters",
            "topics",
            "assignments",
            "assignment_parts",
            "deadlines",
            "resources",
            "resource_topic_annotations",
            "regulations",
            "learning_outcomes",
            "exams",
            "instructors",
        ):
            getattr(kb, collection_name).clear()
        self._parse_course(kb)
        self._parse_schedule(kb)
        self._parse_topics(kb)
        self._parse_assignments(kb)
        self._parse_resources(kb)
        self._parse_regulations(kb)
        self._parse_learning_outcomes(kb)
        validate_kb(kb)
        self._parse_resource_topic_annotations(kb)
        build_indexes(kb)
        return kb

    def _read(self, filename: str) -> tuple[Path, str, list[str]]:
        path = self.data_root / filename
        if not path.exists():
            raise KBValidationError(f"Missing KB source file: {path}")
        text = path.read_text(encoding="utf-8")
        return path, text, text.splitlines()

    def _parse_course(self, kb: KnowledgeBaseModel) -> None:
        source, text, lines = self._read("course_info.txt")
        course_id = _first_value(lines, "course_id")
        if not course_id:
            raise KBValidationError(f"{source.name}: missing course_id")

        numeric_fields = {
            "credits",
            "ects",
            "total_course_hours",
            "lecture_hours",
            "major_assignment_hours",
            "self_study_hours",
        }
        course: dict[str, object] = {
            "id": course_id,
            "course_id": course_id,
        }
        for key in [
            "course_name",
            "course_name_en",
            "semester",
            "credits",
            "ects",
            "course_type",
            "department",
            "format",
            "total_course_hours",
            "lecture_hours",
            "major_assignment_hours",
            "self_study_hours",
        ]:
            value = _first_value(lines, key)
            if key in numeric_fields:
                value = _as_number(value, key, source)
            _put_if_present(course, key, value)

        description = _block(lines, "course_description", ["main_parts"])
        _put_if_present(course, "description", " ".join(_clean_lines(description)))

        parts = _clean_lines(
            _block(lines, "main_parts", ["learning_outcomes", "detailed_learning_outcomes"])
        )
        _put_if_present(course, "parts", parts)
        for number, name in enumerate(parts, start=1):
            part_id = f"COURSE_PART_{number}"
            kb.course_parts[part_id] = {
                "id": part_id,
                "name": name,
                "course_id": course_id,
            }

        assessment: dict[str, str] = {}
        for line in _block(lines, "assessment", ["exam_format"]):
            if ":" in line:
                key, value = line.split(":", 1)
                assessment[key.strip()] = value.strip()
        _put_if_present(course, "assessment", assessment)

        kb.courses[course_id] = course
        self._parse_exams(kb, lines, source, course_id)
        _put_if_present(course, "exam_ids", list(kb.exams))

    @staticmethod
    def _parse_exams(
        kb: KnowledgeBaseModel,
        lines: list[str],
        source: Path,
        course_id: str,
    ) -> None:
        for line in _block(lines, "exam_format", []):
            if ":" not in line:
                continue
            raw_id, description = line.split(":", 1)
            exam_id = raw_id.strip().upper()
            duration_match = re.search(r"(\d+)\s+minutes", description, re.IGNORECASE)
            exam: dict[str, object] = {
                "id": exam_id,
                "format": description.strip(),
                "source": f"course_info:{course_id}",
            }
            _put_if_present(
                exam,
                "duration",
                int(duration_match.group(1)) if duration_match else None,
            )
            kb.exams[exam_id] = exam

    def _parse_schedule(self, kb: KnowledgeBaseModel) -> None:
        source, text, _ = self._read("schedule.txt")
        matches = list(re.finditer(r"(?mi)^WEEK\s+(\d+)\s*$", text))
        if not matches:
            raise KBValidationError(f"{source.name}: no WEEK sections found")

        for index, match in enumerate(matches):
            number = int(match.group(1))
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body_lines = text[match.end() : end].splitlines()
            week_id = f"WEEK_{number:02d}"
            topics = [
                line[2:].strip()
                for line in _block(body_lines, "topics", ["activity", "milestone"])
                if line.strip().startswith("- ")
            ]
            if not topics:
                raise KBValidationError(
                    f"{source.name} {week_id} parsed incompletely: missing required field 'topics'"
                )

            chapter_value = _first_value(body_lines, "chapter")
            chapter_match = re.search(r"(\d+)", chapter_value or "")
            chapter_ids = [f"CH{int(chapter_match.group(1)):02d}"] if chapter_match else []
            week: dict[str, object] = {
                "id": week_id,
                "week_number": number,
                "chapter_ids": chapter_ids,
                "topics": topics,
            }
            _put_if_present(week, "part", _first_value(body_lines, "part"))
            _put_if_present(week, "activity", _first_value(body_lines, "activity"))
            _put_if_present(week, "milestone", _first_value(body_lines, "milestone"))
            kb.weeks[week_id] = week

    def _parse_topics(self, kb: KnowledgeBaseModel) -> None:
        source, text, _ = self._read("topics.txt")
        matches = list(re.finditer(r"(?mi)^CHAPTER\s+(\d+):\s*(.+?)\s*$", text))
        if not matches:
            raise KBValidationError(f"{source.name}: no CHAPTER sections found")

        for index, match in enumerate(matches):
            number = int(match.group(1))
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body_lines = text[match.end() : end].splitlines()
            chapter_id = _first_value(body_lines, "chapter_id") or f"CH{number:02d}"
            expected_id = f"CH{number:02d}"
            if chapter_id != expected_id:
                raise KBValidationError(
                    f"{source.name}: header Chapter {number} has chapter_id {chapter_id!r}, "
                    f"expected {expected_id!r}"
                )
            keywords = [
                value.strip()
                for value in (_first_value(body_lines, "keywords") or "").split(",")
                if value.strip()
            ]
            summary = " ".join(
                _clean_lines(_block(body_lines, "summary", ["subtopics"]))
            )
            subtopics = _clean_lines(_block(body_lines, "subtopics", []))
            if not summary or not subtopics:
                raise KBValidationError(
                    f"{source.name} {chapter_id} parsed incompletely: missing summary or subtopics"
                )
            chapter: dict[str, object] = {
                "id": chapter_id,
                "title": match.group(2).strip(),
                "keywords": keywords,
                "summary": summary,
                "subtopics": subtopics,
            }
            _put_if_present(chapter, "part", _first_value(body_lines, "part"))
            kb.chapters[chapter_id] = chapter

    def _parse_assignments(self, kb: KnowledgeBaseModel) -> None:
        source, text, lines = self._read("assignments.txt")
        assignment_id = _first_value(lines, "assignment_id")
        if not assignment_id:
            raise KBValidationError(f"{source.name}: missing assignment_id")

        parts = list(
            re.finditer(
                r"(?mi)^PART\s+(I|II|III|IV|1|2|3|4)\s+-\s*(.+?)\s*$", text
            )
        )
        if not parts:
            raise KBValidationError(f"{source.name}: no assignment parts found")

        roman_to_number = {"I": 1, "II": 2, "III": 3, "IV": 4}
        part_ids: list[str] = []
        for index, match in enumerate(parts):
            raw_number = match.group(1).upper()
            number = roman_to_number.get(raw_number, int(raw_number) if raw_number.isdigit() else 0)
            part_id = f"BTL_PART_{number}"
            part_ids.append(part_id)
            end = parts[index + 1].start() if index + 1 < len(parts) else text.find("LLM/RAG EXTENSION", match.end())
            if end < 0:
                end = len(text)
            body_lines = text[match.end() : end].splitlines()
            requirements: list[str] = []
            outputs: list[str] = []
            for line in body_lines:
                value = line.strip()
                if value.startswith("- "):
                    value = value[2:].strip()
                if not value:
                    continue
                if re.fullmatch(r"-+", value):
                    continue
                if value.startswith("output/"):
                    outputs.append(value)
                elif line.strip().startswith("-"):
                    requirements.append(value)
            part: dict[str, object] = {
                "id": part_id,
                "title": match.group(2).strip(),
                "assignment_id": assignment_id,
            }
            _put_if_present(part, "requirements", requirements)
            _put_if_present(part, "outputs", outputs)
            kb.assignment_parts[part_id] = part

        goal = " ".join(_clean_lines(_block(lines, "goal", ["PART I - Grammar and Parser"])))
        assignment: dict[str, object] = {
            "id": assignment_id,
            "parts": part_ids,
        }
        for key in ("title", "team_size", "domain"):
            _put_if_present(assignment, key, _first_value(lines, key))
        _put_if_present(assignment, "goal", goal)
        kb.assignments[assignment_id] = assignment

    def _parse_resources(self, kb: KnowledgeBaseModel) -> None:
        source, text, _ = self._read("resources.txt")
        matches = list(re.finditer(r"(?mi)^(TEXTBOOK|REFERENCE)\s+(\d+)\s*$", text))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body_lines = text[match.end() : end].splitlines()
            resource_id = f"RES{index + 1:02d}"
            author = _first_value(body_lines, "author")
            authors = _first_value(body_lines, "authors") or author
            resource: dict[str, object] = {
                "id": resource_id,
                "resource_type": match.group(1).upper(),
                "source": f"resources:{resource_id}",
            }
            for key in ("title", "publisher", "usage"):
                _put_if_present(resource, key, _first_value(body_lines, key))
            _put_if_present(resource, "author", author or authors)
            _put_if_present(resource, "authors", authors)
            _put_if_present(
                resource,
                "year",
                _as_number(_first_value(body_lines, "year"), "year", source),
            )
            kb.resources[resource_id] = resource
        if not kb.resources:
            raise KBValidationError(f"{source.name}: no resources found")

    def _parse_regulations(self, kb: KnowledgeBaseModel) -> None:
        source, text, _ = self._read("regulations.txt")
        matches = list(
            re.finditer(
                rf"(?mi)^({'|'.join(map(re.escape, self.REGULATION_KEYS))}):\s*$",
                text,
            )
        )
        mapping = {
            "attendance": "ATTENDANCE",
            "academic_integrity": "ACADEMIC_INTEGRITY",
            "AI_usage": "AI_USAGE",
            "source_code": "SOURCE_CODE",
            "assignment_sharing": "ASSIGNMENT_SHARING",
            "external_libraries": "EXTERNAL_LIBRARIES",
            "LLM_RAG": "LLM_RAG",
            "OUT_OF_SCOPE": "OUT_OF_SCOPE",
        }
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            value = " ".join(_clean_lines(text[match.end() : end].splitlines()))
            if value:
                raw_key = match.group(1)
                canonical_key = next(
                    (value for key, value in mapping.items() if key.lower() == raw_key.lower()),
                    raw_key.upper(),
                )
                regulation: dict[str, object] = {
                    "id": canonical_key,
                    "text": value,
                    "source": f"regulations:{canonical_key}",
                }
                _put_if_present(
                    regulation,
                    "permission",
                    _permission_from_text(value),
                )
                kb.regulations[canonical_key] = regulation
        if not kb.regulations:
            raise KBValidationError(f"{source.name}: no regulations found")

    def _parse_resource_topic_annotations(self, kb: KnowledgeBaseModel) -> None:
        path = self.annotation_root / "resource_topics.yaml"
        if not path.exists():
            raise KBValidationError(f"Missing KB annotation file: {path}")
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise KBValidationError(f"Cannot read KB annotation file: {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise KBValidationError(f"Invalid YAML in {path}: {exc}") from exc

        annotations = document.get("resource_topics") if isinstance(document, dict) else None
        if not isinstance(annotations, dict):
            raise KBValidationError(
                f"{path.name}: resource_topics must be a mapping"
            )

        for resource_id, annotation in annotations.items():
            if resource_id not in kb.resources:
                raise KBValidationError(
                    f"{path.name}: unknown resource ID {resource_id!r}"
                )
            if not isinstance(annotation, dict):
                raise KBValidationError(
                    f"{path.name}: {resource_id} annotation must be a mapping"
                )
            topics = annotation.get("topics")
            if (
                not isinstance(topics, list)
                or not topics
                or any(
                    not isinstance(topic_id, str)
                    or not re.fullmatch(r"[A-Z][A-Z0-9_]*", topic_id)
                    for topic_id in topics
                )
            ):
                raise KBValidationError(
                    f"{path.name}: {resource_id}.topics must contain canonical IDs"
                )
            if len(set(topics)) != len(topics):
                raise KBValidationError(
                    f"{path.name}: {resource_id}.topics contains duplicates"
                )

            basis = annotation.get("basis")
            if (
                not isinstance(basis, dict)
                or not isinstance(basis.get("field"), str)
                or not isinstance(basis.get("text"), str)
                or not basis["text"].strip()
            ):
                raise KBValidationError(
                    f"{path.name}: {resource_id} requires provenance basis"
                )
            if kb.resources[resource_id].get(basis["field"]) != basis["text"]:
                raise KBValidationError(
                    f"{path.name}: {resource_id} provenance does not match raw resource field"
                )
            if annotation.get("annotation_type") != "TEAM_DERIVED":
                raise KBValidationError(
                    f"{path.name}: {resource_id} must be TEAM_DERIVED"
                )

            kb.resource_topic_annotations[resource_id] = annotation

    def _parse_learning_outcomes(self, kb: KnowledgeBaseModel) -> None:
        source, _, lines = self._read("course_info.txt")
        current_id: str | None = None
        current_lines: list[str] = []

        def flush() -> None:
            if current_id and current_lines:
                kb.learning_outcomes[current_id] = {
                    "id": current_id,
                    "description": " ".join(_clean_lines(current_lines)),
                    "source": f"course_info:{current_id}",
                }

        for line in lines:
            match = re.match(r"^\s*(LO\d+(?:\.\d+)?)\s*-\s*(.+?)\s*$", line)
            if match:
                flush()
                current_id = match.group(1)
                current_lines = [match.group(2)]
            elif current_id and line.startswith((" ", "\t")) and line.strip():
                current_lines.append(line)
        flush()
        if not kb.learning_outcomes:
            raise KBValidationError(f"{source.name}: no learning outcomes found")


class KnowledgeBase(KnowledgeBaseModel):
    """Compatibility entry point: instantiate and load the sample KB."""

    def __init__(
        self,
        data_root: str | Path = DATA,
        annotation_root: str | Path | None = None,
    ):
        super().__init__()
        KnowledgeBaseLoader(data_root, annotation_root).load_into(self)


def validate_kb(kb: KnowledgeBaseModel) -> None:
    """Validate inventory, required fields and canonical references."""

    if kb.default_course_id not in kb.courses:
        raise KBValidationError(
            f"Expected course {kb.default_course_id}, found {list(kb.courses)}"
        )
    if len(kb.courses) != 1:
        raise KBValidationError(
            f"Single-course KB expected exactly 1 course, found {len(kb.courses)}"
        )

    expected_weeks = {f"WEEK_{number:02d}" for number in range(1, 16)}
    if set(kb.weeks) != expected_weeks:
        raise KBValidationError(
            f"Expected weeks WEEK_01..WEEK_15, found {sorted(kb.weeks)}"
        )

    expected_chapters = {f"CH{number:02d}" for number in range(1, 13)}
    if set(kb.chapters) != expected_chapters:
        raise KBValidationError(
            f"Expected chapters CH01..CH12, found {sorted(kb.chapters)}"
        )

    for week_id, week in kb.weeks.items():
        if not week.get("topics"):
            raise KBValidationError(f"{week_id}: topics must not be empty")
        unknown_chapters = set(week.get("chapter_ids", [])) - set(kb.chapters)
        if unknown_chapters:
            raise KBValidationError(
                f"{week_id}: unknown chapter references {sorted(unknown_chapters)}"
            )

    if "BTL01" not in kb.assignments:
        raise KBValidationError("Expected assignment BTL01")
    expected_parts = {f"BTL_PART_{number}" for number in range(1, 5)}
    if set(kb.assignment_parts) != expected_parts:
        raise KBValidationError(
            f"Expected assignment parts {sorted(expected_parts)}, "
            f"found {sorted(kb.assignment_parts)}"
        )

    part_one_outputs = kb.assignment_parts["BTL_PART_1"].get("outputs", [])
    required_outputs = {
        "output/grammar.txt",
        "output/samples.txt",
        "output/parse-results.txt",
    }
    if not required_outputs.issubset(part_one_outputs):
        raise KBValidationError(
            "BTL_PART_1 is missing required outputs: "
            + ", ".join(sorted(required_outputs - set(part_one_outputs)))
        )
