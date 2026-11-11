"""Consolidate completed Phase 4 evidence without fitting or numerical jobs.

Reads revealed replay journals, saved predictions/commitments, raw artifact
hashes and QE XML. Never reads the private oracle-label file, changes a lane's
artifacts, dispatches a job, or updates the canonical budget. Run only after all
lanes, the report and the handoffs have been completed.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase4"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
PROTOCOL_SHA = "b71724ad4e9a940de090d4163bc6a23a10ed9bfb957fb656b50222b884d36c94"
FRESH_SHA = "b7cbae9c54cdc486bac5d9de743f3e75e2322bf7bf01a3f03f7b92acfa3e8359"
SEEDS = list(range(20261022, 20261027))
POLICIES = ["random", "quality", "quality_diversity", "uncertainty", "full"]
CHECKS, INVENTORY = [], {}


def path(value):
    result = (ROOT / value).resolve()
    if not result.is_relative_to(ROOT): raise RuntimeError("Audit path leaves workspace")
    if result.name == "oracle_labels.csv": raise RuntimeError("Oracle access forbidden in evidence audit")
    return result


def sha(value):
    target = path(value)
    with target.open("rb") as stream: digest = hashlib.file_digest(stream, "sha256").hexdigest()
    INVENTORY[target.relative_to(ROOT).as_posix()] = {"path": target.relative_to(ROOT).as_posix(),
        "sha256": digest, "bytes": target.stat().st_size}
    return digest


def read(value):
    target = path(value); sha(target)
    return json.loads(target.read_text(encoding="utf-8-sig"))


def jsonl(value):
    target = path(value); sha(target)
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def check(value, description): CHECKS.append({"passed": bool(value), "check": description})
def close(a, b, tolerance=1e-10): return math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance)
def save(name, value):
    if name not in {"audit.json", "readiness.json", "manifest.json"}: raise RuntimeError("Unsupported audit output")
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def check_stats(saved, values, description):
    check(saved["values"] == list(values) and saved["n"] == len(values), description+": all seed values")
    for key, actual in {"mean": statistics.mean(values), "sample_std": statistics.stdev(values),
                        "min": min(values), "max": max(values)}.items():
        check(close(saved[key], actual), description+": "+key)


def audit_replay(aggregate):
    check(aggregate["status"] == "completed" and aggregate["seeds"] == SEEDS, "All five original paired seeds complete")
    check(aggregate["policy_query_events"] == 1250 and aggregate["phase4_new_policy_query_events"] == 1000,
          "Replay query-event totals: 1250 overall and 1000 new")
    check(not aggregate["hyperparameters_or_coefficients_changed_after_outcomes"] and
          not aggregate["oracle_file_read_by_aggregate"] and aggregate["no_best_seed_or_adapted_model_used_for_fresh_selection"],
          "Frozen acquisition settings and original fresh selector retained")
    row_metadata = path("artifacts/phase2/features/row_metadata.csv"); sha(row_metadata)
    with row_metadata.open(encoding="utf-8", newline="") as stream:
        systems = {row["material_id"]: row["chemical_system"] for row in csv.DictReader(stream)}
    values_by_policy = {p: {k: [] for k in ("near_stable_hits", "precision_at_50", "reference_hull_hits", "chemical_system_coverage_at_50", "adapted_fit_calibration_seconds")} for p in POLICIES}
    differences, query_events = [], 0
    for seed in SEEDS:
        phase = 3 if seed == SEEDS[0] else 4
        base = f"artifacts/phase{phase}/replay/seed_{seed}"
        summary = read(base+"/summary.json")
        record = next(item for item in aggregate["per_seed"] if item["seed"] == seed)
        for field, hash_field in [("source_summary_path", "source_summary_sha256"), ("query_journal_path", "query_journal_sha256"), ("audit_path", "audit_sha256")]:
            check(sha(record[field]) == record[hash_field], f"Aggregate source hash: {seed}/{field}")
        audit = read(f"artifacts/phase4/replay/audits/seed_{seed}.json")
        check(audit["status"] == "passed" and audit["paired_seed"] == seed and audit["policy_queries"] == 250,
              f"Independent per-seed audit: {seed}")
        for key, expected in {"decisions_replayed_from_pre_reveal_predictions": 25, "recomputed_bootstrap_plans": 125,
                              "recomputed_initial_bootstrap_plans": 5, "recomputed_calibrations": 26,
                              "verified_model_snapshots": 26, "fixed_evaluation_rows": 3418}.items():
            check(audit[key] == expected, f"Per-seed audit coverage {seed}/{key}")
        for key in ["all_training_ids_initial_plus_only_own_policy_queries", "all_calibration_ids_fixed",
                    "all_decisions_serialized_before_reveals", "all_evaluator_labels_read_after_all_policy_queries_complete",
                    "all_models_and_decision_reveal_fit_hashes_valid", "original_fresh_snapshot_unchanged"]:
            check(audit[key], f"Per-seed causal guard {seed}/{key}")
        check(not audit["oracle_file_read_by_auditor"], f"Per-seed auditor read no oracle: {seed}")
        split_record = read(f"artifacts/phase2/splits/seed_{seed}.json")
        split = split_record["material_ids"]
        check(summary["provenance"]["split_sha256"] == sha(f"artifacts/phase2/splits/seed_{seed}.json") and
              summary["provenance"]["protocol_sha256"] == PROTOCOL_SHA and
              summary["provenance"]["acquisition_source_sha256"] == sha("research_acquisition.py"), f"Frozen split/protocol/acquisition provenance: {seed}")
        check([len(split[k]) for k in ["train", "calibration", "pool", "unused"]] == [2000,400,2000,3418], f"Frozen split sizes: {seed}")
        check(split_record["whole_systems_only"] and not split_record["target_labels_read_for_split_selection"], f"Whole-system split eligibility: {seed}")
        check(summary["status"] == "completed" and summary["total_policy_queries"] == 250 and
              summary["evaluation_rows"] == 3418 and not summary["evaluator_metric_feedback_to_decisions"], f"Completed seed summary: {seed}")
        check({item["policy"] for item in summary["policies"]} == set(POLICIES), f"All five policies retained: {seed}")
        journal_path = path(base+"/query_journal.csv"); sha(journal_path)
        with journal_path.open(encoding="utf-8", newline="") as stream: journal = list(csv.DictReader(stream))
        check(len(journal) == 250 and sha(journal_path) == audit["query_journal_sha256"], f"250 revealed journal events: {seed}")
        query_events += len(journal)
        model_manifest = ("artifacts/phase3/models/fresh_selector_seed_20261022.manifest.json" if phase == 3
                          else f"artifacts/phase4/models/seed_{seed}/initial_paired_seed_{seed}.manifest.json")
        initial = read(model_manifest)
        check(sha(initial["path"]) == initial["sha256"] == audit["initial_snapshot_sha256"], f"Initial model commitment: {seed}")
        check(initial["pool_queries_revealed_before_snapshot"] == 0 and initial["evaluation_labels_read_before_snapshot"] == 0 and
              initial["train_ids"] == split["train"] and initial["calibration_ids"] == split["calibration"], f"Initial model labels/snapshot chronology: {seed}")
        finished_marker = read(base+"/all_policy_queries_complete.json")
        evaluator_access = jsonl(base+"/evaluation_label_access.jsonl")
        check(finished_marker["total_policy_queries"] == 250 and finished_marker["evaluator_labels_read_so_far"] == 0,
              f"All policy decisions finish before evaluator access: {seed}")
        for access in evaluator_access:
            check(access["utc_started"] >= finished_marker["completed_at_utc"] and access["count"] == 3418 and
                  set(access["material_ids"]) == set(split["unused"]) and access["unrequested_numeric_values_decoded"] == 0,
                  f"Isolated evaluator accesses only fixed untouched IDs after queries: {seed}")
        check(bool(evaluator_access), f"Recorded isolated evaluation access: {seed}")
        evaluator = read(base+"/evaluation_summary.json")
        check(evaluator["policy_decisions_finished_before_label_access"] and set(evaluator["evaluation_ids"]) == set(split["unused"]) and
              len(evaluator["evaluated_predictions"]) == 26, f"26 fixed evaluation prediction sets: {seed}")
        earliest_access = min(item["utc_started"] for item in evaluator_access)
        for item in evaluator["evaluated_predictions"]:
            check(item["n"] == 3418 and item["labels_returned_to_learner"] == 0 and sha(item["prediction_path"]) == item["prediction_sha256"],
                  f"Untouched evaluation prediction commitment: {seed}/{item['prediction_path']}")
            commit_path = path(item["prediction_path"]).with_suffix(".commit.json")
            commitment = read(commit_path)
            check(commitment["created_at_utc"] <= earliest_access and not commitment["oracle_labels_in_file"] and
                  commitment["rows"] == 3418 and commitment["sha256"] == item["prediction_sha256"], f"Predictions committed before evaluator labels: {seed}/{item['prediction_path']}")
        result_by_policy = {}
        for policy in POLICIES:
            own_ids, own_values, fit_seconds = [], [], 0.0
            policy_rows = [item for item in journal if item["policy"] == policy]
            check(len(policy_rows) == 50 and len({item["material_id"] for item in policy_rows}) == 50 and
                  set(item["material_id"] for item in policy_rows) <= set(split["pool"]), f"50 unique own-policy pool queries: {seed}/{policy}")
            reported = next(item for item in summary["policies"] if item["policy"] == policy)
            for round_index in range(1,6):
                directory = f"{base}/{policy}/round_{round_index:02d}"
                decision, reveal, complete, fit = [read(directory+"/"+name+".json") for name in ["decision","reveals","complete","fit_audit"]]
                prior_ids = split["train"]+own_ids
                check(decision["known_ids_sha256"] == canonical(prior_ids) and decision["model_training_ids_sha256"] == canonical(prior_ids) and
                      decision["oracle_labels_supplied_to_acquisition"] == 0 and len(decision["material_ids"]) == 10,
                      f"Pre-reveal decision uses only own previous labels: {seed}/{policy}/{round_index}")
                check(decision["committed_at_utc"] <= reveal["revealed_at_utc"] <= fit["started_at_utc"] <= fit["completed_at_utc"] <= complete["completed_at_utc"],
                      f"Decision/reveal/fit time order: {seed}/{policy}/{round_index}")
                check(reveal["material_ids"] == decision["material_ids"] and reveal["prior_decision_sha256"] == sha(directory+"/decision.json"),
                      f"Reveals bind committed IDs: {seed}/{policy}/{round_index}")
                round_rows = [item for item in policy_rows if int(item["round"]) == round_index]
                check([item["material_id"] for item in round_rows] == reveal["material_ids"] and
                      [float(item["label_eV_atom"]) for item in round_rows] == reveal["labels_eV_atom"], f"Revealed journal labels agree: {seed}/{policy}/{round_index}")
                own_ids.extend(reveal["material_ids"]); own_values.extend(reveal["labels_eV_atom"])
                check(fit["training_ids"] == split["train"]+own_ids and fit["training_ids_sha256"] == canonical(split["train"]+own_ids) and
                      fit["calibration_ids"] == split["calibration"] and not fit["normalization_refitted"], f"Fixed calibration and own-policy-only fit set: {seed}/{policy}/{round_index}")
                check(fit["calibration"]["rank_1_based"] == 361 and fit["calibration"]["floor_eV_atom"] == .01 and len(fit["members"]) == 5,
                      f"Frozen ensemble/calibration settings: {seed}/{policy}/{round_index}")
                for name,key in [("decision.json","decision_sha256"),("reveals.json","reveal_sha256"),("fit_audit.json","fit_audit_sha256")]:
                    check(sha(directory+"/"+name) == complete[key], f"Round evidence hash: {seed}/{policy}/{round_index}/{name}")
                check(sha(complete["model_path"]) == complete["model_sha256"], f"Adapted model hash: {seed}/{policy}/{round_index}")
                fit_seconds += fit["fit_calibration_seconds"]
                curve = reported["curve"][round_index-1]
                check(curve["queries"] == len(own_ids) and curve["near_stable_hits"] == sum(x <= .05 for x in own_values) and
                      curve["reference_hull_hits"] == sum(x <= 0 for x in own_values) and curve["chemical_system_coverage"] == len({systems[mid] for mid in own_ids}),
                      f"Historical hit/coverage curve independently recomputed: {seed}/{policy}/{round_index}")
            endpoint = {"near_stable_hits": sum(x <= .05 for x in own_values), "reference_hull_hits": sum(x <= 0 for x in own_values),
                        "precision_at_50": sum(x <= .05 for x in own_values)/50, "chemical_system_coverage_at_50": len({systems[mid] for mid in own_ids}),
                        "adapted_fit_calibration_seconds": fit_seconds}
            check(reported["queried_ids"] == own_ids and reported["queries"] == 50 and all(close(reported[k],endpoint[k]) for k in ["near_stable_hits","reference_hull_hits","precision_at_50"]),
                  f"Policy endpoint independently reproduced: {seed}/{policy}")
            for key,value in endpoint.items(): values_by_policy[policy][key].append(value)
            result_by_policy[policy] = endpoint
        differences.append(result_by_policy["full"]["near_stable_hits"]-result_by_policy["quality"]["near_stable_hits"])
    check(query_events == 1250, "All 1250 historical query events verified from revealed journals")
    for policy, metrics in values_by_policy.items():
        for key,values in metrics.items(): check_stats(aggregate["policy_endpoint_aggregates"][policy][key], values, f"Five-seed {policy}/{key}")
    check_stats(aggregate["full_minus_quality_near_stable_hits"], differences, "Paired full-minus-quality hit differences")
    paired = aggregate["full_minus_quality_near_stable_hits"]
    check(paired["wins"] == sum(x>0 for x in differences) and paired["ties"] == sum(x==0 for x in differences) and paired["losses"] == sum(x<0 for x in differences), "All paired wins/ties/losses retained")
    aggregate_audit = read("artifacts/phase4/replay/audit.json")
    check(aggregate_audit["status"] == "passed" and aggregate_audit["aggregate_summary_sha256"] == sha("artifacts/phase4/replay/aggregate_summary.json") and aggregate_audit["new_fits_queries_or_oracle_access_in_audit"] == 0,
          "Aggregate audit binds authoritative five-seed summary")
    return values_by_policy, differences


def audit_generation():
    base = "artifacts/phase4/generation"
    primary, audit = read(base+"/summary.json"), read(base+"/audit.json")
    check(audit["status"] == "passed" and audit["checks_passed"] == 1629 and audit["model_draws_in_audit"] == 0 and
          audit["summary_sha256"] == sha(base+"/summary.json"), "Primary generation audit: 1629 artifact checks, zero draws")
    check(primary["all_primary_actual_draws"] == 80 and primary["new_draws_phase4"] == primary["new_charged_attempts_phase4"] == 64 and
          primary["new_composition_primary_attempts"] == 48 and primary["control_primary_attempts"] == 32, "All frozen primary attempt denominators retained")
    check(len(primary["controls"]) == 4 and len(primary["new_compositions"]) == 6 and primary["new_composition_valid_count"] == 0 and
          primary["new_formulas_with_exact_valid_structure"] == 0 and primary["posthoc_cell_count_admissions"] == 0, "Zero exact-cell novel-formula survivors retained")
    for cohort in primary["cohorts"]:
        check(sha(cohort["summary_path"]) == cohort["summary_sha256"] and len(cohort["results"]) == 8, "Primary cohort summary/denominator: "+cohort["run_id"])
        check(sum(bool(item["audited_valid"]) for item in cohort["results"]) == cohort["valid_count"], "Primary validity total: "+cohort["run_id"])
        for item in cohort["results"]:
            for name,key in [("structure_json","structure_sha256"),("cif","cif_sha256")]:
                check(sha(item[name]) == item[key], "Preserved generated artifact: "+item[name])
            raw_name = item.get("raw_json",item.get("raw_path"))
            check(sha(raw_name) == item["raw_sha256"] and item["cif_roundtrip"] and item["raw_expansion_verified"], "Raw expansion and roundtrip audit commitment: "+item["candidate_id"])
    supplement = read(base+"/supplementary_mgo/summary.json")
    supp_audit = read(base+"/supplementary_mgo/audit.json")
    supp_plan = read(base+"/supplementary_mgo/run_plan.json")
    check(supp_audit["status"] == "passed" and supp_audit["checks_passed"] == 141 and supp_audit["model_draws_in_audit"] == 0 and
          supp_audit["summary_sha256"] == sha(base+"/supplementary_mgo/summary.json"), "Supplementary MgO audit: 141 checks, zero audit draws")
    check(supplement["new_actual_draws"] == supplement["charged_attempts"] == 8 and supplement["primary_denominators_unchanged"] and
          not supplement["more_topups_authorized"] and supp_plan["batch_index"] == 2 and supp_plan["batch_size"] == 4 and
          not supp_plan["primary_batches_resampled"], "Exactly one separate balanced eight-draw MgO topup at unused batch2")
    for item in supp_plan["frozen_primary_artifacts"]: check(sha(item["path"]) == item["sha256"], "Primary result immutable across supplementary sampling: "+item["path"])
    for arm in supplement["arms"]:
        check(arm["attempts"] == arm["charged_attempts"] == 4 and arm["primary_attempts"] == 8 and arm["combined_primary_plus_supplementary_attempts"] == 12,
              "Supplementary per-arm four-slot reservations: "+arm["arm"])
        check(sha(arm["summary_path"]) == arm["summary_sha256"], "Supplementary cohort summary hash: "+arm["arm"])
        for item in arm["results"]:
            for name,key in [("raw_json","raw_sha256"),("structure_json","structure_sha256"),("cif","cif_sha256")]: check(sha(item[name]) == item[key], "Supplementary artifact hash: "+item[name])
    shortlist = read("artifacts/phase4/selection/fresh_shortlist.json")
    check(shortlist["fresh_selector_sha256"] == FRESH_SHA and shortlist["research_protocol_sha256"] == PROTOCOL_SHA and shortlist["initial_geometry_only"] and
          not shortlist["adapted_or_other_seed_models_used"] and not shortlist["CHGNet_or_QE_energies_used"] and shortlist["additional_generation_or_relaxations_in_selection"] == 0,
          "Fresh selection uses unchanged initial-only selector without outcome labels")
    check(len(shortlist["formulas"]) == 6 and shortlist["selected_count"] == 0 and shortlist["selected_in_formula_and_pair_order"] == [] and
          all(not item["selected"] and not item["valid_unique_candidates"] and item["primary_attempts"] == 8 for item in shortlist["formulas"]), "Six empty formula pools; no posthoc admission")
    for item in shortlist["formulas"]: check(sha(item["source_summary"]) == item["source_summary_sha256"], "Fresh shortlist source hash: "+item["formula"])
    check(sha(shortlist["initial_features"]) == shortlist["initial_features_sha256"] and sha("research_acquisition.py") == shortlist["acquisition_source_sha256"], "Fresh shortlist feature/acquisition hashes")
    handoff = read("artifacts/phase4/selection/symmetry_relaxation_plan.json")
    check(handoff["source_primary_summary_sha256"] == sha(base+"/summary.json") and handoff["source_supplementary_summary_sha256"] == sha(base+"/supplementary_mgo/summary.json") and
          not handoff["CHGNet_or_DFT_energies_used_to_select"] and handoff["relaxation_jobs_executed_by_this_script"] == 0, "Symmetry selection frozen from correct pools before new relaxations")
    import numpy as np
    for ci, control in enumerate(handoff["controls"]):
        expected_scope = "supplementary_primary_plus_topup_pool" if ci == 0 else "primary_first8_per_arm"
        check(control["quota_per_arm"] == 1 and control["comparison_scope"] == expected_scope, "Balanced q1 symmetry quota with explicit sampling scope: "+control["control"])
        for ai, arm in enumerate(control["arms"]):
            if ci == 0: pool = next(item for item in supplement["arms"] if item["arm"] == arm["arm"])["combined_valid_unique_representatives"]
            else: pool = next(item for item in primary["controls"] if item["control"] == control["control"] and item["arm"] == arm["arm"])["valid_unique_representatives"]
            ids = sorted(item["candidate_id"] for item in pool)
            sequence = [20261022,ci,ai,404]
            selected_indices = np.random.default_rng(np.random.SeedSequence(sequence)).choice(len(ids), size=control["quota_per_arm"], replace=False)
            expected = [ids[int(index)] for index in selected_indices]
            check(arm["seed_sequence"] == sequence and arm["pool_ids"] == ids and [item["candidate_id"] for item in arm["selected"]] == expected,
                  "Seeded uniform symmetry selection independently reproduced: "+control["control"]+"/"+arm["arm"])
            for item in arm["selected"]: check(sha(item["source_structure"]) == item["source_structure_sha256"], "Selected symmetry initial source hash: "+item["candidate_id"])
    check(handoff["selected_structures"] == 4 and handoff["planned_new_symmetry_launches_if_exact_cache_reused"] == 3,
          "Four experimental selections need three new jobs if one identical calculation is reused")
    cache = handoff["cache_candidate"]
    check(sha(cache["result_path"]) == cache["result_sha256"] and cache["initial_source_matches"] and cache["converged"] and cache["new_charge_if_identical_reused"] == 0,
          "One explicit conditional cached MgO result; final Phase5 settings check remains required")
    generation_protocol = read("artifacts/phase2/compositions/generation_protocol.json")
    prototypes = read("artifacts/phase2/compositions/prototype_plan.json")
    check(len(prototypes["plans"]) == prototypes["maximum_relaxation_attempts"] == 4 and
          all(item["eligible_for_attempt"] for item in prototypes["plans"]), "Four predeclared prototype candidates remain the fixed Phase5 subset")
    for item in generation_protocol["deterministic_prototype_candidates"]:
        check(sha(item["cif"]) == item["cif_sha256"] and item["structure_budget_charge"] == 1, "Prototype prepared once with preserved initial geometry: "+item["candidate_id"])
    references = read("artifacts/phase2/controls/same_composition_reference_plan.json")
    eligible_references = [item for item in references["references"] if item["eligible_at_most_20_atoms"]]
    check(references["maximum_attempts"] == 4 and len(references["references"]) == 4 and len(eligible_references) == 3,
          "Reference allocation4 contains three eligible references and one excluded oversize brookite slot")
    for item in eligible_references: sha(item["reference_cif"])
    return primary, supplement, handoff


def audit_qe(starts, finishes, budget):
    from phase3_qe_parser import parse_job
    queue = read("artifacts/phase4/qe/queue_plan.json")
    summary, lane_audit = read("artifacts/phase4/qe/summary.json"), read("artifacts/phase4/qe/audit.json")
    check(lane_audit["status"] == "passed" and lane_audit["checks_passed"] == 83 and summary["all_jobs_finished"] and
          summary["phase4_QE_job_count"] == 3 and summary["CaO_final_geometry_numerical_checks_pass"], "All three CaO-only QE jobs complete; 83 lane checks passed")
    jobs = {}
    for item in summary["jobs"]:
        check(sha(item["path"]) == item["result_sha256"], "QE result inventory hash: "+item["job_id"])
        record = read(item["path"]); directory = path(item["path"]).parent; prov = record["provenance"]; settings = prov["settings"]
        check(sha(directory/"pw.in") == record["input_sha256"] == prov["input_sha256"] and sha(directory/"pw.out") == record["output_sha256"] and
              sha(directory/"settings.json") == prov["settings_sha256"], "QE input/output/settings hashes: "+record["job_id"])
        check(sha(prov["source_geometry"]) == prov["source_geometry_sha256"] and sha(prov["executable"]) == prov["executable_sha256"] and
              prov["queue_plan_sha256"] == sha("artifacts/phase4/qe/queue_plan.json"), "QE source/executable/pre-dispatch queue hashes: "+record["job_id"])
        for element, filename in prov["pseudo_files"].items(): check(sha(directory/"pseudo"/filename) == prov["pseudo_hashes"][element], "QE pseudo hash: "+record["job_id"]+"/"+element)
        parsed = parse_job(directory, settings, return_code=record["return_code"], timed_out=record["timed_out"], write_geometry=False)
        for key in ["job_scf_accepted","job_stationary_at_this_setting","energy_eV_per_atom","max_force_vector_norm_eV_per_angstrom","max_absolute_residual_stress_component_kbar"]:
            check(parsed.get(key) == record["result"].get(key), "QE XML independently reparsed without geometry writes: "+record["job_id"]+"/"+key)
        sha(path(parsed["xml_path"]))
        check(starts[record["job_id"]]["reserved_utc"] <= record["started_at_utc"] and
              close(finishes[record["job_id"]]["wall_seconds"],record["elapsed_wall_seconds"]) and record["threads"]["OMP_NUM_THREADS"] == "4",
              "QE pre-dispatch reservation/whole-process time/four threads: "+record["job_id"])
        check(record["phase"] == 4 and record["category"] != "candidate" and record["job_id"] in queue["allowed_job_ids"], "QE stayed within CaO-only authorized queue: "+record["job_id"])
        jobs[record["job_id"]] = record
    check(len(jobs) == 3 and close(sum(j["elapsed_wall_seconds"] for j in jobs.values()),451.2890359000012) and
          close(summary["phase4_QE_wall_seconds"],451.2890359000012) and sum(j["elapsed_wall_seconds"] for j in jobs.values()) <= queue["additional_phase4_QE_wall_ceiling_seconds"] == 2700,
          "Phase4 QE total451.289s remains within local2700s cap")
    accepted = jobs[summary["accepted_CaO_job_id"]]; setting = accepted["provenance"]["settings"]
    check(accepted["result"]["job_stationary_at_this_setting"] and setting["ecutwfc_Ry"] == 90 and setting["ecutrho_Ry"] == 720 and
          setting["k_spacing_start_inv_angstrom"] == .35, "CaO final accepted90/720Ry,0.35 inverse-A geometry passes force/full-stress checks")
    for probe in summary["final_geometry_sensitivity_checks"]:
        job = jobs[probe["job_id"]]
        shift = abs(job["result"]["energy_eV_per_atom"]-accepted["result"]["energy_eV_per_atom"])
        check(job["result"]["job_scf_accepted"] and job["provenance"]["source_geometry_sha256"] == sha(accepted["result"]["final_geometry_json"]) and
              close(shift,probe["absolute_energy_shift_eV_per_atom"]) and shift <= .005 and probe["same_final_geometry"] and probe["within_5_meV_per_atom"], "CaO final-geometry sensitivity reproduced: "+job["job_id"])
    check(jobs["p4_cao_final_cut75"]["result"]["job_scf_accepted"] and not jobs["p4_cao_final_cut75"]["result"]["job_stationary_at_this_setting"],
          "75Ry fixed-geometry energy probe is SCF accepted but not falsely called stress-stationary")
    mgo = read("artifacts/phase3/qe/p3_ref_mgo_90_k035_cont1/result.json")
    mg_setting = mgo["provenance"]["settings"]
    check(all(setting[k] == mg_setting[k] for k in ["ecutwfc_Ry","ecutrho_Ry","k_spacing_start_inv_angstrom","input_dft","occupations","nspin"]) and
          accepted["provenance"]["pseudo_hashes"]["O"] == mgo["provenance"]["pseudo_hashes"]["O"], "CaO/MgO anchors have compatible settings and shared O pseudopotential")
    weighted_products = accepted["result"]["energy_eV_per_atom"]/3+2*mgo["result"]["energy_eV_per_atom"]/3
    check(close(summary["CaO_energy_eV_per_atom"],accepted["result"]["energy_eV_per_atom"]) and close(summary["known_MgO_reference_energy_eV_per_atom"],mgo["result"]["energy_eV_per_atom"]), "Compatible anchor energies independently reproduced")
    check(not summary["fresh_CaMg2O3_candidate_submitted"] and not summary["full_frozen_inventory_hull_established"] and summary["new_stable_materials"] == 0,
          "Two compatible oxide anchors establish no candidate reaction energy or complete hull")
    legacy = jsonl("artifacts/phase1/qe/qe_jobs.jsonl")
    check(close(sum(j["elapsed_wall_seconds"] for j in legacy),budget["qe"]["charged_wall_seconds"]), "Legacy and canonical cumulative QE times reconcile")
    chronological = sorted(legacy,key=lambda j:j["started_at_utc"])
    check(all(a["finished_at_utc"] <= b["started_at_utc"] for a,b in zip(chronological,chronological[1:])), "All QE jobs serialized under one-job resource limit")
    return weighted_products


def main():
    event_hash_before = sha("artifacts/runtime_budget_events.jsonl")
    budget = read("artifacts/budget_ledger.json")
    if path("artifacts/runtime_budget.lock").exists(): raise RuntimeError("Budget owner is active; refusing Phase4 finalization")
    events = jsonl("artifacts/runtime_budget_events.jsonl")
    reserved = [item for item in events if item["event"] == "reserved"]
    ended = [item for item in events if item["event"] == "finished"]
    starts, finishes = ({item["reservation_id"]:item for item in rows} for rows in [reserved,ended])
    if set(starts) != set(finishes) or any(budget[k]["active_reservations"] for k in ["generation","chgnet","qe"]):
        raise RuntimeError("Live or unresolved numerical reservations; refusing finalization")
    if budget["phase"] != 4 or any(int(item.get("phase",3)) > 4 for item in events):
        raise RuntimeError("Further-phase numerical work exists; preserve historical Phase4 closure")
    existing_manifest = read("artifacts/phase4/manifest.json") if (OUT/"manifest.json").exists() else None
    if existing_manifest and existing_manifest["phase4_end_budget"]["runtime_events_sha256"] != event_hash_before:
        raise RuntimeError("Numerical ledger changed after frozen Phase4 closure; refusing historical overwrite")
    check(len(starts) == len(reserved) and len(finishes) == len(ended), "Every unique atomic reservation has one terminal event")
    check(sha("config/phase2_protocol.json") == PROTOCOL_SHA and read("artifacts/phase3/readiness.json")["ready_for_phase4"], "Phase3 handoff complete; frozen scientific protocol unchanged")
    protocol = read("config/phase2_protocol.json")
    check(sha("research_acquisition.py") == protocol["acquisition_implementation_sha256"], "Frozen acquisition implementation unchanged")
    for item in read("artifacts/phase2/protocol/manifest.json").values():
        if isinstance(item,dict) and {"path","sha256"} <= item.keys(): check(sha(item["path"]) == item["sha256"], "Phase2 source commitment: "+item["path"])
    check(sha("artifacts/phase3/models/fresh_selector_seed_20261022.joblib") == FRESH_SHA, "Original pre-query fresh model unchanged")
    preflight = read("artifacts/phase4/preflight/budget_ledger.json")
    check(preflight["generation"]["charged_attempts"] == 24 and preflight["chgnet"]["charged_attempts"] == 9 and
          close(preflight["qe"]["charged_wall_seconds"],1207.1928419000032), "Historical Phase4 start:24structure/9CHG/1207.193QEseconds")
    execution = read("artifacts/phase4/execution_plan.json")
    check(execution["baseline"]["sha256"] == sha(execution["baseline"]["path"]) and not execution["hypothesis_or_acquisition_retuning"], "Pre-dispatch Phase4 plan binds the original baseline")
    aggregate = read("artifacts/phase4/replay/aggregate_summary.json")
    values, differences = audit_replay(aggregate)
    primary, supplementary, handoff = audit_generation()
    check(budget["phase"] == max([3]+[int(item.get("phase",3)) for item in events]), "Budget header records maximum executed phase")
    check(budget["generation"]["charged_attempts"] == 96 and budget["generation"]["remaining_attempts"] == 32 and
          budget["generation"]["CrystalFormer_sample_attempts"] == 92 and budget["generation"]["deterministic_prototype_attempts"] == 4, "96global structure charges =92CFslots+4prototypes;32remain")
    phase4_generation = [item for item in reserved if item["lane"] == "generation" and item["phase"] == 4]
    check(sum(item["attempts"] for item in phase4_generation) == 72 and len(phase4_generation) == 10 and all(item["category"] == "crystalformer" for item in phase4_generation), "Phase4 charges exactly64primary+8supplementary across10launches")
    check(primary["all_primary_actual_draws"]+supplementary["new_actual_draws"] == 88 and
          budget["generation"]["CrystalFormer_sample_attempts"]-88 == 4, "88actual CF draws plus four retained Phase3 engineering charges")
    check(budget["chgnet"]["charged_attempts"] == 9 and budget["chgnet"]["remaining_attempts"] == 31 and
          not any(item["lane"] == "chgnet" and item["phase"] == 4 for item in reserved), "No Phase4 CHGNet launches; nine prior charges and31remaining")
    check(budget["generation"]["ceiling_attempts"] == 128 and budget["chgnet"]["ceiling_attempts"] == 40 and
          budget["chgnet"]["ceiling_seconds"] == 14400 and budget["qe"]["ceiling_seconds"] == 21600 and
          budget["chgnet"]["remaining_seconds"] >= 0 and budget["qe"]["remaining_seconds"] >= 0, "All original attempt/time ceilings unchanged and binding")
    check(close(budget["qe"]["charged_wall_seconds"],1658.4818778000044) and close(budget["qe"]["remaining_seconds"],19941.518122199996), "QE cumulative1658.482seconds;19941.518seconds remain")
    baseline = read("artifacts/phase3/budget_baseline.json")["budget"]
    check(baseline["generation"]["charged_attempts"]+sum(item["attempts"] for item in reserved if item["lane"] == "generation") == 96 and
          baseline["chgnet"]["charged_attempts"]+sum(item["attempts"] for item in reserved if item["lane"] == "chgnet") == 9,
          "Attempt totals independently reconstructed from baseline and all reservations")
    for lane in ["chgnet","qe"]:
        total = baseline[lane]["charged_wall_seconds"]+sum(finishes[item["reservation_id"]]["wall_seconds"] for item in reserved if item["lane"] == lane)
        check(close(total,budget[lane]["charged_wall_seconds"]), "Whole-process cumulative walltime independently reconstructed: "+lane)
    weighted_products = audit_qe(starts,finishes,budget)
    gate = read("artifacts/phase4/gates/composition_stretch.json")
    # Gate records may add explanatory fields; reject any eight-formula enablement.
    check(not any(gate.get(key,False) for key in ["approved","enabled","stretch_enabled","execute_stretch"]), "No composition stretch enabled after inadequate primary yield")
    check(gate["decision"] == "disabled" and gate["additional_formulas_generated"] == gate["new_structure_draws_in_gate_check"] == 0 and
          gate["primary_failures_retained"] and gate["symmetry_supplement_does_not_replace_primary_gate"] and
          gate["unchanged_global_generation_ceiling"] == 128, "Stretch gate preserves primary failures without extra draws or hidden cap changes")
    report = path("reports/phase4_report.md"); sha(report); text = report.read_text(encoding="utf-8")
    check(not re.search(r"\b(?:PLACEHOLDER|TBD|TODO)\b",text), "Phase4 report contains final results without placeholders")
    planned_outputs = {(OUT/name).resolve() for name in ["audit.json","readiness.json","manifest.json"]}
    deferred_links = []
    for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)",text):
        target = unquote(link.strip().strip("<>").split("#",1)[0])
        if not target or re.match(r"(?:https?://|mailto:)",target): continue
        resolved = (report.parent/target).resolve()
        if resolved in planned_outputs and not resolved.exists(): deferred_links.append(resolved)
        check(resolved.exists() or resolved in planned_outputs, "Report local link resolves or names this finalizer's explicitly planned output: "+target)
    for name in ["README.md","one_day_research_proposal.md","reports/phase4_report.md","scripts/phase4_finalize.py",
                 "research_acquisition.py","research_models.py","research_features.py","research_budget.py",
                 "artifacts/phase4/figures/primary_generation.png","artifacts/phase4/replay_figures/five_seed_acquisition.png"]:
        check(path(name).is_file(), "Reviewable Phase4 deliverable exists: "+name); sha(name)
    for script in sorted((ROOT/"scripts").glob("phase4*.py")): sha(script)
    for source in aggregate["sources"]: check(sha(source["path"]) == source["sha256"], "Aggregate artifact inventory: "+source["path"])
    check(sha("artifacts/runtime_budget_events.jsonl") == event_hash_before and not path("artifacts/runtime_budget.lock").exists(), "No numerical job or ledger mutation occurred during final audit")
    passed = all(item["passed"] for item in CHECKS); completed = datetime.now(timezone.utc).isoformat()
    save("audit.json", {"phase":4,"audited_utc":completed,"status":"passed" if passed else "failed","check_count":len(CHECKS),"checks":CHECKS,
        "failed_checks":[item for item in CHECKS if not item["passed"]],"audit_source_sha256":sha(Path(__file__)),
        "oracle_label_file_accesses":0,"new_fits_draws_relaxations_or_QE_jobs":0,"canonical_budget_writes":0,
        "verified_replay_seeds":SEEDS,"policy_query_events":1250,"new_phase4_policy_query_events":1000,
        "actual_primary_CF_draws":80,"supplementary_CF_draws":8,"new_phase4_CF_draws":72,"new_QE_jobs_verified":3,
        "weighted_CaO_plus_2MgO_product_energy_eV_per_atom":weighted_products,
        "weighted_product_scope":"Compatible anchor product only; no fresh CaMg2O3 candidate energy, decomposition energy or complete hull is established."})
    readiness = {"phase":4,"status":"complete" if passed else "audit_failed","completed_utc":completed,"ready_for_phase5":passed,
        "protocol_sha256":PROTOCOL_SHA,"original_fresh_selector_sha256":FRESH_SHA,"completed_paired_seeds":SEEDS,
        "retrospective_policy_query_events":1250,"phase4_new_policy_query_events":1000,
        "primary_exact_cell_generated_new_formula_survivors":0,"diagnostic_reduced_formula_geometry_and_atom_cap_survivors":12,
        "actual_CrystalFormer_draws_total":88,"phase4_actual_and_charged_CF_draws":72,
        "primary_symmetry_generation_evidence_complete":True,"symmetry_architecture_causal_benefit_established":False,
        "fresh_shortlist":"artifacts/phase4/selection/fresh_shortlist.json","fresh_shortlist_count":0,
        "symmetry_selection":"artifacts/phase4/selection/symmetry_relaxation_plan.json","balanced_symmetry_quotas":{"MgO":1,"TiO2":1},
        "phase5_symmetry_new_CHGNet_jobs_if_cache_verified":3,"phase5_conditional_cached_symmetry_reuse":1,
        "phase5_predeclared_prototypes":4,"phase5_same_composition_reference_allocation":4,
        "phase5_eligible_predeclared_same_composition_references":3,"phase5_excluded_reference_slot":"Brookite requires at least24 atoms; no eligible saved CIF, no outcome-based replacement",
        "remaining_generation_slots":32,"remaining_CHGNet_launches":31,"remaining_CHGNet_seconds":budget["chgnet"]["remaining_seconds"],
        "remaining_QE_seconds":budget["qe"]["remaining_seconds"],"numerical_stop_utc":budget["numerical_stop_utc"],
        "new_stable_material_established":False,"full_compatible_competition_hull_established":False,
        "phase5_tasks":["Implement budgeted Phase5 execution consuming the frozen symmetry selection; verify exact CHG settings before one cached reuse",
            "Run only the three selected new symmetry relaxations, four predeclared prototypes and three eligible same-composition references within original category/global caps; leave the oversize brookite reference slot unused",
            "Retain the empty transformer shortlist; do not admit larger cells or invent replacements after outcomes",
            "Continue permitted reference/numerical work only when useful; compatible anchors alone do not establish a full hull"],
        "review_commands":["Get-Content artifacts/phase4/selection/symmetry_relaxation_plan.json",
            "Get-Content artifacts/phase4/selection/fresh_shortlist.json",
            ".envs/analysis/Scripts/python.exe scripts/phase4_finalize.py"],
        "review_command_scope":"Inspection and evidence audit only. A Phase5 numerical runner has not yet been implemented; no executable command is invented.",
        "phase4_end_budget_snapshot":"artifacts/phase4/manifest.json#phase4_end_budget"}
    save("readiness.json",readiness)
    frozen_budget = existing_manifest["phase4_end_budget"] if existing_manifest else {
        "frozen_utc":completed,"budget_ledger":budget,"budget_ledger_sha256":sha("artifacts/budget_ledger.json"),
        "runtime_events_sha256":event_hash_before,"runtime_event_count":len(events),
        "scope":"Historical Phase4 close. Future Phase5 ledgers may advance; this snapshot remains unchanged."}
    sha("artifacts/phase4/audit.json");sha("artifacts/phase4/readiness.json")
    save("manifest.json", {"phase":4,"created_utc":completed,"status":"complete" if passed else "audit_failed",
        "phase4_end_budget":frozen_budget,"files":[INVENTORY[key] for key in sorted(INVENTORY) if key != "artifacts/phase4/manifest.json"],
        "scope":"Hashes of sources, frozen commitments, per-round fit/model/reveal evidence, generation/QE artifacts, gates, handoffs and final documents read by this audit. Oracle labels are excluded."})
    if not all(target.is_file() for target in deferred_links):
        raise RuntimeError("A planned finalizer output link did not materialize")
    print(json.dumps({"phase":4,"status":"passed" if passed else "failed","checks":len(CHECKS),"failed":sum(not item["passed"] for item in CHECKS),
        "ready_for_phase5":passed,"remaining_generation_slots":32,"remaining_CHGNet_launches":31,"remaining_QE_seconds":budget["qe"]["remaining_seconds"]}))
    return 0 if passed else 1


if __name__ == "__main__": raise SystemExit(main())
