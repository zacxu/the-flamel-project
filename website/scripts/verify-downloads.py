"""Check actual browser-downloaded W3 CSVs against frozen source records."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import statistics
from datetime import datetime, timezone

W = Path(__file__).resolve().parents[1]
ROOT = W.parent
checks = []


def check(value, name):
    checks.append({"check": name, "passed": bool(value)})
    if not value:
        raise ValueError(name)


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def close(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-13, abs_tol=1e-14)


baseline = json.loads((W / "reports/W3_BASELINE.json").read_text())
source_names = ["artifacts/phase4/replay/query_journal_all_seeds.csv",
                "artifacts/phase2/features/row_metadata.csv",
                "artifacts/phase6/uncertainty/learning_curves.csv"]
for name in source_names:
    check(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == baseline["sourceHashes"][name], "Original source hash: " + name)
journal = {(row["seed"], row["policy"], row["query_number"]): row for row in rows(ROOT / source_names[0])}
metadata = {row["material_id"]: row for row in rows(ROOT / source_names[1])}
curves = {(row["seed"], row["policy"], row["queries"]): row for row in rows(ROOT / source_names[2])}
seeds = sorted({key[0] for key in curves})
policies = {key[1] for key in curves}
check(len(seeds) == 5 and len(policies) == 5 and len(curves) == 125,
      "Independent source has all five saved splits, five policies and five boundaries")
policy_labels = {"quality": "Quality", "full": "Full", "quality_diversity": "Quality + Diversity",
                 "random": "Random", "uncertainty": "Uncertainty"}
comparison_columns = {
    "mode", "seed", "policy", "policy_label", "completed_queries", "historical_near_stable_hits_mean",
    "historical_near_stable_hits_sample_sd", "precision_mean_fraction", "precision_sample_sd_fraction",
    "chemical_system_coverage_mean", "chemical_system_coverage_sample_sd", "aggregate_split_count",
    "near_stable_threshold_eV_per_atom_inclusive", "reference_hull_threshold_eV_per_atom_inclusive",
    "study_id", "data_release_id", "source_ids", "scope", "null_meaning",
}
query_columns = {
    "seed", "policy", "batch", "query_number", "material_id", "formula", "reduced_formula",
    "chemical_system", "physical_atoms", "selection_role", "recorded_acquisition_score",
    "predicted_mean_eV_per_atom", "calibrated_radius_eV_per_atom", "diversity_at_selection",
    "historical_target_eV_per_atom", "historical_near_stable_hit", "reference_hull_hit", "label_visibility",
    "study_id", "data_release_id", "source_ids", "null_meaning", "scope",
}
files = sorted((W / "reports/downloads").glob("*.csv"))
check(len(files) >= 3, "Actual predictions, revealed queries and comparison CSV downloads retained")
visibility_files = set()
point_origin_files = []
aggregate_files = []
for path in files:
    data = rows(path)
    check(len(data) > 0, "Downloaded CSV has rows: " + path.name)
    if "query_number" in data[0]:
        match = re.fullmatch(r"flamel-queries-(\d+)-([a-z_]+)-batch-([1-5])-(predictions|revealed)\.csv", path.name)
        check(bool(match), "Query download has its recorded selection identity in filename: " + path.name)
        selected_seed, selected_policy, selected_batch, selected_visibility = match.groups()
        check(selected_seed in seeds and selected_policy in policies, "Query filename uses a real saved seed/policy")
        expected_visibility = "hidden" if selected_visibility == "predictions" else "revealed"
        visibility_files.add(expected_visibility)
        check(set(data[0]) == query_columns, "Query CSV fields and eV-per-atom unit labels are exact")
        check(len(data) == 10, "Downloaded batch contains exactly ten selections: " + path.name)
        expected_numbers = sorted(int(key[2]) for key, record in journal.items()
                                  if key[0] == selected_seed and key[1] == selected_policy and record["round"] == selected_batch)
        check([int(row["query_number"]) for row in data] == expected_numbers,
              "Query CSV contains exactly its selected batch in original selection order")
        for row in data:
            check((row["seed"], row["policy"], row["batch"], row["label_visibility"]) ==
                  (selected_seed, selected_policy, selected_batch, expected_visibility),
                  "Every query row retains exact selected split, policy, batch and reveal filter")
            source = journal[(row["seed"], row["policy"], row["query_number"])]
            meta = metadata[source["material_id"]]
            check(source["round"] == row["batch"] and source["material_id"] == row["material_id"], "Query identity and saved batch agree")
            for key in ["formula", "reduced_formula", "chemical_system"]:
                check(row[key] == meta[key], "Selected metadata agrees: " + key)
            check(row["physical_atoms"] == meta["n_sites"], "Actual physical atoms agree")
            check(row["selection_role"] == source["role"], "Saved selection role agrees")
            for public, original in [("predicted_mean_eV_per_atom", "predicted_mean_eV_atom"),
                                     ("calibrated_radius_eV_per_atom", "calibrated_radius_eV_atom"),
                                     ("diversity_at_selection", "diversity_at_selection")]:
                check(close(row[public], source[original]), "Full-precision prediction field agrees: " + public)
            check((row["recorded_acquisition_score"] == "" and source["score"] == "") or
                  (source["score"] != "" and close(row["recorded_acquisition_score"], source["score"])), "Recorded score/null preserved")
            if row["label_visibility"] == "hidden":
                check(all(row[key] == "" for key in ["historical_target_eV_per_atom", "historical_near_stable_hit", "reference_hull_hit"]), "Pre-reveal downloaded targets and both hit flags are empty")
            else:
                check(row["label_visibility"] == "revealed", "CSV reveal state is valid")
                check(close(row["historical_target_eV_per_atom"], source["label_eV_atom"]), "Downloaded historical target agrees")
                check(row["historical_near_stable_hit"] == str(float(source["label_eV_atom"]) <= .05).lower(), "Inclusive near-stable hit agrees")
                check(row["reference_hull_hit"] == str(float(source["label_eV_atom"]) <= 0).lower(), "Inclusive reference-hull hit agrees")
            check(row["source_ids"] == "selected_queries;selected_row_metadata" and
                  row["data_release_id"] == baseline["dataReleaseId"] and
                  row["study_id"] == "flamel-frozen-study-20261022", "Query source/study/release identity retained")
            check(row["scope"] == "Selected records only; not the candidate pool. Teaching reveal only; outcomes exist in public static data.",
                  "Query CSV clearly scopes selected records and pedagogical reveal")
    else:
        match = re.fullmatch(r"flamel-comparison-(aggregate|\d+)-(0|10|20|30|40|50)queries\.csv", path.name)
        check(bool(match), "Comparison download has its actual scope and budget in filename: " + path.name)
        selection, selected_budget = match.groups()
        selected_budget = int(selected_budget)
        aggregate = selection == "aggregate"
        check(aggregate or selection in seeds, "Comparison filename names aggregate or an actual split")
        check(set(data[0]) in (comparison_columns, comparison_columns | {"point_origin"}),
              "Comparison CSV has exact metric, fraction and energy-threshold units")
        if "point_origin" in data[0]:
            point_origin_files.append(path.name)
        if aggregate:
            aggregate_files.append(path.name)
        identities = [(row["policy"], row["completed_queries"]) for row in data]
        check(len(identities) == len(set(identities)), "Comparison selection has no repeated policy/budget rows")
        selected_policies = {row["policy"] for row in data}
        check(bool(selected_policies) and selected_policies <= policies, "Comparison contains only real selected policies")
        expected_identities = {(policy, str(count)) for policy in selected_policies
                               for count in range(0, selected_budget + 1, 10)}
        check(set(identities) == expected_identities,
              "Comparison includes exactly selected policies and all boundaries through filename budget")
        for row in data:
            count = int(row["completed_queries"])
            check(row["mode"] == ("aggregate" if aggregate else "seed"), "Browser comparison preserves its selected mode")
            check(row["seed"] == ("" if aggregate else selection), "Aggregate seed is blank; single-split seed matches filter")
            check(row["aggregate_split_count"] == ("5" if aggregate else ""), "Aggregate split count is five; single split has no aggregate count")
            check(row["policy_label"] == policy_labels[row["policy"]], "Policy display label agrees with selected policy")
            check(close(row["near_stable_threshold_eV_per_atom_inclusive"], .05) and
                  close(row["reference_hull_threshold_eV_per_atom_inclusive"], 0),
                  "CSV retains inclusive 0.05 and zero eV/atom historical thresholds")
            if count == 0:
                check(row["historical_near_stable_hits_mean"] == "0" and row["chemical_system_coverage_mean"] == "0" and row["precision_mean_fraction"] == "", "Downloaded zero origin has counts zero, precision unavailable")
                check(row["historical_near_stable_hits_sample_sd"] == ("0" if aggregate else "") and
                      row["chemical_system_coverage_sample_sd"] == ("0" if aggregate else "") and
                      row["precision_sample_sd_fraction"] == "",
                      "Zero-query aggregate count SD is zero and undefined precision SD is empty")
            else:
                source_seeds = seeds if aggregate else [selection]
                originals = [curves[(seed, row["policy"], str(count))] for seed in source_seeds]
                independent_metrics = [
                    ("historical_near_stable_hits_mean", "historical_near_stable_hits_sample_sd",
                     [float(record["near_stable_hits"]) for record in originals]),
                    ("precision_mean_fraction", "precision_sample_sd_fraction",
                     [float(record["near_stable_hits"]) / count for record in originals]),
                    ("chemical_system_coverage_mean", "chemical_system_coverage_sample_sd",
                     [float(record["chemical_system_coverage"]) for record in originals]),
                ]
                for mean_key, sd_key, values in independent_metrics:
                    check(close(row[mean_key], statistics.mean(values)),
                          "Independently reconstructed browser mean agrees: " + mean_key)
                    if aggregate:
                        check(close(row[sd_key], statistics.stdev(values)),
                              "Independent five-split sample SD (n-1) agrees: " + sd_key)
            if not aggregate:
                check(all(row[key] == "" for key in ["historical_near_stable_hits_sample_sd", "precision_sample_sd_fraction", "chemical_system_coverage_sample_sd"]), "Single-split CSV has no invented split SD")
            if "point_origin" in row:
                check(row["point_origin"] == ("derived_zero_state" if count == 0 else "recorded_batch_boundary"), "Downloaded point origin is explicitly labelled")
            check(row["source_ids"] == "learning_curves;policy_endpoints" and
                  row["data_release_id"] == baseline["dataReleaseId"] and
                  row["study_id"] == "flamel-frozen-study-20261022", "Comparison source/study/release identity retained")
            check(row["scope"] == ("Five split outcomes; descriptive sample SD (n-1), not a confidence interval." if aggregate
                                   else "One recorded split; no split-variability band."),
                  "Comparison download states the appropriate variability scope")
check(visibility_files == {"hidden", "revealed"}, "Both predictions-only and revealed actual query downloads are retained")
check(bool(point_origin_files), "At least one final actual comparison CSV includes explicit point_origin")
check(bool(aggregate_files), "Actual aggregate browser CSV is independently verified")
report = {"phase": "W3", "status": "passed", "checkedAt": datetime.now(timezone.utc).isoformat(),
          "checksPassed": len(checks), "dataReleaseId": baseline["dataReleaseId"],
          "scope": "Actual browser CSV artifacts compared independently to original frozen journal, metadata and curves.",
          "aggregateFiles": aggregate_files, "pointOriginFiles": point_origin_files,
          "queryDownloadVisibilities": sorted(visibility_files), "aggregateMetrics": ["hits", "precision", "chemical-system coverage"],
          "files": [{"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in files], "checks": checks}
(W / "reports/W3_DOWNLOAD_VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "passed", "checksPassed": len(checks), "downloadFiles": len(files)}))
