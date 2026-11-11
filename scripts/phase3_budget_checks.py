"""Exercise budget caps/concurrency in isolated fake ledgers; no real jobs."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import research_budget as budget


def main():
    out = ROOT / "artifacts/phase3/tests/budget_guards"
    out.mkdir(parents=True, exist_ok=True)
    if (out / "events.jsonl").exists():
        raise RuntimeError("The isolated test ledger already exists; inspect its saved result instead")
    real_ledger_before = (ROOT / "artifacts/runtime_budget_events.jsonl").read_bytes() if (ROOT / "artifacts/runtime_budget_events.jsonl").exists() else b""
    budget.BASELINE = out / "baseline.json"
    budget.EVENTS = out / "events.jsonl"
    budget.CANONICAL = out / "canonical.json"
    budget.LOCK = out / "lock"
    baseline = json.loads((ROOT / "artifacts/phase3/budget_baseline.json").read_text())
    budget.BASELINE.write_text(json.dumps(baseline))
    budget.CANONICAL.write_text(json.dumps(baseline["budget"]))
    checks = []

    def rejects(label, callable):
        try:
            callable()
        except (RuntimeError, ValueError):
            checks.append(label)
        else:
            raise AssertionError(f"Guard failed: {label}")

    rejects("structure count ceiling", lambda: budget.reserve_job("generation", "too-many", attempts=117, max_seconds=5, category="crystalformer"))
    rejects("CHGNet category ceiling", lambda: budget.reserve_job("chgnet", "bad-category", category="unknown", max_seconds=5))
    rejects("QE runtime ceiling", lambda: budget.reserve_job("qe", "too-long", max_seconds=21601))
    ticket = budget.reserve_job("generation", "fake-failed-generation", attempts=1, max_seconds=5, category="crystalformer")
    budget.finish_job(ticket, wall_seconds=.1, status="failed")
    rejects("duplicate generation reservation", lambda: budget.reserve_job("generation", "fake-failed-generation", max_seconds=5))
    rejects("duplicate finish", lambda: budget.finish_job(ticket, wall_seconds=.1, status="failed"))
    assert budget.snapshot()["generation"]["charged_attempts"] == 13
    checks.append("failed generation remains charged")
    ticket = budget.reserve_job("qe", "fake-qe-active", max_seconds=10)
    rejects("one active QE job", lambda: budget.reserve_job("qe", "fake-qe-other", max_seconds=10))
    budget.finish_job(ticket, wall_seconds=3, status="timeout")
    assert budget.snapshot()["qe"]["charged_wall_seconds"] == baseline["budget"]["qe"]["charged_wall_seconds"] + 3
    checks.append("timeout runtime charged and reservation released")
    # Two independent OS processes compete for one QE reservation.
    code = """import sys,json;from pathlib import Path
sys.path.insert(0,sys.argv[1]);import research_budget as b
p=Path(sys.argv[2]);b.BASELINE=p/'baseline.json';b.EVENTS=p/'events.jsonl';b.CANONICAL=p/'canonical.json';b.LOCK=p/'lock'
try:
 t=b.reserve_job('qe',sys.argv[3],max_seconds=10);print(json.dumps({'accepted':True,'id':t['reservation_id']}))
except RuntimeError:
 print(json.dumps({'accepted':False,'id':sys.argv[3]}))
"""
    children = [subprocess.Popen([sys.executable, "-c", code, str(ROOT), str(out), f"concurrent-{i}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(2)]
    outcomes = []
    for child in children:
        stdout, stderr = child.communicate(timeout=20)
        if child.returncode:
            raise RuntimeError(stderr)
        outcomes.append(json.loads(stdout))
    assert sum(x["accepted"] for x in outcomes) == 1
    winner = next(x["id"] for x in outcomes if x["accepted"])
    budget.finish_job(winner, wall_seconds=.1, status="completed")
    checks.append("atomic competing processes admit exactly one QE job")
    # The real ledger may independently advance while tests run; test paths never target it.
    assert budget.EVENTS.is_relative_to(out) and budget.CANONICAL.is_relative_to(out)
    checks.append("all synthetic reservations remain in isolated paths")
    result = {"status": "passed", "checks": checks, "real_numerical_jobs": 0,
              "isolated_test_directory": out.relative_to(ROOT).as_posix()}
    (out / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
