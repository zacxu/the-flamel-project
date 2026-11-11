"""Freeze label-blind whole-chemical-system replay partitions and oracle store."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase2/splits"
PALETTE = ["Mg", "Ca", "Sr", "Ba", "Zn", "Al", "Ga", "In", "Ti", "Zr", "Hf", "Sn"]
SEEDS = [20261022, 20261023, 20261024, 20261025, 20261026]
TARGET = "e_above_hull_mp2020_corrected_ppd_mp"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def fill_exact(groups, sizes, target, rng, mandatory=()):
    """Random order, whole-group knapsack; no outcome or feature values are inputs."""
    mandatory = list(mandatory)
    remainder = target - sum(sizes[g] for g in mandatory)
    if remainder < 0:
        raise RuntimeError("Mandatory element coverage exceeds the target")
    candidates = sorted(set(groups)-set(mandatory))
    rng.shuffle(candidates)
    # Dynamic programming finds an exact row count without splitting a group.
    previous = {0: None}
    for group in candidates:
        count = sizes[group]
        for total in sorted(list(previous), reverse=True):
            new = total + count
            if new <= remainder and new not in previous:
                previous[new] = (total, group)
        if remainder in previous:
            break
    if remainder not in previous:
        raise RuntimeError(f"Cannot meet target {target} without splitting chemical systems")
    selected = list(mandatory)
    while remainder:
        remainder, group = previous[remainder]
        selected.append(group)
    return sorted(selected)


def coverage_core(groups, sizes, rng):
    """Cover all available elements in initial training using labels-blind groups."""
    group_elements = {g: set(g.split("-")) for g in groups}
    uncovered = set().union(*group_elements.values())
    chosen = []
    tie = {g: rng.random() for g in sorted(groups)}
    while uncovered:
        rare_element = min(uncovered, key=lambda e: (sum(e in v for v in group_elements.values()), e))
        options = [g for g in groups if rare_element in group_elements[g]]
        group = min(options, key=lambda g: (sizes[g], -len(group_elements[g] & uncovered), tie[g], g))
        chosen.append(group)
        uncovered -= group_elements[group]
    return sorted(set(chosen))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / "artifacts/phase1/data/eligible_population.csv"
    with source.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 8294 or len({r["material_id"] for r in rows}) != 8294:
        raise RuntimeError("Expected the audited unique eligible population")
    reserved = sorted({"-".join(sorted(metals+("O",))) for n in (1, 2)
                       for metals in itertools.combinations(PALETTE, n)})
    groups = {}
    for row in rows:
        groups.setdefault(row["chemical_system"], []).append(row["material_id"])
    available = sorted(set(groups)-set(reserved))
    sizes = {g: len(v) for g, v in groups.items()}
    counts = []
    assignments = []
    union_elements = set().union(*(set(g.split("-")) for g in available))
    for seed in SEEDS:
        rng = random.Random(seed)
        core = coverage_core(available, sizes, rng)
        training = fill_exact(available, sizes, 2000, rng, core)
        remainder = sorted(set(available)-set(training))
        calibration = fill_exact(remainder, sizes, 400, rng)
        remainder = sorted(set(remainder)-set(calibration))
        pool = fill_exact(remainder, sizes, 2000, rng)
        unused = sorted(set(remainder)-set(pool))
        partitions = {"train": training, "calibration": calibration, "pool": pool, "unused": unused,
                      "fresh_reserved": sorted(set(groups) & set(reserved))}
        ids = {name: sorted(material_id for g in gs for material_id in groups[g]) for name, gs in partitions.items()}
        assert [len(ids[k]) for k in ["train", "calibration", "pool"]] == [2000, 400, 2000]
        assert set().union(*(set(g.split("-")) for g in training)) == union_elements
        assert not (set(training) | set(calibration) | set(pool)) & set(reserved)
        assert sum(map(len, ids.values())) == 8294
        flat = [material_id for values in ids.values() for material_id in values]
        assert len(set(flat)) == 8294
        record = {"seed": seed, "groups": partitions, "material_ids": ids,
                  "counts": {k: {"rows": len(ids[k]), "chemical_systems": len(partitions[k])} for k in partitions},
                  "training_elements": sorted(union_elements), "all_candidate_elements_seen_individually_in_training": True,
                  "whole_systems_only": True, "target_labels_read_for_split_selection": False}
        dump(OUT / f"seed_{seed}.json", record)
        counts.append({"seed": seed, **record["counts"]})
        for partition, chemical_systems in partitions.items():
            for group in chemical_systems:
                assignments.extend({"seed": seed, "material_id": mid, "chemical_system": group, "partition": partition} for mid in sorted(groups[group]))
    with (OUT / "assignments.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["seed", "material_id", "chemical_system", "partition"])
        writer.writeheader()
        writer.writerows(assignments)
    dump(OUT / "reserved_systems.json", {
        "reservation_policy": "All 78 binary/ternary O chemical systems from the fixed 12-metal palette, including every control, proposal and reserve; stronger than reserving only selected formulas.",
        "palette": PALETTE, "chemical_systems": reserved,
        "observed_eligible_reserved_systems": len(set(groups) & set(reserved)),
        "eligible_reserved_rows": sum(sizes.get(g, 0) for g in reserved),
        "available_rows": sum(sizes[g] for g in available), "available_systems": len(available),
        "applies_to_all_seeds": True, "reserved_from_training_calibration_and_replay_pool": True})
    # Only after ID/group assignments are frozen do we materialize labels, in a separate oracle file.
    eligible_ids = {r["material_id"] for r in rows}
    labels = {}
    with gzip.open(ROOT / "data/wbm/2023-12-13-wbm-summary.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["material_id"] in eligible_ids:
                labels[row["material_id"]] = row[TARGET]
    if len(labels) != len(eligible_ids):
        raise RuntimeError("Oracle labels did not join all feature IDs")
    with (OUT / "oracle_labels.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["material_id", TARGET])
        writer.writerows((mid, labels[mid]) for mid in sorted(labels))
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": "frozen", "seeds": SEEDS,
                "fresh_selector_seed": SEEDS[0], "paired_policies_use_identical_splits": True,
                "initial_labels_per_replay": 2400, "additional_query_budget_per_policy_seed": 50,
                "target_column": TARGET, "signed_values_preserved": True,
                "label_read_order": "All split assignments written before reading target values; target values never enter split allocation.",
                "oracle_scope": "Separate historical labels. Only training/calibration and explicitly selected pool labels may enter a policy fit. Evaluation-only oracle reads cannot influence decisions.",
                "grouping": "Lexically sorted element symbols joined by hyphen; all eligible rows in an assigned system go to one partition.",
                "initial_training_element_coverage": "A label-blind coverage core includes every available element before random-order whole-group subset-sum fill.",
                "split_targets_met_exactly_without_group_splitting": True,
                "counts": counts,
                "population_source": {"path": source.relative_to(ROOT).as_posix(), "sha256": digest(source)},
                "files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p)} for p in sorted(OUT.glob("*")) if p.is_file() and p.name != "manifest.json"],
                "script_sha256": digest(Path(__file__))}
    dump(OUT / "manifest.json", manifest)
    print(json.dumps({"status": "frozen", "seeds": SEEDS, "reserved_rows": 476,
                      "available_rows": 7818, "split_sizes_each": [2000, 400, 2000],
                      "available_elements": len(union_elements), "model_fits": 0, "queries_revealed": 0}))


if __name__ == "__main__":
    main()
