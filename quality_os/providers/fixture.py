from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .base import GenerationResult


class FixtureProvider:
    name = "fixture"

    def __init__(self, root: Path):
        self.root = root

    def generate(self, stage: str, context: dict[str, Any], schema: dict[str, Any]) -> GenerationResult:
        started = time.monotonic()
        path = self.root / "fixtures" / "agent_outputs" / f"{stage}.json"
        raw = path.read_text(encoding="utf-8")
        output = json.loads(raw)
        return GenerationResult(
            provider=self.name,
            stage=stage,
            output=output,
            raw=raw,
            duration_ms=round((time.monotonic() - started) * 1000),
            is_ai=False,
            command=[],
            model="deterministic-fixture-not-an-llm",
        )
