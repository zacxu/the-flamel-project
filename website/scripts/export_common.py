"""Shared read-only frozen-source access for the W1 website export.

This module deliberately contains no model/experiment dispatch capabilities.
Only sources named in the planning inventory or explicitly requested and bound
to the frozen Phase 6 manifest can be accessed.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

WEBSITE = Path(__file__).resolve().parents[1]
ROOT = WEBSITE.parent
STUDY_ID = "flamel-frozen-study-20261022"
SCHEMA_VERSION = 1


def sha_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def strict_float(value: Any, *, nullable: bool = True) -> float | None:
    import math
    if value is None or (isinstance(value, str) and value.strip().lower() in {"", "none", "null", "nan", "n/a", "unavailable"}):
        if nullable:
            return None
        raise ValueError("Required numeric value is absent")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite numeric value cannot enter public data")
    return result


def strict_bool(value: Any, *, nullable: bool = False) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, str) and value.strip().lower() in {"", "none", "null", "n/a"}):
        if nullable:
            return None
        raise ValueError("Required boolean is absent")
    if str(value).strip().lower() in {"true", "1"}:
        return True
    if str(value).strip().lower() in {"false", "0"}:
        return False
    raise ValueError(f"Unknown boolean value: {value!r}")


class ExportContext:
    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.payloads: dict[str, dict] = {}
        self.assets: dict[str, bytes] = {}
        self.inputs: dict[str, dict] = {}
        self.inventory_path = WEBSITE / "research_sources.json"
        self.inventory = json.loads(self.inventory_path.read_text(encoding="utf-8"))
        self.inventory_sha256 = sha_file(self.inventory_path)
        self.baseline = dict(self.inventory["baseline_integrity"])
        for name, expected in self.baseline.items():
            self.check(sha_file(self._path(name)) == expected, "Frozen baseline before export: " + name)
        manifest_path = "artifacts/phase6/manifest.json"
        manifest = json.loads(self._path(manifest_path).read_text(encoding="utf-8"))
        self.frozen_files = {row["path"].replace("\\", "/"): row["sha256"] for row in manifest["files"]}
        self.frozen_files[manifest_path] = self.baseline[manifest_path]
        for item in self.inventory["sources"]:
            self.authorize(item["workspace_relative_path"], item["sha256"], item["purpose"], public_id=item["id"])

    def _path(self, value: str | Path) -> Path:
        p = Path(value)
        result = p if p.is_absolute() else ROOT / p
        resolved = result.resolve()
        if not resolved.is_relative_to(ROOT.resolve()):
            raise ValueError("Source outside the research workspace")
        return resolved

    def _key(self, value: str | Path) -> str:
        return self._path(value).relative_to(ROOT).as_posix()

    def check(self, condition: Any, label: str, **details: Any) -> None:
        record = {"check": label, "passed": bool(condition), **details}
        self.checks.append(record)
        if not record["passed"]:
            raise ValueError("Export validation failed: " + label)

    def authorize(self, relative: str | Path, expected_sha256: str, purpose: str,
                  *, public_id: str | None = None) -> None:
        key = self._key(relative)
        # The website needs selected recorded outcomes, never model binaries,
        # complete oracle/evaluation targets or compressed raw source snapshots.
        if any(token in key.lower() for token in ("oracle", "posthoc_target_access", "evaluation_label_access", ".joblib", ".pkl", ".npz", ".gz")):
            raise ValueError("This input is outside the public-export source policy: " + key)
        if key in self.inputs:
            self.check(self.inputs[key]["sha256"] == expected_sha256, "Consistent repeated source binding: " + key)
            return
        if key in self.frozen_files:
            self.check(self.frozen_files[key] == expected_sha256, "Source agrees with frozen manifest: " + key)
        else:
            original = next((row for row in self.inventory["sources"] if row["workspace_relative_path"] == key), None)
            self.check(original is not None and original["sha256"] == expected_sha256,
                       "Non-manifest input explicitly present in planning inventory: " + key)
        p = self._path(key)
        self.check(p.is_file() and sha_file(p) == expected_sha256, "Source bytes verified before use: " + key)
        source_id = public_id or "source-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        self.check(not any(row["sourceId"] == source_id for row in self.inputs.values()), "Unique public source ID: " + source_id)
        self.inputs[key] = {"path": key, "sourceId": source_id, "sha256": expected_sha256,
                            "bytes": p.stat().st_size, "purpose": purpose,
                            "label": (p.parent.name + "/" + p.name)}

    def source_id(self, relative: str | Path) -> str:
        key = self._key(relative)
        if key not in self.inputs:
            expected = self.frozen_files.get(key)
            if expected is None:
                raise ValueError("Referenced source is not in the frozen manifest: " + key)
            self.authorize(key, expected, "Referenced frozen evidence requested by the website exporter")
        return self.inputs[key]["sourceId"]

    def read_json(self, relative: str | Path) -> Any:
        self.source_id(relative)
        return json.loads(self._path(relative).read_text(encoding="utf-8"))

    def read_csv(self, relative: str | Path) -> list[dict[str, str]]:
        self.source_id(relative)
        with self._path(relative).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    def read_asset(self, relative: str | Path) -> bytes:
        self.source_id(relative)
        return self._path(relative).read_bytes()

    def add_json(self, logical_name: str, payload: dict) -> None:
        if not logical_name.endswith(".json") or ".." in Path(logical_name).parts or "\\" in logical_name or logical_name.startswith("/"):
            raise ValueError("Invalid public logical dataset name")
        if logical_name in self.payloads or not isinstance(payload, dict):
            raise ValueError("Duplicate dataset name or unsupported payload shape: " + logical_name)
        data = {"schemaVersion": SCHEMA_VERSION, "dataset": logical_name[:-5], "studyId": STUDY_ID, **payload}
        # Prove strict JSON at creation, before any output filesystem writes.
        json_bytes(data)
        self.payloads[logical_name] = data

    def add_asset(self, logical_name: str, content: bytes) -> None:
        if ".." in Path(logical_name).parts or "\\" in logical_name or logical_name.startswith("/") or logical_name in self.assets:
            raise ValueError("Invalid or duplicate asset name")
        self.assets[logical_name] = content

    def public_sources(self) -> list[dict]:
        return [{"sourceId": row["sourceId"], "label": row["label"], "sha256": row["sha256"],
                 "bytes": row["bytes"], "description": row["purpose"]}
                for row in sorted(self.inputs.values(), key=lambda row: row["sourceId"])]

    def verify_unchanged(self) -> None:
        for key, record in self.inputs.items():
            self.check(sha_file(self._path(key)) == record["sha256"], "Source remains unchanged after export: " + key)
        for key, expected in self.baseline.items():
            self.check(sha_file(self._path(key)) == expected, "Frozen baseline remains unchanged after export: " + key)
        self.check(sha_file(self.inventory_path) == self.inventory_sha256, "Planning source inventory remains unchanged during export")
