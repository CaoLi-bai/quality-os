from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"send\s+.*(?:external|remote)", re.I),
    re.compile(r"mark\s+every\s+requirement\s+approved", re.I),
    re.compile(r"忽略.{0,12}(指令|要求)"),
]


def scan_untrusted(text: str) -> list[str]:
    return [pattern.pattern for pattern in INJECTION_PATTERNS if pattern.search(text)]


def compile_context(root: Path, inputs: list[str], trusted: bool) -> dict[str, Any]:
    sources = []
    findings = []
    model_documents = []
    for name in inputs:
        path = root / name
        content = path.read_text(encoding="utf-8")
        source = {
            "path": name,
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "trusted": trusted,
        }
        sources.append(source)
        matches = [] if trusted else scan_untrusted(content)
        if matches:
            findings.append({"path": name, "patterns": matches, "action": "excluded_from_model_context"})
        else:
            model_documents.append({"path": name, "content": content})
    return {
        "sources": sources,
        "security_findings": findings,
        "documents": model_documents,
    }
