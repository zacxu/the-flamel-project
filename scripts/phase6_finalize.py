"""Close Phase 6 using saved evidence, with no experiment dispatch or label reads.

Only Phase 6 audit/readiness/manifest/numerical_freeze files are written. Earlier
phase closures stay immutable, including their archived versions of root docs.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
from urllib.parse import unquote

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase6"
CHECKS = []
FILES = {}
PROTOCOL_SHA = "b71724ad4e9a940de090d4163bc6a23a10ed9bfb957fb656b50222b884d36c94"
ACQUISITION_SHA = "68374dd88f03cf6f3652c79a46774993bdc3bb936459da214870ddfec07e1f7c"
SELECTOR_SHA = "b7cbae9c54cdc486bac5d9de743f3e75e2322bf7bf01a3f03f7b92acfa3e8359"


def path(value):
    p = Path(value)
    p = p if p.is_absolute() else ROOT / p
    if not p.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Input outside this workspace")
    return p


def digest(value):
    p = path(value)
    with p.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    FILES[p.relative_to(ROOT).as_posix()] = {"path": p.relative_to(ROOT).as_posix(),
                                           "sha256": sha, "bytes": p.stat().st_size}
    return sha


def read(value):
    digest(value)
    return json.loads(path(value).read_text(encoding="utf-8"))


def rows(value):
    digest(value)
    with path(value).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, value):
    if name not in {"audit.json", "readiness.json", "manifest.json", "numerical_freeze.json"}:
        raise ValueError("Closure output outside the allowed list")
    destination = OUT / name
    temporary = destination.with_suffix(".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, destination)


def check(condition, description, **detail):
    CHECKS.append({"check": description, "passed": bool(condition), **detail})


def close(a, b, tolerance=1e-9):
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=tolerance)


def check_descriptive(actual, expected, description):
    check(actual["values"] == expected and close(actual["mean"], statistics.mean(expected))
          and close(actual["sample_std"], statistics.stdev(expected)), description)


def historical_integrity(plan):
    latest = {}
    for phase in (3, 4, 5):
        manifest = read(f"artifacts/phase{phase}/manifest.json")
        for item in manifest["files"]:
            latest[item["path"]] = item
    archived = {item["path"]: item for item in plan["baseline"]}
    mutable_docs = {"README.md", "one_day_research_proposal.md"}
    for name, item in latest.items():
        source = archived[name]["archive"] if name in mutable_docs else name
        check(digest(source) == item["sha256"], "Frozen latest Phase 1-5 evidence checksum: " + name,
              archived_document=name in mutable_docs)
    return len(latest)


def lane_results(name):
    prefix = f"artifacts/phase6/{name}"
    summary = read(prefix + "/summary.json")
    audit = read(prefix + "/audit.json")
    checks = audit["checks"]
    check(audit["status"] == "passed" and not audit["failed_checks"]
          and audit["checks_total"] == audit["checks_passed"] == len(checks)
          and all(item["passed"] for item in checks), "All independent " + name + " lane checks passed")
    if "summary_sha256" in audit:
        check(digest(prefix + "/summary.json") == audit["summary_sha256"], name + " audit binds its final summary")
    else:
        check(summary["status"] == audit["status"] and summary["checks_total"] == audit["checks_total"]
              and not summary["failed_checks"], name + " summary and audit record the same completed checks")
    source = prefix + ("/source_manifest.json" if name == "uncertainty" else "/source_hashes.json")
    manifest = read(source)
    records = manifest["files"]
    records = [{"path": key, **value} for key, value in records.items()] if isinstance(records, dict) else records
    for record in records:
        check(digest(record["path"]) == record["sha256"], name + " input/source checksum: " + record["path"])
    return summary, audit


def main():
    plan = read("artifacts/phase6/execution_plan.json")
    baseline_map = {item["path"]: item for item in plan["baseline"]}
    budget = read("artifacts/budget_ledger.json")
    event_sha = digest("artifacts/runtime_budget_events.jsonl")
    events = [json.loads(line) for line in path("artifacts/runtime_budget_events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    for item in plan["baseline"]:
        check(digest(item["archive"]) == item["sha256"], "Phase 6 preflight archive checksum: " + item["path"])
        if item["path"] not in {"README.md", "one_day_research_proposal.md"}:
            check(digest(item["path"]) == item["sha256"], "Phase 6 preserves prior numerical evidence: " + item["path"])
    check(event_sha == baseline_map["artifacts/runtime_budget_events.jsonl"]["sha256"]
          and digest("artifacts/budget_ledger.json") == baseline_map["artifacts/budget_ledger.json"]["sha256"],
          "No new experiments or canonical budget writes during Phase 6")
    check(all(row.get("phase", 0) <= 5 for row in events) and budget["phase"] == 5,
          "Latest numerical-job phase remains Phase 5; the analysis phase creates no synthetic reservation")
    starts = {row["reservation_id"]: row for row in events if row["event"] == "reserved"}
    ends = {row["reservation_id"]: row for row in events if row["event"] == "finished"}
    check(set(starts) == set(ends) and all(not budget[lane]["active_reservations"] for lane in ("generation", "chgnet", "qe")),
          "Every reservation is finished and all numerical lanes are idle")
    check(not path("artifacts/runtime_budget.lock").exists() and not path("artifacts/phase1/qe/qe_active.lock").exists(),
          "No active numerical ownership locks remain")
    check(digest("config/phase2_protocol.json") == PROTOCOL_SHA and digest("research_acquisition.py") == ACQUISITION_SHA
          and digest("artifacts/phase3/models/fresh_selector_seed_20261022.joblib") == SELECTOR_SHA,
          "Scientific protocol, acquisition code and pre-query fresh selector remain unchanged")
    historical_count = historical_integrity(plan)
    uncertainty, ua = lane_results("uncertainty")
    structures, sa = lane_results("structures")
    evidence, ea = lane_results("evidence")
    check(evidence["numerical_decision"]["required_allowed_unfinished_job_count"] == 0
          and evidence["numerical_decision"]["new_numerical_jobs_dispatched_phase6"] == 0
          and evidence["no_numerical_or_oracle_jobs"] and evidence["frozen_phase5_end_state_unchanged"],
          "Independent numerical review finds no required eligible unfinished job or new experiment")
    check(not evidence["full_hull_established"] and not evidence["new_stable_material_established"]
          and not evidence["perturbation_validation_complete"] and not evidence["phonon_calculation_performed"],
          "Independent DFT review supports only the scoped accepted anchors and incomplete perturbation")
    for system, total, accepted, missing in (("Ca-Mg-O", 161, 2, 159), ("Mg-O", 57, 1, 56)):
        coverage = evidence["reference_coverage"][system]
        check(coverage["frozen_entries"] == total and coverage["accepted_fresh_compatible_QE"] == accepted
              and coverage["missing"] == missing and not coverage["full_inventory_complete"],
              "Independent reference inventory completeness: " + system)
        other = structures["DFT_validation"]["competitor_coverage"][system]
        check(other["frozen_entries"] == total and other["accepted_original_source_references"] == accepted
              and other["uncomputed_original_source_entries"] == missing and not other["full_inventory_hull_established"],
              "Independent structure and DFT lanes agree on inventory coverage: " + system)
    known = structures["DFT_validation"]["known_control"]
    check(close(known["candidate_minus_reference_eV_per_atom"], evidence["known_MgO_candidate_minus_reference_eV_atom"], 1e-12)
          and known["structure_match"] == evidence["known_MgO_final_reference_structure_match"]
          and not known["energy_ordering_resolved"] and not evidence["known_MgO_energy_ordering_resolved"],
          "Independent lanes agree on known-MgO recovery and unresolved tiny energy difference")
    check(uncertainty["saved_prediction_sets_recomputed"] == 130 and uncertainty["policy_own_label_lineage_rounds_verified"] == 125,
          "All 130 held-out prediction sets and 125 policy refit lineages were independently checked")
    for key in ("new_pool_queries", "new_model_fits", "new_model_predictions", "new_calibration_fits"):
        check(uncertainty[key] == 0, "Posthoc uncertainty analysis performs no " + key)
    check(uncertainty["reserved_chemical_systems"] == 78 and uncertainty["observed_reserved_systems"] == 74
          and uncertainty["reserved_rows"] == 476, "All observed reserved chemistry rows are kept outside each predictor split")
    endpoints = rows("artifacts/phase4/replay/per_seed_policy_metrics.csv")
    for policy in ("random", "quality", "quality_diversity", "uncertainty", "full"):
        selected = sorted([row for row in endpoints if row["policy"] == policy], key=lambda row: row["seed"])
        for key, source_key in (("near_stable_hits", "near_stable_hits"), ("precision_at_50", "precision_at_50"),
                                ("reference_hull_hits", "reference_hull_hits"), ("chemical_system_coverage", "chemical_system_coverage_at_50")):
            values = [float(row[source_key]) for row in selected]
            check_descriptive(uncertainty["policy_endpoint_aggregates"][policy][key], values,
                              "Independent five-seed descriptive aggregate: " + policy + ":" + key)
    differences = [row["full_minus_quality_hits"] for row in uncertainty["paired_differences"]]
    check(differences == [-9, -8, -19, -10, -13], "Negative full-minus-quality outcome is retained for every frozen seed")
    check_descriptive(uncertainty["full_minus_quality_hits"], differences, "Paired hit difference mean and sample SD reproduced")
    access = read("artifacts/phase6/uncertainty/posthoc_target_access.json")
    check(access["new_pool_labels_revealed"] == access["reserved_labels_decoded"] == access["unrequested_numeric_values_decoded"] == 0
          and access["decisions_complete_before_this_analysis"] and access["previously_evaluated_IDs_decoded"] == len(access["target_IDs"]),
          "Target decoding is documented as posthoc re-use of previously evaluated IDs only")
    for key in ("new_generator_draws", "new_predictor_fits_or_predictions", "new_CHGNet_launches", "new_QE_jobs"):
        check(structures[key] == 0, "Structure/novelty audit performs no " + key)
    old_chg = read("artifacts/phase5/chgnet/summary.json")
    check(old_chg["converged_selections"] == old_chg["selections"] == 11 and old_chg["new_CHGNet_launches"] == 10
          and old_chg["cached_reuses"] == 1, "Complete CHGNet experimental and compute counts remain distinct")
    old_qe = read("artifacts/phase5/qe/summary.json")
    check(old_qe["perturbation_validation_incomplete"] and not old_qe["perturbation_final_geometry_numerical_checks_pass"]
          and old_qe["accepted_perturbation_job_id"] is None and not old_qe["final_geometry_sensitivity_checks"],
          "The terminal-SCF-failed perturbation remains incomplete, with no continuation or finite-probe claim")
    shortlist = read("artifacts/phase4/selection/fresh_shortlist.json")
    check(shortlist["selected_count"] == 0 and not shortlist["default_CaMg_DFT_queue_changed"],
          "No larger-cell diagnostic or prototype replaces the frozen empty transformer shortlist")
    check(budget["generation"]["charged_attempts"] == 96 and budget["generation"]["remaining_attempts"] == 32
          and budget["chgnet"]["charged_attempts"] == 19 and budget["chgnet"]["remaining_attempts"] == 21
          and budget["qe"]["completed_jobs"] == 19, "All original actual/failed/cached workload counts remain accounted for")
    check(budget["generation"]["ceiling_attempts"] == 128 and budget["chgnet"]["ceiling_attempts"] == 40
          and budget["chgnet"]["ceiling_seconds"] == 14400 and budget["qe"]["ceiling_seconds"] == 21600,
          "Original attempt and cumulative-time ceilings remain unchanged")
    cutoff = datetime.fromisoformat(budget["numerical_stop_utc"])
    check(budget["numerical_stop_utc"] == "2026-10-22T10:24:44+00:00"
          and all(datetime.fromisoformat(row["finished_utc"]) <= cutoff for row in ends.values()),
          "All experiments ended before the original 18:24:44 Singapore hard stop")
    prior_manifest_path = OUT / "manifest.json"
    if prior_manifest_path.exists():
        previous = read(prior_manifest_path)
        if previous["final_numerical_evidence"]["runtime_events_sha256"] != event_sha:
            raise RuntimeError("Numerical evidence changed after Phase 6 freeze; refusing historical rewrite")
    deferred = {(OUT / name).resolve() for name in ("audit.json", "manifest.json", "readiness.json", "numerical_freeze.json")}
    for name in ("reports/phase6_report.md", "README.md", "one_day_research_proposal.md", "artifacts/phase6/current_submission_requirements.md"):
        document = path(name); digest(document)
        text = document.read_text(encoding="utf-8")
        check(chr(65533) not in text and not re.search(r"\b(?:TBD|TODO|PLACEHOLDER)\b", text), "Final document has complete UTF-8 content: " + name)
        for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            target = unquote(link.strip().strip("<>").split("#", 1)[0])
            if not target or re.match(r"(?:https?://|mailto:)", target):
                continue
            resolved = (document.parent / target).resolve()
            check(resolved.is_file() or resolved in deferred, "Final local document link resolves: " + name + ":" + target)
    for source in sorted((ROOT / "scripts").glob("phase6*.py")):
        digest(source)
    for source in sorted(OUT.rglob("*")):
        if source.is_file() and source != prior_manifest_path and source.name not in {"audit.json", "readiness.json", "numerical_freeze.json"} and source.suffix != ".partial":
            digest(source)
    check(digest("artifacts/runtime_budget_events.jsonl") == event_sha, "Final audit itself dispatches no jobs and leaves the experimental ledger unchanged")
    failed = [item for item in CHECKS if not item["passed"]]
    completed = datetime.now(timezone.utc).isoformat()
    if failed:
        write("audit.json", {"phase": 6, "status": "failed", "audited_utc": completed,
              "checks_total": len(CHECKS), "checks_passed": len(CHECKS)-len(failed),
              "failed_checks": failed, "checks": CHECKS,
              "new_experiment_dispatches": 0, "canonical_budget_writes": 0})
        print(json.dumps({"status": "failed", "failed": failed, "ready_for_phase7": False}))
        return 1
    frozen = {"phase": 6, "frozen_utc": completed, "status": "frozen" if not failed else "audit_failed",
              "budget_ledger": budget, "budget_ledger_sha256": digest("artifacts/budget_ledger.json"),
              "runtime_events_sha256": event_sha, "runtime_event_count": len(events),
              "new_phase6_experiments": 0, "canonical_budget_writes": 0,
              "hard_stop_utc": budget["numerical_stop_utc"],
              "ended_before_hard_stop": all(datetime.fromisoformat(row["finished_utc"]) <= cutoff for row in ends.values()),
              "scope": "Final evidence for this frozen study. Phases 7-8 may analyze/audit/package it without new experiment dispatch. Read-only metric recomputation is distinct from new physical/model experiments.",
              "mechanism": "Hash-bound closure record verified against the unchanged runtime event ledger; no change to the already frozen dispatch API.",
              "DFT_perturbation_status": "Incomplete terminal SCF; no continuation/probes permitted by its original queue",
              "no_new_stable_material_established": True}
    existing_freeze = OUT / "numerical_freeze.json"
    if existing_freeze.exists():
        prior = read(existing_freeze)
        if prior["status"] != "frozen":
            raise RuntimeError("Existing closure did not pass; it is not an accepted numerical freeze")
        if prior["runtime_events_sha256"] != event_sha or prior["budget_ledger_sha256"] != frozen["budget_ledger_sha256"]:
            raise RuntimeError("Final numerical freeze cannot be changed")
        frozen = prior
    else:
        write("numerical_freeze.json", frozen)
    audit = {"phase": 6, "status": "passed" if not failed else "failed", "audited_utc": completed,
             "checks_total": len(CHECKS), "checks_passed": len(CHECKS)-len(failed), "failed_checks": failed, "checks": CHECKS,
             "independent_lane_check_counts": {"uncertainty": ua["checks_total"], "structures": sa["checks_total"], "evidence": ea["checks_total"]},
             "prior_latest_manifest_paths_checked": historical_count,
             "new_experiment_dispatches": 0, "canonical_budget_writes": 0,
             "oracle_labels_decoded_by_finalizer": 0,
             "evaluation_target_reuse_scope": "The separate uncertainty lane decodes only previously evaluated IDs after all decisions; this finalizer checks metadata and file hashes only."}
    write("audit.json", audit)
    readiness = {"phase": 6, "status": "complete" if not failed else "audit_failed", "completed_utc": completed,
                 "ready_for_phase7": not failed, "numerical_evidence_frozen": not failed,
                 "scientific_protocol_sha256": PROTOCOL_SHA, "original_fresh_selector_sha256": SELECTOR_SHA,
                 "all_five_paired_replay_seeds_complete": True, "saved_evaluation_prediction_sets_recomputed": 130,
                 "full_minus_quality_hits": uncertainty["full_minus_quality_hits"],
                 "symmetry_energy_scope": "One structure per arm; same architecture with changed conditioning; supplemented MgO kept separate",
                 "fresh_primary_transformer_candidates": 0, "converged_CHGNet_selections": 11,
                 "accepted_QE_source_reference_entries": 2, "frozen_primary_reference_entries": 161,
                 "not_completed_primary_reference_entries": 159, "perturbation_validation_incomplete": True,
                 "new_stable_material_established": False, "complete_hull_established": False,
                 "remaining_generation_slots_unused": 32, "remaining_CHGNet_launches_unused": 21,
                 "remaining_QE_seconds_unused": budget["qe"]["remaining_seconds"],
                 "report": "reports/phase6_report.md", "main_figure": "artifacts/phase6/figures/research_overview.png",
                 "phase7_tasks": ["Write the one-page research account using frozen claims and figures",
                                  "Prepare and record a presentation of at most four minutes",
                                  "Package reproducible code/configurations and representative structures",
                                  "Prepare public repository/video-post links and the Moment team entry"],
                 "phase8_tasks": ["Check public access, duration/page limits, repository contents and all scientific claims",
                                  "Verify Moment team membership and platform declaration; perform the authorized final submission"],
                 "submission_requirements": "artifacts/phase6/current_submission_requirements.md",
                 "submission_deadline_utc": "2026-10-23T00:00:00+00:00",
                 "publication_or_submission_performed": False,
                 "review_command": ".envs/analysis/Scripts/python.exe scripts/phase6_finalize.py"}
    write("readiness.json", readiness)
    for name in ("audit.json", "readiness.json", "numerical_freeze.json"):
        digest(OUT / name)
    write("manifest.json", {"phase": 6, "status": "complete" if not failed else "audit_failed", "created_utc": completed,
                            "final_numerical_evidence": frozen, "files": [FILES[key] for key in sorted(FILES) if key != "artifacts/phase6/manifest.json"],
                            "scope": "Latest immutable Phase 1-5 sources/results, archived prior root docs, Phase 6 analyses/audits/figures, current docs and unchanged final numerical ledgers."})
    print(json.dumps({"status": audit["status"], "checks": len(CHECKS), "failed": failed,
                      "manifest_files": len(FILES), "ready_for_phase7": not failed}))
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
