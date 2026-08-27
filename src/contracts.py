from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class ParserResult:
    valid: bool
    sentence_type: str | None
    query_frame: str | None
    slots: dict[str, list[str]] = field(default_factory=dict)
    tree: str | None = None
    def to_dict(self): return asdict(self)

@dataclass
class SemanticQuery:
    intent: str
    entities: dict[str, list[str]] = field(default_factory=dict)
    attribute: str | None = None
    answer_mode: str = 'VALUE'
    def to_dict(self): return asdict(self)

@dataclass
class ContextState:
    focus_entities: list[dict[str,str]] = field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass
class RetrievalResult:
    status: str
    values: list[Any] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)
