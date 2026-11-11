"""Independently validate the public W1 release against saved research bytes.

This module does not import the exporter, call research finalizers, infer
symmetry, run predictors, optimize structures or dispatch scientific jobs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime
import hashlib
import itertools
import json
import math
from pathlib import Path, PurePosixPath
import re
import statistics
import sys
from urllib.parse import urlsplit

import numpy as np


WEBSITE = Path(__file__).resolve().parents[1]
ROOT = WEBSITE.parent
PUBLIC = WEBSITE / "public" / "research"
REPORT = WEBSITE / "reports" / ("W6_RESEARCH_VALIDATION.json" if "--phase=W6" in sys.argv else "W5_RESEARCH_VALIDATION.json" if "--phase=W5" in sys.argv else "W4_RESEARCH_VALIDATION.json" if "--phase=W4" in sys.argv else "W3_RESEARCH_VALIDATION.json" if "--phase=W3" in sys.argv else "W2_RESEARCH_VALIDATION.json" if "--phase=W2" in sys.argv else "W1_VALIDATION.json")
SEEDS = set(range(20261022, 20261027))
POLICIES = {"full", "quality", "quality_diversity", "random", "uncertainty"}
CHECKS: list[dict] = []


def check(condition, description, **details):
    CHECKS.append({"check": description, "passed": bool(condition), **details})
    if not condition:
        raise ValueError(description)


def strict_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"Duplicate JSON key {key!r}")
            value[key] = item
        return value

    def constant(value):
        raise ValueError(f"Non-JSON numeric constant {value}")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=constant)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def rows(relative):
    with (ROOT / relative).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def number(value):
    check(isinstance(value, (int, float)) and not isinstance(value, bool)
          and math.isfinite(value), "Finite numeric field", value=value)
    return value


def near(a, b, atol=1e-10):
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=atol)


def identity(row):
    return row["seed"], row["policy"], row["queries"]


def validate_public_strings(value, location="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            check(not re.search(r"(?i)^(password|passwd|api[_-]?key|secret|access[_-]?token|session[_-]?id|evaluation[_-]?(ids|targets)|eval[_-]?ids|y_true|oracle[_-]?targets)$", key),
                  "Public key excludes secrets and complete evaluation targets", location=f"{location}.{key}")
            validate_public_strings(item, f"{location}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            validate_public_strings(item, f"{location}[{i}]")
    elif isinstance(value, str):
        check(not re.search(r"(?i)((?<![a-z])[A-Z]:[\\/]|/Users/|/home/|filemanager\.ai|scriptinstall\.rocks|cpsess\d|(?:\?|&)(?:login|post_login|token|session|password)=)", value),
              "Public string excludes local paths, admin URLs and credentials", location=location)
        check(not any(token in value.lower() for token in ("artifacts/phase", "vendor/quantum_espresso", ".envs/", "node_modules/")),
              "Public string excludes internal research/runtime paths", location=location)
    elif isinstance(value, float):
        check(math.isfinite(value), "All JSON numbers finite", location=location)
    elif value is not None:
        check(isinstance(value, (int, bool)), "Supported JSON primitive", location=location)


def source_references(value, known, location="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "sourceId" or key.endswith("SourceId"):
                check(item is None or isinstance(item, str) and item in known,
                      "Public source reference resolves", location=f"{location}.{key}")
            elif key == "sourceIds" or key.endswith("SourceIds"):
                check(isinstance(item, list) and all(source in known for source in item),
                      "Public source-reference array resolves", location=f"{location}.{key}")
            source_references(item, known, f"{location}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            source_references(item, known, f"{location}[{i}]")


def validate_release():
    manifest = strict_json(PUBLIC / "manifest.json")
    check(manifest["schemaVersion"] == 1 and bool(manifest["studyId"])
          and bool(manifest["dataReleaseId"]), "Manifest schema and release/study identity")
    check(datetime.fromisoformat(manifest["generatedAt"].replace("Z", "+00:00")).tzinfo is not None,
          "Export time is explicitly zoned")
    files = manifest["files"]
    check(len({entry["logicalName"] for entry in files}) == len(files)
          and len({entry["path"] for entry in files}) == len(files), "Unique logical and immutable output paths")
    datasets, assets = {}, {}
    for entry in files:
        relative = PurePosixPath(entry["path"])
        full = (PUBLIC / relative).resolve()
        check(not relative.is_absolute() and ".." not in relative.parts and "\\" not in entry["path"]
              and full.is_relative_to(PUBLIC.resolve()) and full.is_file(),
              "Manifest output is an existing bounded public file", logicalName=entry["logicalName"])
        check(relative.parts[:2] == ("releases", manifest["dataReleaseId"]),
              "Every data asset belongs to the pinned release", logicalName=entry["logicalName"])
        actual_hash = digest(full)
        check(re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is not None
              and entry["sha256"] == actual_hash and full.stat().st_size == entry["bytes"],
              "Manifest hash and byte count match output", logicalName=entry["logicalName"])
        check(actual_hash[:16] in relative.name, "Output filename contains its content hash", logicalName=entry["logicalName"])
        if entry["mediaType"] == "application/json":
            data = strict_json(full)
            check(data["schemaVersion"] == 1 and data["studyId"] == manifest["studyId"]
                  and data["dataset"] + ".json" == entry["logicalName"],
                  "Dataset schema/study/logical identity", logicalName=entry["logicalName"])
            check(entry["bytes"] < 500_000, "JSON shard below 500 kB", logicalName=entry["logicalName"])
            validate_public_strings(data, entry["logicalName"])
            datasets[entry["logicalName"]] = data
        else:
            if entry["mediaType"] == "image/png":
                check(full.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
                      "Public image has a valid PNG signature", logicalName=entry["logicalName"])
            else:
                check(entry["mediaType"] == "text/plain; charset=utf-8"
                      and entry["logicalName"].startswith("notices/")
                      and bool(full.read_text(encoding="utf-8")),
                      "Other public assets are explicitly typed nonempty attribution text", logicalName=entry["logicalName"])
            assets[entry["logicalName"]] = full
    check("provenance.json" in datasets, "Public source registry present")
    sources = datasets["provenance.json"]["sources"]
    check(len({source["sourceId"] for source in sources}) == len(sources), "Unique opaque public source IDs")
    source_by_id = {source["sourceId"]: source for source in sources}
    for data in datasets.values():
        source_references(data, source_by_id)
    validate_public_strings(manifest, "manifest")
    immutable = PUBLIC / "releases" / manifest["dataReleaseId"] / "manifest.json"
    check(immutable.is_file() and immutable.read_bytes() == (PUBLIC / "manifest.json").read_bytes(),
          "Mutable discovery pointer currently equals its immutable release manifest")
    pin_text = (WEBSITE / "src/data/release.ts").read_text(encoding="utf-8")
    match = re.search(r"export const DATA_RELEASE\s*=\s*(\{.*\})\s+as const;", pin_text, re.S)
    check(match is not None, "Frontend immutable data-release pin exists")
    pin = json.loads(match.group(1))
    check(pin["dataReleaseId"] == manifest["dataReleaseId"]
          and pin["studyId"] == manifest["studyId"]
          and pin["manifestSha256"] == digest(immutable)
          and pin["manifestPath"] == "research/" + immutable.relative_to(PUBLIC).as_posix(),
          "Frontend pin binds exact immutable manifest, study and release")
    return manifest, datasets, assets, source_by_id


def validate_originals(public_sources):
    inventory = strict_json(WEBSITE / "research_sources.json")
    for relative, expected in inventory["baseline_integrity"].items():
        check(digest(ROOT / relative) == expected, "Original frozen numerical baseline remains unchanged", source=relative)
    private = strict_json(WEBSITE / "reports" / "W1_EXPORT.json")
    inputs = private.get("inputAllowlist", private.get("inputs"))
    check(isinstance(inputs, (dict, list)), "Exporter records a private named source allowlist")
    if isinstance(inputs, dict):
        inputs = [dict(row, path=row.get("path", name)) for name, row in inputs.items()]
    by_id = {}
    for item in inputs:
        relative = item.get("path", item.get("workspaceRelativePath", item.get("workspace_relative_path")))
        file = (ROOT / relative).resolve()
        check(file.is_relative_to(ROOT.resolve()) and file.is_file(), "Private source path stays within study", source=relative)
        check(digest(file) == item["sha256"] and file.stat().st_size == item["bytes"],
              "Independent original source bytes agree with recorded allowlist", source=relative)
        source_id = item.get("sourceId", item.get("id"))
        check(source_id not in by_id, "Private source ID unambiguous", sourceId=source_id)
        by_id[source_id] = {**item, "absolutePath": file}
    check(set(public_sources) == set(by_id), "Public provenance exactly matches the private named allowlist")
    for source_id, public in public_sources.items():
        check(public["sha256"] == by_id[source_id]["sha256"] and public["bytes"] == by_id[source_id]["bytes"],
              "Opaque public provenance binds to original source bytes", sourceId=source_id)
    return by_id


def validate_replay(data):
    curves = data["replay/curves.json"]
    check(set(curves["seeds"]) == SEEDS and set(curves["policies"]) == POLICIES, "Frozen replay grid unchanged")
    points, endpoints = curves["points"], curves["endpoints"]
    check(len(points) == 125 and len(endpoints) == 25, "125 nonzero learning points and 25 endpoints")
    point_lookup = {identity(point): point for point in points}
    endpoint_lookup = {(point["seed"], point["policy"]): point for point in endpoints}
    check(len(point_lookup) == 125 and len(endpoint_lookup) == 25, "Replay point keys are unique")
    origin = curves["zeroQueryOrigin"]
    check(all(origin[key] == 0 for key in ("queries", "nearStableHits", "referenceHullHits", "chemicalSystemCoverage"))
          and origin["precision"] is None and origin["origin"] == "derived_zero_state" and bool(origin["label"]),
          "Zero-query origin is labelled as a derived display state with unavailable precision")
    metadata_rows = rows("artifacts/phase2/features/row_metadata.csv")
    metadata = {row["material_id"]: row for row in metadata_rows}
    originals = rows("artifacts/phase4/replay/query_journal_all_seeds.csv")
    journal = {(int(row["seed"]), row["policy"], int(row["query_number"])): row for row in originals}
    all_ids, events = set(), 0
    role_hits, role_queries = Counter(), Counter()
    for seed in sorted(SEEDS):
        shard = data[f"replay/seed-{seed}.json"]
        check(shard["seed"] == seed and {h["policy"] for h in shard["histories"]} == POLICIES
              and len(shard["histories"]) == 5, "Seed shard contains five distinct policies", seed=seed)
        for history in shard["histories"]:
            policy = history["policy"]
            batches = history["batches"]
            check([batch["round"] for batch in batches] == [1, 2, 3, 4, 5], "Five ordered recorded batches", seed=seed, policy=policy)
            observed, systems, near_hits, hull_hits = [], set(), 0, 0
            for batch in batches:
                check(len(batch["queries"]) == 10, "Recorded batch has ten selections", seed=seed, policy=policy, batch=batch["round"])
                check(datetime.fromisoformat(batch["decision"]["utc"]) <= datetime.fromisoformat(batch["reveal"]["utc"]),
                      "Recorded reveal follows its decision", seed=seed, policy=policy, batch=batch["round"])
                for query in batch["queries"]:
                    key = seed, policy, query["queryNumber"]
                    original, joined = journal[key], metadata[query["materialId"]]
                    check(query["materialId"] == original["material_id"]
                          and query["formula"] == joined["formula"]
                          and query["reducedFormula"] == joined["reduced_formula"]
                          and query["chemicalSystem"] == joined["chemical_system"]
                          and query["atoms"] == int(joined["n_sites"]),
                          "Selection identity/formula/system/atom metadata independently joined", key=list(key))
                    for public, source in [("predictedMeanEVPerAtom", "predicted_mean_eV_atom"),
                                           ("calibratedRadiusEVPerAtom", "calibrated_radius_eV_atom"),
                                           ("diversityAtSelection", "diversity_at_selection"),
                                           ("revealedLabelEVPerAtom", "label_eV_atom")]:
                        check(near(query[public], original[source]), "Selected numerical field matches saved journal", key=list(key), field=public)
                    check(type(query["nearStableHit"]) is bool and type(query["referenceHullHit"]) is bool,
                          "Historical hit fields are booleans", key=list(key))
                    label = query["revealedLabelEVPerAtom"]
                    check(query["nearStableHit"] == (label <= .05)
                          and query["referenceHullHit"] == (label <= 0),
                          "Historical hit thresholds are inclusive with signed labels", key=list(key))
                    check((query["score"] is None) == (policy == "random")
                          and (query["score"] is None or near(query["score"], original["score"])),
                          "Random score remains null; recorded scores remain exact", key=list(key))
                    check(query["role"] == original["role"], "Recorded acquisition role preserved", key=list(key))
                    observed.append(query["queryNumber"])
                    all_ids.add(query["materialId"])
                    systems.add(query["chemicalSystem"])
                    near_hits += label <= .05
                    hull_hits += label <= 0
                    events += 1
                    if policy == "full":
                        role_queries[query["role"]] += 1
                        role_hits[query["role"]] += label <= .05
                calculated = {"queries": len(observed), "nearStableHits": near_hits,
                              "referenceHullHits": hull_hits, "chemicalSystemCoverage": len(systems)}
                check(calculated == batch["cumulativeAfterReveal"]
                      and all(point_lookup[seed, policy, len(observed)][field] == value for field, value in calculated.items()),
                      "Independently reconstructed histories reproduce cumulative curves", seed=seed, policy=policy, queries=len(observed))
            check(observed == list(range(1, 51)), "Selection history query numbering is complete", seed=seed, policy=policy)
            endpoint = endpoint_lookup[seed, policy]
            check(all(endpoint[field] == value for field, value in calculated.items())
                  and near(endpoint["precisionAt50"], near_hits / 50), "History reproduces endpoint precision/counts", seed=seed, policy=policy)
    check(events == 1250 and len(all_ids) == 720, "1250 selected events and 720 distinct queried materials")
    check(role_queries == {"conservative": 175, "optimistic": 75}
          and role_hits == {"conservative": 140, "optimistic": 7}, "Full-policy selected roles preserve 140/175 versus 7/75")
    for policy in POLICIES:
        for metric in ("nearStableHits", "referenceHullHits", "chemicalSystemCoverage", "precisionAt50"):
            values = [endpoint_lookup[seed, policy][metric] for seed in sorted(SEEDS)]
            aggregate = curves["policyStatistics"][policy][metric]
            check(aggregate["values"] == values and near(aggregate["mean"], statistics.mean(values))
                  and near(aggregate["sampleStd"], statistics.stdev(values))
                  and aggregate["min"] == min(values) and aggregate["max"] == max(values),
                  "Endpoint aggregate uses five split values and sample SD", policy=policy, metric=metric)
    differences = [endpoint_lookup[seed, "full"]["nearStableHits"] - endpoint_lookup[seed, "quality"]["nearStableHits"] for seed in sorted(SEEDS)]
    check(differences == [-9, -8, -19, -10, -13]
          and curves["fullMinusQualityHits"]["values"] == differences
          and near(curves["fullMinusQualityHits"]["sampleStd"], statistics.stdev(differences)),
          "All five negative paired outcomes and their sample SD retained")
    return {"events": events, "distinctSelectedMaterials": len(all_ids), "curves": 125, "endpoints": 25}


def validate_uncertainty(data):
    uncertainty = data["uncertainty.json"]
    metrics, risks, deciles, roles = (uncertainty[key] for key in ("evaluationMetrics", "riskCoverage", "deciles", "roles"))
    check([len(metrics), len(risks), len(deciles), len(roles)] == [130, 300, 300, 10], "Complete saved uncertainty source counts")
    expected = {(seed, "initial_shared", 0) for seed in SEEDS} | {(seed, policy, budget) for seed in SEEDS for policy in POLICIES for budget in range(10, 51, 10)}
    check({identity(row) for row in metrics} == expected and len({identity(row) for row in metrics}) == 130,
          "Initial snapshot appears once per seed and complete later grid is retained")
    metric_index = {identity(row): row for row in metrics}
    original_metrics = {(int(row["seed"]), row["policy"], int(row["queries"])): row
                        for row in rows("artifacts/phase6/uncertainty/evaluation_metrics.csv")}
    for row in metrics:
        original = original_metrics[identity(row)]
        check(all(near(row[public], original[source]) for public, source in [
            ("maeEVPerAtom", "MAE_eV_atom"), ("rmseEVPerAtom", "RMSE_eV_atom"),
            ("disagreementAbsoluteErrorSpearman", "Spearman_disagreement_absolute_error"),
            ("interval90EmpiricalCoverage", "interval_90_empirical_coverage"),
            ("meanIntervalWidthEVPerAtom", "mean_interval_width_eV_atom"),
            ("calibrationScale", "calibration_q")]),
            "All public uncertainty measurements independently agree with saved source row", key=list(identity(row)))
    endpoints = {(seed, "initial_shared", 0) for seed in SEEDS} | {(seed, policy, 50) for seed in SEEDS for policy in POLICIES}
    check({(*identity(row), round(row["requestedRetainedFraction"], 1)) for row in risks} == {(*key, i / 10) for key in endpoints for i in range(1, 11)},
          "Every endpoint has all ten recorded retention steps")
    check({(*identity(row), row["decile"]) for row in deciles} == {(*key, i) for key in endpoints for i in range(1, 11)},
          "Every endpoint has all ten disagreement deciles")
    for row in metrics:
        check(row["rows"] == 3418 and 0 <= row["interval90EmpiricalCoverage"] <= 1
              and row["meanIntervalWidthEVPerAtom"] >= 0 and row["maeEVPerAtom"] >= 0,
              "Evaluation counts, empirical fractions and error units have valid domains", key=list(identity(row)))
    for row in risks:
        count = metric_index[identity(row)]["rows"]
        check(row["retainedRows"] == math.ceil(count * row["requestedRetainedFraction"])
              and near(row["actualRetainedFraction"], row["retainedRows"] / count)
              and near(row["maeRelativeToAllRows"], row["maeEVPerAtom"] / row["allRowsMaeEVPerAtom"])
              and near(row["allRowsMaeEVPerAtom"], metric_index[identity(row)]["maeEVPerAtom"]),
              "Selective-risk retained rows/fraction and all-row comparison reconcile", key=list(identity(row)))
    for key in endpoints:
        subset = [row for row in deciles if identity(row) == key]
        check(sum(row["rows"] for row in subset) == 3418
              and near(sum(row["rows"] * row["maeEVPerAtom"] for row in subset) / 3418,
                       metric_index[key]["maeEVPerAtom"]), "Decile partition independently reproduces full MAE", key=list(key))
    for row in roles:
        check(row["queries"] == (35 if row["role"] == "conservative" else 15)
              and near(row["precision"], row["nearStableHits"] / row["queries"]),
              "Role precision uses actual frozen role counts", seed=row["seed"], role=row["role"])
    return {"evaluationSnapshots": 130, "riskRows": 300, "decileRows": 300, "roleRows": 10}


def validate_generation(data):
    generation = data["generation.json"]
    draws, cohorts, excluded = (generation[key] for key in ("draws", "cohorts", "excluded"))
    relaxed, prototypes, pairs = (generation[key] for key in ("relaxedStructures", "prototypes", "symmetryPairs"))
    check([len(draws), len(cohorts), len(excluded), len(relaxed), len(prototypes), len(pairs)] == [88, 12, 12, 11, 4, 2], "Generation/prototype/model table counts preserved")
    lookup = {row["candidateId"]: row for row in draws}
    original_draws = {row["candidate_id"]: row for row in rows("artifacts/phase6/structures/generation_draws.csv")}
    for row in draws:
        original = original_draws[row["candidateId"]]
        bool_fields = {"exactCountsMatch": "exact_counts_match", "geometryValid": "geometry_valid", "valid": "valid",
                       "correctRatioGeometryWithinCapDiagnosticOnly": "correct_ratio_geometry_within_cap_diagnostic_only",
                       "differentCellCountDiagnosticExcluded": "different_cell_count_diagnostic_excluded",
                       "largerCellDiagnosticExcluded": "larger_cell_diagnostic_excluded"}
        check(all(type(row[public]) is bool and row[public] == (original[source] == "True") for public, source in bool_fields.items())
              and row["atoms"] == int(original["n_atoms"])
              and row["actualCounts"] == json.loads(original["actual_counts"])
              and row["geometrySourceSha256"] == original["source_sha256"],
              "Generation booleans, physical counts and geometry identity agree with original source", candidateId=row["candidateId"])
    check(len(lookup) == 88 and all(lookup[row["candidateId"]] == row for row in excluded), "Excluded diagnostics remain a subset of emitted draws")
    new = [row for row in draws if row["kind"] == "new_composition"]
    check(len(new) == 48 and sum(row["valid"] for row in new) == 0
          and len({row["formula"] for row in new}) == 6, "Six proposal cohorts retain all 48 exact-cell failures")
    check(all(row["largerCellDiagnosticExcluded"] is True and row["valid"] is False for row in excluded), "All 12 larger-cell diagnostics remain explicitly excluded")
    for cohort in cohorts:
        members = [row for row in draws if all(row[key] == cohort[key] for key in ("scope", "kind", "control", "arm", "formula"))]
        check(len(members) == cohort["draws"] and sum(row["valid"] for row in members) == cohort["exactValid"]
              and sum(row["valid"] and row["duplicateOf"] is None for row in members) == cohort["exactValidUnique"],
              "Raw draw membership independently reproduces cohort yields", formula=cohort["formula"], scope=cohort["scope"], arm=cohort["arm"])
    model = {row["candidateId"]: row for row in relaxed}
    check(len(model) == 11 and Counter(row["role"] for row in relaxed) == {"symmetry": 4, "prototype": 4, "same_composition_reference": 3}
          and all(row["converged"] is True and row["newStableMaterialEstablished"] is False for row in relaxed),
          "Eleven model finals retain role/convergence and claim limits")
    for pair in pairs:
        check(pair["quotaPerArm"] == 1 and pair["energyDistributionEstablished"] is False and pair["dftStabilityComparison"] is False
              and near(pair["p1MinusNontrivialChgnetEVPerAtom"], model[pair["p1CandidateId"]]["chgnetEnergyEVPerAtom"] - model[pair["nontrivialCandidateId"]]["chgnetEnergyEVPerAtom"]),
              "One-pair CHGNet comparison has correct arithmetic and limited scope", control=pair["control"])
    check(all(row["freshDftSubmitted"] is False and row["stableMaterialEstablished"] is False for row in prototypes), "Prototype convergence does not promote candidates to DFT or stability claims")
    return {"actualDraws": 88, "cohorts": 12, "excludedLargerCellDiagnostics": 12, "modelFinals": 11}


def validate_dft(data):
    dft = data["dft.json"]
    jobs, memberships, missing, accepted = (dft[key] for key in ("jobs", "referenceMemberships", "missingMemberships", "acceptedGeometries"))
    check([len(jobs), len(memberships), len(missing), len(accepted)] == [19, 218, 215, 3], "Complete QE attempts, memberships and accepted geometries")
    check(len({row["jobId"] for row in jobs}) == 19 and len({(row["inventorySystem"], row["materialId"]) for row in memberships}) == 218,
          "QE jobs and inventory-system memberships have unique compound identities")
    original_jobs = {row["job_id"]: row for row in rows("artifacts/phase6/evidence/fresh_DFT_evidence_table.csv")}
    for job in jobs:
        source = original_jobs[job["jobId"]]
        bool_fields = {"jobDone": "JOB_DONE", "terminalScfAccepted": "terminal_SCF_accepted",
                       "stationaryAtThisSetting": "stationary_at_this_setting",
                       "acceptedWithFinalGeometrySensitivity": "accepted_with_final_geometry_sensitivity"}
        check(all(type(job[public]) is bool and job[public] == (source[field] == "True") for public, field in bool_fields.items()),
              "QE process, electronic, geometry and finite-sensitivity flags independently match saved source", jobId=job["jobId"])
        for public, field in {"energyEVPerAtom": "energy_eV_per_atom", "maxForceEVPerAngstrom": "max_force_eV_A", "maxFullStressKbar": "max_full_stress_kbar"}.items():
            check((job[public] is None and source[field] == "") or job[public] is not None and source[field] != "" and near(job[public], source[field]),
                  "QE terminal measurement/null matches source", jobId=job["jobId"], field=public)
    accepted_ids = {row["acceptedJobId"] for row in accepted}
    check(accepted_ids == {job["jobId"] for job in jobs if job["acceptedWithFinalGeometrySensitivity"]}, "Exactly three fully checked QE relaxed geometries")
    check(missing == [row for row in memberships if not row["acceptedFreshCompatibleQe"]]
          and len({row["materialId"] for row in memberships if row["acceptedFreshCompatibleQe"]}) == 2,
          "Missing memberships are complement; accepted source IDs remain two")
    for system, expected in {"Ca-Mg-O": (161, 2, 159), "Mg-O": (57, 1, 56)}.items():
        subset = [row for row in memberships if row["inventorySystem"] == system]
        checked = sum(row["acceptedFreshCompatibleQe"] for row in subset)
        check((len(subset), checked, len(subset) - checked) == expected, "Reference coverage counts memberships without cross-system deduplication", system=system)
    for row in accepted:
        check(row["maxForceEVPerAngstrom"] <= .0205688269904 and row["maxFullStressKbar"] <= .5
              and row["cutoffShiftEVPerAtom"] <= .005 and row["kpointShiftEVPerAtom"] <= .005,
              "Accepted QE results satisfy independent finite force/stress/sensitivity thresholds", jobId=row["acceptedJobId"])
    perturbations = [row for row in jobs if row["phase"] == 5]
    check(len(perturbations) == 1 and all(not row["terminalScfAccepted"] and not row["stationaryAtThisSetting"]
              and not row["acceptedWithFinalGeometrySensitivity"] and row["energyEVPerAtom"] is None
              and row["maxForceEVPerAngstrom"] is None and row["maxFullStressKbar"] is None for row in perturbations),
          "Time-limited perturbation preserves absent terminal evidence as null")
    check(all(dft[key] is False for key in ("perturbationValidationComplete", "phononCalculationPerformed", "fullHullEstablished", "newStableMaterialEstablished"))
          and dft["knownMgoControl"]["energyOrderingResolved"] is False,
          "Incomplete perturbation/hull/phonon and unresolved known-control energy limits retained")
    return {"qeAttempts": 19, "referenceMemberships": 218, "missingMemberships": 215, "acceptedRelaxedGeometries": 3, "acceptedOriginalSourceIds": 2}


def validate_geometry(data, sources, assets):
    index = data["structures/index.json"]
    stages = {entry["stageId"]: data[entry["logicalFile"]] for entry in index["stages"]}
    check(len(stages) == 26 and len(index["candidates"]) == 14, "Fourteen entities and 26 saved stages")
    nonorthogonal, accepted = [], []
    translations = np.asarray(list(itertools.product(range(-2, 3), repeat=3)), dtype=float)
    model_results = {row["candidateId"]: row for row in data["generation.json"]["relaxedStructures"]}
    qe_results = {row["jobId"]: row for row in data["dft.json"]["jobs"]}
    fallback_files = set()
    for stage_id, stage in stages.items():
        geometry = stage["geometry"]
        basis = np.asarray(geometry["latticeRowsAngstrom"], dtype=float)
        fractional = np.asarray(geometry["fractionalCoordinates"], dtype=float)
        atoms = geometry["actualAtoms"]
        check(basis.shape == (3, 3) and fractional.shape == (atoms, 3)
              and np.isfinite(basis).all() and np.isfinite(fractional).all(), "Saved geometry has finite 3D basis and physical atom count", stageId=stage_id)
        check(len(geometry["sites"]) == atoms and [row["siteIndex"] for row in geometry["sites"]] == list(range(atoms))
              and all(len(site["species"]) == 1 and site["species"][0]["occupancy"] == 1 for site in geometry["sites"]),
              "Site order, ordered occupancy and physical atom counts agree", stageId=stage_id)
        check(geometry["pbc"] == [True, True, True] and geometry["displayWrappingApplied"] is False
              and geometry["periodicImagesAdded"] is False, "Saved periodic geometry has no invented display atoms", stageId=stage_id)
        determinant = np.linalg.det(basis)
        check(determinant > 0 and near(determinant, geometry["volumeAngstrom3"], 1e-8)
              and np.allclose((fractional @ basis) @ np.linalg.inv(basis), fractional, rtol=0, atol=1e-12),
              "Independent row-basis Cartesian roundtrip and positive determinant volume", stageId=stage_id)
        gram = basis @ basis.T
        if not np.allclose(gram, np.diag(np.diag(gram)), rtol=0, atol=1e-6):
            nonorthogonal.append(stage_id)
        source = sources[stage["sourceId"]]
        original = strict_json(source["absolutePath"])
        source_basis = np.asarray(original["lattice"]["matrix"], dtype=float)
        source_fractional = np.asarray([site["abc"] for site in original["sites"]], dtype=float)
        source_cartesian = np.asarray([site["xyz"] for site in original["sites"]], dtype=float)
        check(stage["sourceSha256"] == source["sha256"] and len(original["sites"]) == atoms
              and np.allclose(basis, source_basis, rtol=0, atol=1e-12)
              and np.allclose(fractional, source_fractional, rtol=0, atol=1e-12)
              and np.allclose(fractional @ basis, source_cartesian, rtol=0, atol=1e-8),
              "Public geometry source hash and saved basis/site coordinates independently verified", stageId=stage_id)
        check(all(exported["species"] == [{"element": species["element"], "occupancy": species["occu"]} for species in original_site["species"]]
                  for exported, original_site in zip(geometry["sites"], original["sites"])), "Public species match source site species", stageId=stage_id)
        nearest = math.inf
        for i in range(atoms):
            for j in range(i + 1, atoms):
                delta = fractional[i] - fractional[j]
                delta -= np.rint(delta)
                nearest = min(nearest, np.linalg.norm((translations + delta) @ basis, axis=1).min())
        check((atoms < 2 and geometry["minimumPeriodicDistanceAngstrom"] is None)
              or atoms >= 2 and near(nearest, geometry["minimumPeriodicDistanceAngstrom"], 1e-8),
              "Independent periodic nearest-site distance agrees", stageId=stage_id)
        parent_id = stage["parentStageId"]
        if parent_id is not None:
            check(parent_id in stages and stages[parent_id]["candidateId"] == stage["candidateId"]
                  and stage["recordedParentSourceId"] == stages[parent_id]["sourceId"],
                  "Recorded stage parent has same entity and exact source identity", stageId=stage_id)
            parent_hash = sources[stage["recordedParentSourceId"]]["sha256"]
            evidence_objects = []
            for reference in stage["evidence"]:
                file = sources[reference["sourceId"]]["absolutePath"]
                if file.suffix.lower() == ".json":
                    evidence_objects.append(strict_json(file))
            if stage["stage"] == "model_relaxed":
                check(any(item.get("source_structure_sha256") == parent_hash for item in evidence_objects),
                      "Original model result independently proves exact source-parent hash", stageId=stage_id)
            elif stage["stage"] == "accepted_dft":
                check(any(item.get("provenance", {}).get("source_geometry_sha256") == parent_hash for item in evidence_objects),
                      "Original QE result independently proves exact source-parent hash", stageId=stage_id)
        check(stage["dftValidation"]["newStableMaterialEstablished"] is False
              and stage["dftValidation"]["fullHullEstablished"] is False
              and stage["symmetry"]["newSymmetryInferencePerformed"] is False,
              "Geometry display does not invent stability or symmetry inference", stageId=stage_id)
        if stage["stage"] == "accepted_dft":
            accepted.append(stage)
            check(all(stage["dftValidation"][key] is True for key in ("terminalSCFAccepted", "stationarityAccepted", "finiteSensitivityAccepted")),
                  "Accepted QE stage requires all three scientific gates", stageId=stage_id)
            original_qe = [strict_json(sources[reference["sourceId"]]["absolutePath"])
                           for reference in stage["evidence"]
                           if sources[reference["sourceId"]]["absolutePath"].name == "result.json"]
            parent_hash = sources[stage["recordedParentSourceId"]]["sha256"]
            check(len(original_qe) == 1 and original_qe[0]["provenance"]["source_geometry_sha256"] == parent_hash
                  and original_qe[0]["result"]["n_atoms"] == atoms
                  and near(original_qe[0]["result"]["total_energy_eV"] / atoms, stage["energy"]["value"]),
                  "Original QE result binds input-source hash, physical atoms and normalized energy for all accepted cells", stageId=stage_id)
        elif stage["stage"] == "model_relaxed":
            original_models = [strict_json(sources[reference["sourceId"]]["absolutePath"])
                               for reference in stage["evidence"]
                               if sources[reference["sourceId"]]["absolutePath"].name == "result.json"]
            check(len(original_models) == 1 and original_models[0]["final_structure_sha256"] == stage["sourceSha256"]
                  and original_models[0]["atoms"] == atoms
                  and near(original_models[0]["energy_total_eV"] / atoms, stage["energy"]["value"]),
                  "Original model result binds final-source hash, physical atoms and normalized energy", stageId=stage_id)
        if stage["energy"] is not None:
            check(math.isfinite(stage["energy"]["value"]) and stage["energy"]["unit"] == "eV/atom"
                  and bool(stage["energy"]["engine"]) and bool(stage["energy"]["settingsScope"]),
                  "Stage energy has engine, unit and settings scope", stageId=stage_id)
            if stage["stage"] == "model_relaxed":
                check(near(stage["energy"]["value"], model_results[stage["candidateId"]]["chgnetEnergyEVPerAtom"]),
                      "Model-stage energy agrees with model table", stageId=stage_id)
            elif stage["stage"] == "accepted_dft":
                check(near(stage["energy"]["value"], qe_results[stage["dftValidation"]["jobId"]]["energyEVPerAtom"]),
                      "Accepted QE-stage energy agrees with accepted job table", stageId=stage_id)
        fallback = stage["fallbackFigureLogicalName"]
        fallback_files.add(fallback)
        check(fallback in assets and assets[fallback].stat().st_size < 100_000,
              "Each saved stage has a small actual-geometry fallback asset", stageId=stage_id)
    check(len(nonorthogonal) > 0 and set(nonorthogonal) == set(index["validation"]["nonOrthogonalStageIds"]),
          "Actual nonorthogonal stages exercise coordinate convention", stageIds=nonorthogonal)
    check(len(accepted) == 3, "Exactly three accepted QE geometry stages")
    check(len(fallback_files) == 26, "Every saved stage has its own explicitly identified fallback")
    check(stages["qe_source_reference_mgo_mp1265--accepted_dft"]["geometry"]["actualAtoms"] == 2
          and stages["qe_source_reference_mgo_mp1265--accepted_dft"]["parentStageId"] is None,
          "Two-atom accepted MgO reference has no fabricated eight-atom model parent")
    known = stages["phase1_mgo_attempt_000--accepted_dft"]
    check(known["geometry"]["actualAtoms"] == 8 and known["parentStageId"] == "phase1_mgo_attempt_000--model_relaxed",
          "Accepted generated MgO has proven eight-atom model parent")
    excluded = [stage for stage in stages.values() if stage["eligibility"]["excluded"]]
    check(len(excluded) == 1 and excluded[0]["geometry"]["actualAtoms"] == 12
          and excluded[0]["eligibility"]["exactCellEligible"] is False,
          "Twelve-atom excluded draw retains ineligibility independently of six-atom prototype")
    evidence = index["evidenceOnly"]
    check(len(evidence) == 1 and evidence[0]["acceptedTerminalStageId"] is None
          and evidence[0]["energy"] is None, "Incomplete perturbation is evidence only with no terminal stage/energy")
    for candidate in index["candidates"]:
        check(candidate["defaultStageId"] in candidate["stageIds"]
              and all(stage_id in stages and stages[stage_id]["candidateId"] == candidate["candidateId"] for stage_id in candidate["stageIds"]),
              "Candidate stage/default availability resolves", candidateId=candidate["candidateId"])
    return {"entities": 14, "stages": 26, "nonorthogonalStages": len(nonorthogonal), "acceptedQeStages": 3}


def run():
    manifest, data, assets, public_sources = validate_release()
    sources = validate_originals(public_sources)
    counts = {"replay": validate_replay(data), "uncertainty": validate_uncertainty(data),
              "generation": validate_generation(data), "dft": validate_dft(data),
              "structures": validate_geometry(data, sources, assets)}
    summary = data["summary.json"]
    theme, methods = data["theme.json"], data["methods.json"]
    check(all(policy in theme["policyLabels"] and policy in theme["policyColours"]
              for policy in data["replay/curves.json"]["policies"]),
          "Every replay policy has a consistent public label and colour")
    check(all(stage["stage"] in theme["statusLabels"] for stage in data["structures/index.json"]["stages"]),
          "Every actual saved-stage enum has a public status label, including the excluded draw")
    check(all(item["url"] is None and item["status"] == "not_published"
              for item in methods["externalPublicationLinks"]),
          "Unpublished repository, writeup and video links remain explicitly unavailable")
    check(methods["liveScientificCompute"] is False and methods["target"]["freshQETargetCompatible"] is False,
          "Methods preserve recorded-only execution and historical/fresh-energy separation")
    check(summary["newStableMaterialEstablished"] is False and summary["numericalStudyFrozen"] is True
          and summary["newExperimentsInWebsiteExport"] == 0, "Summary preserves frozen numerical scope")
    check(all(near(row["charged"] + row["remaining"], row["cap"]) for row in summary["budgets"]),
          "Public budget arithmetic independently reconciles")
    for relative, expected in strict_json(WEBSITE / "research_sources.json")["baseline_integrity"].items():
        check(digest(ROOT / relative) == expected, "Original numerical baseline unchanged after validation", source=relative)
    return {"dataReleaseId": manifest["dataReleaseId"], "studyId": manifest["studyId"],
            "manifestSha256": digest(PUBLIC / "manifest.json"), "logicalJsonDatasets": len(data),
            "binaryAssets": len(assets), "publicSources": len(public_sources), "counts": counts}


def main():
    summary, error = {}, None
    try:
        summary = run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        CHECKS.append({"check": "Validation completed without unclassified exception", "passed": False, "error": error})
    report = {"schemaVersion": 1, "status": "passed" if error is None else "failed",
              "checkedAt": datetime.now().astimezone().isoformat(),
              "scope": "Independent public export and saved-source arithmetic validation; no scientific inference or new experiments",
              **summary, "checksPassed": sum(row["passed"] for row in CHECKS),
              "checksTotal": len(CHECKS), "error": error, "checks": CHECKS}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, allow_nan=False, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "checks"}, ensure_ascii=False, indent=2))
    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
