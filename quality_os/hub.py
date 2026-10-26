from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class QualityHub:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation TEXT NOT NULL,
                UNIQUE(source, target, relation)
            );
            """
        )

    def add_node(self, node_id: str, node_type: str, payload: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?)",
            (node_id, node_type, json.dumps(payload, ensure_ascii=False)),
        )
        self.connection.commit()

    def link(self, source: str, target: str, relation: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO edges VALUES (?, ?, ?)",
            (source, target, relation),
        )
        self.connection.commit()

    def load(self, spec: dict[str, Any], cases: dict[str, Any]) -> None:
        for requirement in spec["requirements"]:
            req_id = requirement["id"]
            self.add_node(req_id, "requirement", requirement)
            risk_id = f"RISK-{requirement['risk'].upper()}"
            self.add_node(risk_id, "risk", {"name": requirement["risk"]})
            self.link(req_id, risk_id, "has_risk")
            oracle_id = f"ORACLE-{req_id}"
            self.add_node(oracle_id, "oracle", {"source": requirement["oracle_source"], "acceptance": requirement["acceptance"]})
            self.link(req_id, oracle_id, "verified_by")
        for case in cases["cases"]:
            self.add_node(case["id"], "case", case)
            self.add_node(case["test_nodeid"], "test", {"path": case["test_nodeid"]})
            self.link(case["id"], case["test_nodeid"], "implemented_by")
            for req_id in case["requirement_ids"]:
                self.link(req_id, case["id"], "covered_by")

    def record_run(self, run_id: str, payload: dict[str, Any], test_nodeids: list[str]) -> None:
        self.add_node(run_id, "run", payload)
        for nodeid in test_nodeids:
            self.link(nodeid, run_id, "executed_in")

    def trace_requirement(self, requirement_id: str) -> dict[str, Any]:
        node = self.connection.execute("SELECT payload FROM nodes WHERE id = ?", (requirement_id,)).fetchone()
        if not node:
            raise KeyError(requirement_id)
        cases = self.connection.execute(
            "SELECT target FROM edges WHERE source = ? AND relation = 'covered_by'", (requirement_id,)
        ).fetchall()
        result = {"requirement": json.loads(node["payload"]), "cases": []}
        for case_row in cases:
            case_id = case_row["target"]
            case = self.connection.execute("SELECT payload FROM nodes WHERE id = ?", (case_id,)).fetchone()
            tests = self.connection.execute(
                "SELECT target FROM edges WHERE source = ? AND relation = 'implemented_by'", (case_id,)
            ).fetchall()
            result["cases"].append({"case": json.loads(case["payload"]), "tests": [row["target"] for row in tests]})
        return result

    def close(self) -> None:
        self.connection.close()
