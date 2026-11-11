"""Atomic reservations for every new generation, CHGNet and QE attempt.

Reservations charge attempt counts before dispatch. Runtime ceilings reserve the
entire watchdog allowance until an actual finish record replaces it. An unknown
unfinished job keeps its reservation; it is never silently released or retried.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "artifacts/phase3/budget_baseline.json"
EVENTS = ROOT / "artifacts/runtime_budget_events.jsonl"
CANONICAL = ROOT / "artifacts/budget_ledger.json"
LOCK = ROOT / "artifacts/runtime_budget.lock"
CATEGORIES = {"symmetry": 10, "new_composition_shortlist": 12,
              "prototype": 4, "same_composition_reference": 4, "contingency": 2}


def utc():
    return datetime.now(timezone.utc).isoformat()


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def _locked():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15
    while True:
        try:
            descriptor = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, json.dumps({"pid": os.getpid(), "utc": utc()}).encode())
            os.close(descriptor)
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise RuntimeError("Budget lock is busy. Inspect its recorded owner; do not delete active locks.")
            time.sleep(.05)
    try:
        yield
    finally:
        LOCK.unlink()


def _events():
    if not EVENTS.exists():
        return []
    return [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(event):
    with EVENTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _state():
    if not BASELINE.exists():
        raise RuntimeError("Initialize the Phase3 budget baseline before dispatching any new job")
    baseline = _read(BASELINE)
    state = json.loads(json.dumps(baseline["budget"]))
    state.update(phase=3, as_of_utc=utc(), runtime_event_ledger=EVENTS.relative_to(ROOT).as_posix())
    stream = _events()
    starts = {row["reservation_id"]: row for row in stream if row["event"] == "reserved"}
    finishes = {row["reservation_id"]: row for row in stream if row["event"] == "finished"}
    active = {key: row for key, row in starts.items() if key not in finishes}
    for lane in ["generation", "chgnet", "qe"]:
        charged_starts = [row for row in starts.values() if row["lane"] == lane]
        charged_finishes = [finishes[key] for key, row in starts.items() if row["lane"] == lane and key in finishes]
        lane_active = [row for row in active.values() if row["lane"] == lane]
        if lane in {"generation", "chgnet"}:
            state[lane]["charged_attempts"] += sum(row["attempts"] for row in charged_starts)
            state[lane]["remaining_attempts"] = state[lane]["ceiling_attempts"] - state[lane]["charged_attempts"]
        if lane == "generation":
            state[lane]["CrystalFormer_sample_attempts"] += sum(row["attempts"] for row in charged_starts if row["category"] == "crystalformer")
            state[lane]["cumulative_new_job_wall_seconds"] = sum(row["wall_seconds"] for row in charged_finishes)
            state[lane]["CrystalFormer_sample_attempts_interpretation"] = (
                "Conservatively charged CrystalFormer reservation slots, not the number of emitted model draws. "
                "Unemitted slots remain charged after a failed reservation; use cohort evidence to identify actual draws. "
                "The Phase3 early cohort charged 12 slots for 8 actual draws plus 4 unemitted engineering slots."
            )
            state[lane]["timing_scope"] = (
                "cumulative_sampling_seconds and cumulative_run_seconds_including_initialization_and_conversion "
                "retain only the measured Phase1 baseline captured in Phase2; they are not total timings for later sampling. "
                "cumulative_new_job_wall_seconds sums finished post-baseline generation-job walltime, including failures "
                "and recovery. Phase3 pure sampling time was not completely recovered and must not be inferred from these totals."
            )
        else:
            state[lane]["charged_wall_seconds"] += sum(row["wall_seconds"] for row in charged_finishes)
            state[lane]["remaining_seconds"] = state[lane]["ceiling_seconds"] - state[lane]["charged_wall_seconds"]
            state[lane]["reserved_inflight_seconds"] = sum(row["max_seconds"] for row in lane_active)
            state[lane]["available_unreserved_seconds"] = state[lane]["remaining_seconds"] - state[lane]["reserved_inflight_seconds"]
        if lane == "qe":
            state[lane]["completed_jobs"] += len(charged_finishes)
        if lane == "chgnet":
            state[lane]["actual_relaxations"] += sum(bool(row.get("metadata", {}).get("relaxation_started", False)) for row in charged_finishes)
            state[lane]["new_runtime_launches"] = len(charged_starts)
        state[lane]["active_reservations"] = [row["reservation_id"] for row in lane_active]
        state[lane]["source_ledgers"] = list(dict.fromkeys(state[lane]["source_ledgers"] + [EVENTS.relative_to(ROOT).as_posix()]))
    state["chgnet"]["phase3_and_later_category_charged_attempts"] = {
        category: sum(row["attempts"] for row in starts.values() if row["lane"] == "chgnet" and row["category"] == category)
        for category in CATEGORIES}
    state["note"] = "Canonical state reconstructed from immutable Phase2 totals plus append-only runtime reservations. Counts are charged before dispatch; unfinished runtime reservations remain unavailable. Every failed/retried job is retained."
    return state, starts, finishes, active


def initialize():
    """Capture the exact Phase2 state once; safe to call again for inspection."""
    with _locked():
        if not BASELINE.exists():
            if EVENTS.exists() and EVENTS.stat().st_size:
                raise RuntimeError("Runtime events exist without a baseline; inspect before proceeding")
            budget = _read(CANONICAL)
            if budget["phase"] != 2 or budget["generation"]["charged_attempts"] != 12 or budget["chgnet"]["charged_attempts"] != 8:
                raise RuntimeError("Expected the frozen Phase2 totals (12 structures,8 CHGNet launches)")
            source = ROOT / "config/phase2_protocol.json"
            _atomic(BASELINE, {"initialized_utc": utc(), "budget": budget,
                               "phase2_protocol_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                               "phase2_canonical_budget_sha256": hashlib.sha256(CANONICAL.read_bytes()).hexdigest()})
        state, _, _, _ = _state()
        _atomic(CANONICAL, state)
        return state


def snapshot():
    with _locked():
        state, _, _, _ = _state()
        _atomic(CANONICAL, state)
        return state


def reserve_job(lane, job_id, attempts=1, max_seconds=900, phase=3, category="", metadata=None):
    """Reserve before any sampling/relaxation/QE process is dispatched."""
    if lane not in {"generation", "chgnet", "qe"} or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("Expected a supported lane and positive integer attempt count")
    if not job_id or not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("Expected a unique job ID and finite positive watchdog allowance")
    if lane in {"chgnet", "qe"} and attempts != 1:
        raise ValueError("CHGNet/QE jobs must reserve one attempt individually")
    with _locked():
        state, starts, _, active = _state()
        if job_id in starts:
            raise RuntimeError(f"Job ID already reserved: {job_id}; inspect/reuse its artifacts, never silently rerun")
        deadline = datetime.fromisoformat(state["numerical_stop_utc"])
        if datetime.now(timezone.utc) + timedelta(seconds=max_seconds) > deadline:
            raise RuntimeError("Requested watchdog extends beyond the project's numerical stop")
        if lane in {"generation", "chgnet"} and attempts > state[lane]["remaining_attempts"]:
            raise RuntimeError(f"Insufficient {lane} attempt capacity")
        if lane in {"chgnet", "qe"} and max_seconds > state[lane]["available_unreserved_seconds"]:
            raise RuntimeError(f"Insufficient unreserved {lane} walltime")
        if lane == "qe" and any(row["lane"] == "qe" for row in active.values()):
            raise RuntimeError("One QE reservation is already active; wait for its recorded finish")
        if lane == "chgnet":
            if category not in CATEGORIES:
                raise ValueError(f"Unknown frozen CHGNet allocation: {category}")
            charged = state[lane]["phase3_and_later_category_charged_attempts"][category]
            if charged + attempts > CATEGORIES[category]:
                raise RuntimeError(f"CHGNet category cap reached: {category}")
        record = {"event": "reserved", "reservation_id": str(job_id), "lane": lane,
                  "phase": phase, "category": category, "attempts": attempts,
                  "max_seconds": float(max_seconds), "reserved_utc": utc(),
                  "dispatcher_pid": os.getpid(), "metadata": metadata or {}}
        _append(record)
        updated, _, _, _ = _state()
        _atomic(CANONICAL, updated)
        return {"reservation_id": str(job_id), "lane": lane, "attempts": attempts,
                "max_seconds": float(max_seconds), "reserved_utc": record["reserved_utc"]}


def finish_job(ticket_or_id, wall_seconds, status, metadata=None):
    """Charge actual elapsed process time, including failures and watchdog timeouts."""
    key = ticket_or_id["reservation_id"] if isinstance(ticket_or_id, dict) else str(ticket_or_id)
    if not math.isfinite(wall_seconds) or wall_seconds < 0 or status not in {"completed", "failed", "timeout", "aborted"}:
        raise ValueError("Expected finite nonnegative elapsed time and an explicit terminal status")
    with _locked():
        _, starts, finishes, _ = _state()
        if key not in starts or key in finishes:
            raise RuntimeError("Finish must refer to exactly one unfinished reservation")
        start = starts[key]
        _append({"event": "finished", "reservation_id": key, "lane": start["lane"],
                 "phase": start["phase"], "status": status, "finished_utc": utc(),
                 "wall_seconds": float(wall_seconds), "attempts": start["attempts"],
                 "watchdog_allowance_exceeded": wall_seconds > start["max_seconds"],
                 "metadata": metadata or {}})
        state, _, _, _ = _state()
        _atomic(CANONICAL, state)
        return state
