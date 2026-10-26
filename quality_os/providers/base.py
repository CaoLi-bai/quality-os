from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass
class GenerationResult:
    provider: str
    stage: str
    output: dict[str, Any]
    raw: str
    duration_ms: int
    is_ai: bool
    command: list[str]
    model: str | None = None

    def evidence(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("output")
        value.pop("raw")
        return value


class Provider(Protocol):
    name: str

    def generate(self, stage: str, context: dict[str, Any], schema: dict[str, Any]) -> GenerationResult:
        ...
