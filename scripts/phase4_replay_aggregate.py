"""Aggregate already completed frozen replay artifacts; never fit or read oracle labels."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache" / "matplotlib")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from research_acquisition import POLICIES

SEEDS = tuple(range(20261022, 20261027))
OUT = ROOT / "artifacts/phase4/replay"
FIGURES = ROOT / "artifacts/phase4/replay_figures"
NAMES = {"random": "Random", "quality": "Predicted quality", "quality_diversity": "Quality + diversity",
         "uncertainty": "Uncertainty", "full": "Full uncertainty + diversity"}
COLORS = {"random": "#777777", "quality": "#0072B2", "quality_diversity": "#009E73",
          "uncertainty": "#E69F00", "full": "#CC79A7"}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def describe(values):
    values = np.asarray(values, dtype=float)
    return {"values": values.tolist(), "n": len(values), "mean": float(values.mean()),
            "sample_std": float(values.std(ddof=1)), "min": float(values.min()), "max": float(values.max())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    records, curves, evaluations, journals, seed_records, sources = [], [], [], [], [], []
    completed = []
    for seed in SEEDS:
        phase = 3 if seed == SEEDS[0] else 4
        directory = ROOT / f"artifacts/phase{phase}/replay/seed_{seed}"
        summary = read(directory / "summary.json")
        audit = read(OUT / f"audits/seed_{seed}.json")
        assert summary["status"] == "completed" and audit["status"] == "passed"
        assert summary["paired_seed"] == seed and summary["total_policy_queries"] == 250
        assert audit["decisions_replayed_from_pre_reveal_predictions"] == 25
        assert audit["recomputed_bootstrap_plans"] == 125
        assert audit["original_fresh_snapshot_unchanged"]
        assert not summary["evaluator_metric_feedback_to_decisions"]
        completed.append(summary["completed_at_utc"])
        for row in summary["policies"]:
            policy_fit_seconds = sum(read(directory / row["policy"] / f"round_{round_index:02d}" / "fit_audit.json")["fit_calibration_seconds"]
                                     for round_index in range(1, 6))
            records.append({"seed": seed, "policy": row["policy"], "queries": row["queries"],
                            "near_stable_hits": row["near_stable_hits"], "precision_at_50": row["precision_at_50"],
                            "reference_hull_hits": row["reference_hull_hits"],
                            "chemical_system_coverage_at_50": row["curve"][-1]["chemical_system_coverage"],
                            "adapted_fit_calibration_seconds": policy_fit_seconds})
            for point in row["curve"]:
                curves.append({"seed": seed, "policy": row["policy"], **point})
        evaluator = read(directory / "evaluation_summary.json")
        assert evaluator["policy_decisions_finished_before_label_access"]
        for row in evaluator["evaluated_predictions"]:
            parts = Path(row["prediction_path"]).parts
            initial = parts[-1] == "initial_eval_predictions.npz"
            policy, queries = ("initial_shared", 0) if initial else (parts[-3], int(parts[-2].split("_")[-1])*10)
            evaluations.append({"seed": seed, "policy": policy, "queries": queries,
                                **{key: value for key, value in row.items() if key not in ("prediction_path", "evaluated_at_utc")}})
        with (directory / "query_journal.csv").open(encoding="utf-8", newline="") as stream:
            journal = list(csv.DictReader(stream))
        assert len(journal) == 250
        journals.extend(journal)
        split = read(ROOT / f"artifacts/phase2/splits/seed_{seed}.json")["material_ids"]
        initial_metrics = next(row for row in evaluations if row["seed"] == seed and row["policy"] == "initial_shared")
        policy_map = {row["policy"]: row for row in records if row["seed"] == seed}
        fit_seconds = audit["total_initial_and_adapted_fit_calibration_seconds"]
        if phase == 3:
            log_path = ROOT / "artifacts/phase3/model_logs/run.log"
            text = log_path.read_text(encoding="utf-8")
            measured_elapsed = sum(float(value) for pair in re.findall(r"initial-only complete seconds=([0-9.]+)|full run complete elapsed_seconds=([0-9.]+)", text)
                                   for value in pair if value)
            elapsed_scope = "Sum of original logged initial-only and resume invocations; excludes imports and user waiting gap"
            elapsed_source = str(log_path.relative_to(ROOT))
        else:
            execution_cost_path = directory / "execution_cost.json"
            measured_elapsed = read(execution_cost_path)["wall_seconds_in_this_invocation"]
            elapsed_scope = "Original single replay invocation; excludes imports before timer starts"
            elapsed_source = str(execution_cost_path.relative_to(ROOT))
        seed_records.append({"seed": seed, "phase_executed": phase, "initial_training_rows": len(split["train"]),
                             "fixed_calibration_rows": len(split["calibration"]), "fixed_evaluation_rows": len(split["unused"]),
                             "pool_rows": len(split["pool"]), "policy_query_events": 250,
                             "initial_and_adapted_fit_calibration_seconds": fit_seconds,
                             "measured_invocation_elapsed_seconds": measured_elapsed,
                             "measured_invocation_elapsed_scope": elapsed_scope,
                             "elapsed_source_path": elapsed_source,
                             "full_minus_quality_near_stable_hits": policy_map["full"]["near_stable_hits"]-policy_map["quality"]["near_stable_hits"],
                             "initial_evaluation_MAE_eV_atom": initial_metrics["MAE_eV_atom"],
                             "initial_evaluation_90_interval_coverage": initial_metrics["interval_90_empirical_coverage"],
                             "source_summary_path": str((directory / "summary.json").relative_to(ROOT)),
                             "source_summary_sha256": sha(directory / "summary.json"),
                             "query_journal_path": str((directory / "query_journal.csv").relative_to(ROOT)),
                             "query_journal_sha256": sha(directory / "query_journal.csv"),
                             "audit_path": str((OUT / f"audits/seed_{seed}.json").relative_to(ROOT)),
                             "audit_sha256": sha(OUT / f"audits/seed_{seed}.json")})
        for path in (directory / "summary.json", directory / "evaluation_summary.json", directory / "query_journal.csv", OUT / f"audits/seed_{seed}.json"):
            sources.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path), "size_bytes": path.stat().st_size})
    assert len(records) == 25 and len(curves) == 125 and len(evaluations) == 130 and len(journals) == 1250
    assert [row["near_stable_hits"] for row in records if row["seed"] == 20261022 and row["policy"] in ("quality", "full")] == [43, 34]
    write_csv(OUT / "per_seed_policy_metrics.csv", records)
    write_csv(OUT / "learning_curves.csv", curves)
    write_csv(OUT / "per_seed_evaluation_metrics.csv", evaluations)
    write_csv(OUT / "query_journal_all_seeds.csv", journals)
    write_csv(OUT / "per_seed_cost_and_initial_evaluation.csv", seed_records)
    policy_aggregates = {}
    for policy in POLICIES:
        rows = [row for row in records if row["policy"] == policy]
        policy_aggregates[policy] = {key: describe([row[key] for row in rows]) for key in (
            "near_stable_hits", "precision_at_50", "reference_hull_hits", "chemical_system_coverage_at_50", "adapted_fit_calibration_seconds")}
    differences = []
    for seed in SEEDS:
        rows = {row["policy"]: row for row in records if row["seed"] == seed}
        differences.append({"seed": seed, "full_near_stable_hits": rows["full"]["near_stable_hits"],
                            "quality_near_stable_hits": rows["quality"]["near_stable_hits"],
                            "full_minus_quality_near_stable_hits": rows["full"]["near_stable_hits"]-rows["quality"]["near_stable_hits"],
                            "full_minus_quality_reference_hull_hits": rows["full"]["reference_hull_hits"]-rows["quality"]["reference_hull_hits"],
                            "full_minus_quality_diversity_near_stable_hits": rows["full"]["near_stable_hits"]-rows["quality_diversity"]["near_stable_hits"]})
    write_csv(OUT / "paired_differences.csv", differences)
    delta = [row["full_minus_quality_near_stable_hits"] for row in differences]
    final_evaluations = {}
    for policy in ("initial_shared", *POLICIES):
        rows = [row for row in evaluations if row["policy"] == policy and row["queries"] == (0 if policy == "initial_shared" else 50)]
        final_evaluations[policy] = {key: describe([row[key] for row in rows]) for key in (
            "MAE_eV_atom", "RMSE_eV_atom", "Spearman_disagreement_absolute_error",
            "interval_90_empirical_coverage", "mean_interval_width_eV_atom")}
    fit_seconds = sum(row["initial_and_adapted_fit_calibration_seconds"] for row in seed_records)
    summary = {
        "status": "completed", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": list(SEEDS), "n_paired_seeds": 5, "policies": list(POLICIES),
        "source_phase3_seed_reused_without_refit_or_requery": 20261022,
        "phase4_new_seeds": list(SEEDS[1:]), "per_seed": seed_records,
        "policy_endpoint_aggregates": policy_aggregates, "paired_differences": differences,
        "full_minus_quality_near_stable_hits": {**describe(delta), "wins": sum(x > 0 for x in delta),
                                                "ties": sum(x == 0 for x in delta), "losses": sum(x < 0 for x in delta)},
        "evaluation_endpoint_aggregates": final_evaluations,
        "policy_query_events": 1250, "phase4_new_policy_query_events": 1000,
        "query_events_per_policy_across_all_seeds": 250,
        "distinct_pool_ids_queried_across_all_seeds_and_policies": len({row["material_id"] for row in journals}),
        "shared_initial_label_count_per_seed": 2400,
        "total_initial_and_adapted_model_snapshots": 130, "phase4_new_model_snapshots": 104,
        "ensemble_members_per_model": 5, "trees_per_member": 128,
        "total_initial_and_adapted_fit_calibration_seconds": fit_seconds,
        "phase4_new_fit_calibration_seconds": sum(row["initial_and_adapted_fit_calibration_seconds"] for row in seed_records[1:]),
        "sum_measured_invocation_elapsed_seconds": sum(row["measured_invocation_elapsed_seconds"] for row in seed_records),
        "phase4_new_sum_measured_invocation_elapsed_seconds": sum(row["measured_invocation_elapsed_seconds"] for row in seed_records[1:]),
        "cost_scope": "Measured wall durations of replay invocations and fitting, not CPU seconds or new DFT evaluations; excludes Python imports before replay timers and artifact-only audits",
        "estimator_threads": 2, "all_decisions_replayed": 125,
        "all_adapted_bootstrap_plans_recomputed": 625, "all_initial_bootstrap_plans_recomputed": 25,
        "all_calibrations_recomputed": 130,
        "original_fresh_selector_sha256": read(ROOT / "artifacts/phase3/models/fresh_selector_seed_20261022.manifest.json")["sha256"],
        "hyperparameters_or_coefficients_changed_after_outcomes": False,
        "metric_scope": "Retrospective WBM signed historical hull-distance labels, not fresh DFT discoveries",
        "small_sample_scope": "Five paired split seeds from one overlapping dataset. Mean and sample SD are descriptive; seeds are not independent datasets. No significance or arbitrary-OOD coverage claim.",
        "evaluation_scope": "3418 untouched rows per seed; shared across its five policies, never supplied to that seed learner. Other seed partitions may overlap; no cross-seed model or queried-label sharing.",
        "no_best_seed_or_adapted_model_used_for_fresh_selection": True,
        "oracle_file_read_by_aggregate": False,
        "sources": sources,
        "source_hashes": {str(path.relative_to(ROOT)): sha(path) for path in (
            ROOT / "scripts/phase4_replay.py", ROOT / "scripts/phase4_replay_audit.py", Path(__file__),
            ROOT / "research_models.py", ROOT / "research_acquisition.py", ROOT / "config/phase2_protocol.json")},
    }
    write(OUT / "aggregate_summary.json", summary)
    write(OUT / "audit.json", {
        "status": "passed", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": list(SEEDS), "n_paired_seeds": 5,
        "new_policy_queries": 1000, "total_policy_queries": 1250,
        "unique_queries_per_policy_per_seed": 50,
        "decisions_replayed_from_pre_reveal_predictions": 125,
        "adapted_bootstrap_plans_recomputed": 625,
        "initial_bootstrap_plans_recomputed": 25,
        "calibrations_recomputed": 130, "verified_model_snapshots": 130,
        "all_training_ids_initial_plus_only_own_policy_queries": True,
        "all_calibration_ids_fixed": True, "all_diversity_normalizers_frozen_initial_only": True,
        "all_decisions_serialized_before_reveals": True,
        "all_evaluator_labels_read_after_all_policy_queries_complete_within_seed": True,
        "all_models_and_decision_reveal_fit_hashes_valid": True,
        "phase3_sources_reused_read_only": True,
        "original_fresh_selector_unchanged": True,
        "per_seed_audits": [{"seed": row["seed"], "path": row["audit_path"], "sha256": row["audit_sha256"]}
                            for row in seed_records],
        "aggregate_summary_path": str((OUT / "aggregate_summary.json").relative_to(ROOT)),
        "aggregate_summary_sha256": sha(OUT / "aggregate_summary.json"),
        "aggregate_source_sha256": sha(Path(__file__)),
        "oracle_file_read_by_aggregate_or_auditor": False,
        "new_fits_queries_or_oracle_access_in_audit": 0,
        "floating_reproduction_tolerance_rtol_and_atol": 1e-12,
    })
    with plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "font.family": "DejaVu Sans", "pdf.fonttype": 42}):
        figure, axes = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
        x = np.asarray([0, 10, 20, 30, 40, 50])
        for policy in POLICIES:
            for axis, key in zip(axes, ("near_stable_hits", "reference_hull_hits")):
                matrix = np.asarray([[0]+[row[key] for row in curves if row["seed"] == seed and row["policy"] == policy] for seed in SEEDS])
                mean, std = matrix.mean(axis=0), matrix.std(axis=0, ddof=1)
                axis.plot(x, mean, marker="o", markersize=3, color=COLORS[policy], label=NAMES[policy],
                          linewidth=2 if policy == "full" else 1.6, linestyle="--" if policy == "quality_diversity" else "-")
                axis.fill_between(x, np.maximum(0, mean-std), np.minimum(x, mean+std), color=COLORS[policy], alpha=.08)
                axis.set(xlim=(0, 50), ylim=(0, 50), xlabel="Historical label queries per policy", ylabel="Cumulative hits")
                axis.grid(alpha=.18)
        axes[0].set_title("Near-stable: signed hull distance ≤ 0.05 eV/atom")
        axes[1].set_title("On/below historical reference hull: ≤ 0")
        axes[0].legend(frameon=False, fontsize=8, loc="upper left")
        figure.suptitle("Five paired chemical-system splits: mean ± sample SD (descriptive)", fontsize=12)
        for extension in ("png", "pdf"):
            figure.savefig(FIGURES / f"five_seed_acquisition.{extension}", dpi=200)
        plt.close(figure)
        figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
        for i, (seed, difference) in enumerate(zip(SEEDS, delta, strict=True)):
            axes[0].bar(i, difference, color=COLORS["full"] if difference >= 0 else COLORS["quality"])
        axes[0].axhline(0, color="#444444", linewidth=.8)
        axes[0].set_xticks(range(5), [str(seed) for seed in SEEDS], rotation=30, ha="right")
        axes[0].set(ylabel="Full − quality near-stable hits at 50 queries", title="Paired differences for every frozen seed")
        for policy in POLICIES:
            matrix = []
            for seed in SEEDS:
                initial = next(row for row in evaluations if row["seed"] == seed and row["policy"] == "initial_shared")
                matrix.append([initial["interval_90_empirical_coverage"]]+[row["interval_90_empirical_coverage"] for row in evaluations if row["seed"] == seed and row["policy"] == policy])
            axes[1].plot(x, np.mean(matrix, axis=0), color=COLORS[policy], label=NAMES[policy], marker="o", markersize=3,
                         linestyle="--" if policy == "quality_diversity" else "-")
        axes[1].axhline(.90, color="#444444", linestyle=":", linewidth=1, label="Nominal 90%")
        axes[1].set(xlabel="Historical label queries per policy", ylabel="Mean empirical interval coverage", ylim=(.7, 1),
                    title="Fixed untouched evaluation rows within each seed")
        axes[1].legend(frameon=False, fontsize=7, loc="lower left")
        for axis in axes:
            axis.grid(axis="y", alpha=.18)
        for extension in ("png", "pdf"):
            figure.savefig(FIGURES / f"paired_differences_and_calibration.{extension}", dpi=200)
        plt.close(figure)
    write(OUT / "aggregate_artifact_inventory.json", {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path), "size_bytes": path.stat().st_size}
                  for path in sorted([*OUT.glob("*.csv"), OUT / "aggregate_summary.json", OUT / "audit.json", *FIGURES.glob("*")])],
    })
    print(json.dumps({"status": "completed", "seeds": list(SEEDS), "endpoint_means": {
        policy: data["near_stable_hits"]["mean"] for policy, data in policy_aggregates.items()},
        "full_minus_quality": summary["full_minus_quality_near_stable_hits"],
        "fit_calibration_seconds": fit_seconds, "summary": str((OUT / "aggregate_summary.json").relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
