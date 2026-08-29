"""Defensive validation of Person 2's SemanticQuery contract."""

from pathlib import Path
from typing import Any

import yaml

from src.contracts import SemanticQuery


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUERY_FRAMES = ROOT / "contracts" / "query_frames.yaml"


class InvalidSemanticQuery(ValueError):
    """A SemanticQuery does not match any supported QueryFrame."""


class ContractDefinitionError(ValueError):
    """The shared QueryFrame contract is ambiguous or malformed."""


class SemanticQueryValidator:
    """Load and validate against the existing query_frames.yaml format.

    The contract currently uses ``required``/``optional`` entity-key lists,
    a fixed ``attribute`` or an ``attributes`` list, and ``answer_mode``.
    Frames that use ``attributes`` without an explicit mode are the VALUE
    frames already defined by the committed contract.
    """

    def __init__(self, contract_path: str | Path = DEFAULT_QUERY_FRAMES):
        self.contract_path = Path(contract_path)
        self.frames = self._load_frames(self.contract_path)
        self._validate_contract_definition()

    @staticmethod
    def _load_frames(path: Path) -> dict[str, dict[str, Any]]:
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ContractDefinitionError(f"Cannot read {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ContractDefinitionError(f"Invalid YAML in {path}: {exc}") from exc

        frames = document.get("frames") if isinstance(document, dict) else None
        if not isinstance(frames, dict) or not frames:
            raise ContractDefinitionError("query_frames.yaml must define frames")
        return frames

    @staticmethod
    def _attributes(spec: dict[str, Any]) -> list[str]:
        if "attribute" in spec:
            return [spec["attribute"]]
        values = spec.get("attributes", [])
        return list(values) if isinstance(values, list) else []

    @staticmethod
    def _answer_mode(spec: dict[str, Any]) -> str | None:
        mode = spec.get("answer_mode")
        if mode is not None:
            return mode
        # Existing contract uses ``attributes`` for VALUE frames.
        if "attributes" in spec:
            return "VALUE"
        return None

    def _validate_contract_definition(self) -> None:
        for name, spec in self.frames.items():
            if not isinstance(spec, dict):
                raise ContractDefinitionError(f"Frame {name} must be a mapping")
            if not spec.get("intent"):
                raise ContractDefinitionError(f"Frame {name} has no intent")
            if not self._attributes(spec):
                raise ContractDefinitionError(f"Frame {name} has no attribute")
            if self._answer_mode(spec) not in {"VALUE", "LIST", "BOOLEAN"}:
                raise ContractDefinitionError(
                    f"Frame {name} has no supported answer_mode"
                )
            for key in ("required", "optional"):
                if not isinstance(spec.get(key, []), list):
                    raise ContractDefinitionError(
                        f"Frame {name}.{key} must be a list"
                    )

    def _matching_frames(self, query: SemanticQuery) -> list[str]:
        if not isinstance(query.entities, dict):
            raise InvalidSemanticQuery("entities must be a mapping")
        for key, values in query.entities.items():
            if not isinstance(key, str) or not isinstance(values, list):
                raise InvalidSemanticQuery("entity values must be lists")
            if any(not isinstance(value, str) for value in values):
                raise InvalidSemanticQuery("entity values must be canonical strings")

        matches: list[str] = []
        for name, spec in self.frames.items():
            if spec.get("intent") != query.intent:
                continue
            if query.attribute not in self._attributes(spec):
                continue
            if query.answer_mode != self._answer_mode(spec):
                continue

            required = set(spec.get("required", []))
            optional = set(spec.get("optional", []))
            entity_keys = set(query.entities)
            if not required.issubset(
                {key for key, values in query.entities.items() if values}
            ):
                continue
            if not entity_keys.issubset(required | optional):
                continue
            matches.append(name)
        return matches

    def validate(self, query: SemanticQuery) -> str:
        if not isinstance(query, SemanticQuery):
            raise InvalidSemanticQuery("expected SemanticQuery")
        if query.intent == "UNKNOWN":
            raise InvalidSemanticQuery("UNKNOWN must be handled before retrieval")

        matches = self._matching_frames(query)
        if not matches:
            raise InvalidSemanticQuery(
                "No QueryFrame matches "
                f"intent={query.intent!r}, attribute={query.attribute!r}, "
                f"answer_mode={query.answer_mode!r}, entities={query.entities!r}"
            )
        if len(matches) > 1:
            raise ContractDefinitionError(
                "SemanticQuery matches multiple QueryFrames: "
                + ", ".join(matches)
            )
        return matches[0]
