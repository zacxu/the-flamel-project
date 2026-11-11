"""Curate frozen research tables for the website; never execute research code.

Only selected historical queries are published. Evaluation targets, raw oracle
tables, local paths and arbitrary dictionary contents are deliberately absent.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
import math
import re
from statistics import mean, stdev

from export_common import ExportContext


U = "artifacts/phase6/uncertainty/"
S = "artifacts/phase6/structures/"
E = "artifacts/phase6/evidence/"
SEEDS = list(range(20261022, 20261027))
POLICIES = ["full", "quality", "quality_diversity", "random", "uncertainty"]


def number(value, *, nullable=False):
    if value == "" or value is None:
        if nullable:
            return None
        raise ValueError("Missing required numeric value")
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric measurement")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite numeric value")
    return result


def integer(value, *, nullable=False):
    result = number(value, nullable=nullable)
    if result is None:
        return None
    if int(result) != result:
        raise ValueError(f"Non-integral integer field: {value!r}")
    return int(result)


def boolean(value):
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError(f"Not an explicit boolean: {value!r}")


def text_or_none(value):
    return value or None


def counts(value):
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, dict) or not result:
        raise ValueError("Expected nonempty element counts")
    return {str(k): integer(v) for k, v in result.items()}


def source_ref(ctx, path):
    """Resolve registered provenance without copying an internal filesystem path."""
    if not path:
        return None
    try:
        return ctx.source_id(path.replace("\\", "/"))
    except (KeyError, ValueError):
        return None


def statistics(values):
    values = [number(v) for v in values]
    return {"mean": mean(values), "sampleStd": stdev(values),
            "min": min(values), "max": max(values), "values": values}


def close(a, b):
    return math.isclose(number(a), number(b), rel_tol=1e-10, abs_tol=1e-12)


def convert_rows(ctx, path, specification):
    rows = ctx.read_csv(path)
    return [{out: parser(row[source]) for out, (source, parser) in specification.items()}
            for row in rows]


def point(row):
    return {"seed": integer(row["seed"]), "policy": row["policy"],
            "queries": integer(row["queries"]),
            "nearStableHits": integer(row["near_stable_hits"]),
            "referenceHullHits": integer(row["reference_hull_hits"]),
            "chemicalSystemCoverage": integer(row["chemical_system_coverage"])}


def export_replay(ctx, frozen):
    curves = [point(r) for r in ctx.read_csv(U + "learning_curves.csv")]
    endpoints = [dict(point(r), precisionAt50=number(r["precision_at_50"]))
                 for r in ctx.read_csv(U + "policy_endpoints.csv")]
    journal = ctx.read_csv("artifacts/phase4/replay/query_journal_all_seeds.csv")
    needed = {r["material_id"] for r in journal}
    # The complete local metadata table is joined and discarded, never exported.
    selected_rows = [r for r in ctx.read_csv("artifacts/phase2/features/row_metadata.csv")
                     if r["material_id"] in needed]
    selected = {r["material_id"]: r for r in selected_rows}
    ctx.check(len(journal) == 1250 and len(needed) == 720,
              "Historical query population", events=len(journal), selectedMaterials=len(needed))
    ctx.check(set(selected) == needed and len(selected_rows) == len(needed),
              "All selected query metadata resolve exactly once")
    ctx.check(all(r["formula"] and r["reduced_formula"] and r["chemical_system"]
                  and integer(r["n_sites"]) > 0 for r in selected_rows),
              "Selected-only formula and chemical metadata are complete")
    ctx.check(len(curves) == 125 and len(endpoints) == 25,
              "Replay curve and endpoint counts")
    curve_index = {(r["seed"], r["policy"], r["queries"]): r for r in curves}
    endpoint_index = {(r["seed"], r["policy"]): r for r in endpoints}
    grouped = defaultdict(list)
    for row in journal:
        grouped[integer(row["seed"]), row["policy"]].append(row)
    ctx.check(set(grouped) == {(s, p) for s in SEEDS for p in POLICIES},
              "Exactly five seeds by five policies")
    for seed in SEEDS:
        histories = []
        for policy in POLICIES:
            rows = sorted(grouped[seed, policy], key=lambda r: integer(r["query_number"]))
            ctx.check([integer(r["query_number"]) for r in rows] == list(range(1, 51)),
                      "Replay query order", seed=seed, policy=policy)
            ctx.check(len({r["material_id"] for r in rows}) == 50,
                      "No replacement within policy history", seed=seed, policy=policy)
            batches, systems = [], set()
            near, hull = 0, 0
            for round_number in range(1, 6):
                batch = [r for r in rows if integer(r["round"]) == round_number]
                ctx.check(len(batch) == 10, "Ten queries per saved batch",
                          seed=seed, policy=policy, round=round_number)
                metadata = {(r["decision_utc"], r["reveal_utc"],
                             r["decision_sha256"], r["reveal_sha256"]) for r in batch}
                ctx.check(len(metadata) == 1, "Batch decision and reveal identity",
                          seed=seed, policy=policy, round=round_number)
                decision_utc, reveal_utc, decision_hash, reveal_hash = next(iter(metadata))
                ctx.check(datetime.fromisoformat(decision_utc) <= datetime.fromisoformat(reveal_utc)
                          and all(re.fullmatch(r"[0-9a-f]{64}", h) for h in [decision_hash, reveal_hash]),
                          "Decision precedes reveal with valid identity hashes",
                          seed=seed, policy=policy, round=round_number)
                queries = []
                for row in batch:
                    metadata_row = selected[row["material_id"]]
                    label = number(row["label_eV_atom"])
                    near_hit, hull_hit = label <= 0.05, label <= 0.0
                    near += near_hit
                    hull += hull_hit
                    systems.add(metadata_row["chemical_system"])
                    score = number(row["score"], nullable=True)
                    ctx.check((score is None) == (policy == "random"),
                              "Only random selection has null acquisition score",
                              seed=seed, policy=policy, query=integer(row["query_number"]))
                    queries.append({
                        "queryNumber": integer(row["query_number"]),
                        "materialId": row["material_id"],
                        "formula": metadata_row["formula"],
                        "reducedFormula": metadata_row["reduced_formula"],
                        "chemicalSystem": metadata_row["chemical_system"],
                        "atoms": integer(metadata_row["n_sites"]),
                        "role": row["role"], "score": score,
                        "predictedMeanEVPerAtom": number(row["predicted_mean_eV_atom"]),
                        "calibratedRadiusEVPerAtom": number(row["calibrated_radius_eV_atom"]),
                        "diversityAtSelection": number(row["diversity_at_selection"]),
                        "revealedLabelEVPerAtom": label,
                        "nearStableHit": near_hit, "referenceHullHit": hull_hit})
                derived = {"queries": round_number * 10, "nearStableHits": near,
                           "referenceHullHits": hull, "chemicalSystemCoverage": len(systems)}
                saved = curve_index[seed, policy, round_number * 10]
                ctx.check(all(derived[k] == saved[k] for k in derived),
                          "Selected-history cumulative counts match frozen learning curve",
                          seed=seed, policy=policy, round=round_number, computed=derived)
                batches.append({"round": round_number,
                                "decision": {"utc": decision_utc, "sha256": decision_hash},
                                "reveal": {"utc": reveal_utc, "sha256": reveal_hash},
                                "queries": queries, "cumulativeAfterReveal": derived})
            endpoint = endpoint_index[seed, policy]
            ctx.check(all(endpoint[k] == derived[k] for k in derived)
                      and close(endpoint["precisionAt50"], near / 50),
                      "Selected-history endpoint matches frozen endpoint",
                      seed=seed, policy=policy)
            histories.append({"policy": policy, "batches": batches})
        ctx.add_json(f"replay/seed-{seed}.json", {
            "schemaVersion": 1, "seed": seed,
            "scope": "Replay of recorded retrospective decisions; labels reveal only after each saved batch.",
            "sourceIds": [ctx.source_id("artifacts/phase4/replay/query_journal_all_seeds.csv"),
                          ctx.source_id("artifacts/phase2/features/row_metadata.csv")],
            "histories": histories})
    policy_statistics = {}
    metric_names = {"nearStableHits": "near_stable_hits", "referenceHullHits": "reference_hull_hits",
                    "chemicalSystemCoverage": "chemical_system_coverage", "precisionAt50": "precision_at_50"}
    for policy in POLICIES:
        records = [endpoint_index[s, policy] for s in SEEDS]
        policy_statistics[policy] = {}
        for public, internal in metric_names.items():
            recomputed = statistics([r[public] for r in records])
            recorded = frozen["policy_endpoint_aggregates"][policy][internal]
            ctx.check(all(close(recomputed[k], recorded[old]) for k, old in
                          [("mean", "mean"), ("sampleStd", "sample_std"), ("min", "min"), ("max", "max")])
                      and all(close(a, b) for a, b in zip(recomputed["values"], recorded["values"])),
                      "Policy aggregate recomputed from selected histories", policy=policy, metric=public)
            policy_statistics[policy][public] = recomputed
    differences = [endpoint_index[s, "full"]["nearStableHits"] -
                   endpoint_index[s, "quality"]["nearStableHits"] for s in SEEDS]
    ctx.check(differences == [-9, -8, -19, -10, -13], "Negative paired result retained")
    ctx.add_json("replay/curves.json", {
        "schemaVersion": 1, "seeds": SEEDS, "policies": POLICIES,
        "thresholds": {"nearStableEVPerAtom": 0.05, "referenceHullEVPerAtom": 0,
                       "comparison": "less_than_or_equal", "label": "historical signed hull distance"},
        "zeroQueryOrigin": {"queries": 0, "nearStableHits": 0, "referenceHullHits": 0,
                            "chemicalSystemCoverage": 0, "precision": None,
                            "origin": "derived_zero_state",
                            "label": "Zero-query display origin; no acquired labels"},
        "points": curves, "endpoints": endpoints,
        "policyStatistics": policy_statistics, "fullMinusQualityHits": statistics(differences),
        "sourceIds": [ctx.source_id(U + "learning_curves.csv"),
                      ctx.source_id(U + "policy_endpoints.csv")]})
    return policy_statistics, statistics(differences)


def export_uncertainty(ctx, frozen):
    base = {"seed": ("seed", integer), "policy": ("policy", str), "queries": ("queries", integer)}
    metrics = convert_rows(ctx, U + "evaluation_metrics.csv", dict(base,
        rows=("n", integer), maeEVPerAtom=("MAE_eV_atom", number),
        rmseEVPerAtom=("RMSE_eV_atom", number),
        disagreementAbsoluteErrorSpearman=("Spearman_disagreement_absolute_error", number),
        interval90EmpiricalCoverage=("interval_90_empirical_coverage", number),
        meanIntervalWidthEVPerAtom=("mean_interval_width_eV_atom", number),
        calibrationScale=("calibration_q", number)))
    risks = convert_rows(ctx, U + "risk_coverage.csv", dict(base,
        requestedRetainedFraction=("requested_retained_fraction", number),
        retainedRows=("retained_rows", integer), actualRetainedFraction=("actual_retained_fraction", number),
        maeEVPerAtom=("MAE_eV_atom", number), allRowsMaeEVPerAtom=("all_rows_MAE_eV_atom", number),
        maeRelativeToAllRows=("MAE_relative_to_all_rows", number),
        interval90EmpiricalCoverage=("interval_90_empirical_coverage", number)))
    deciles = convert_rows(ctx, U + "uncertainty_deciles.csv", dict(base,
        decile=("uncertainty_decile", integer), rows=("n", integer),
        meanDisagreementEVPerAtom=("mean_disagreement_eV_atom", number),
        minDisagreementEVPerAtom=("min_disagreement_eV_atom", number),
        maxDisagreementEVPerAtom=("max_disagreement_eV_atom", number),
        maeEVPerAtom=("MAE_eV_atom", number),
        interval90EmpiricalCoverage=("interval_90_empirical_coverage", number),
        meanIntervalWidthEVPerAtom=("mean_interval_width_eV_atom", number)))
    roles = convert_rows(ctx, U + "full_policy_role_diagnostics.csv", {
        "seed": ("seed", integer), "role": ("role", str), "queries": ("queries", integer),
        "nearStableHits": ("near_stable_hits", integer), "precision": ("precision", number),
        "referenceHullHits": ("reference_hull_hits", integer),
        "meanPredictedMeanEVPerAtom": ("mean_predicted_mean_eV_atom", number),
        "meanCalibratedRadiusEVPerAtom": ("mean_calibrated_radius_eV_atom", number),
        "meanDiversityDistance": ("mean_diversity_distance", number)})
    ctx.check([len(metrics), len(risks), len(deciles), len(roles)] == [130, 300, 300, 10],
              "All uncertainty diagnostic rows retained")
    expected_snapshots = {(s, "initial_shared", 0) for s in SEEDS} | {
        (s, p, q) for s in SEEDS for p in POLICIES for q in [10, 20, 30, 40, 50]}
    ctx.check({(r["seed"], r["policy"], r["queries"]) for r in metrics} == expected_snapshots
              and all(r["rows"] == 3418 for r in metrics),
              "Shared initial snapshots occur once per seed and full evaluation grid is present")
    endpoint_grid = {(s, "initial_shared", 0) for s in SEEDS} | {
        (s, p, 50) for s in SEEDS for p in POLICIES}
    ctx.check({(r["seed"], r["policy"], r["queries"], round(r["requestedRetainedFraction"], 1))
               for r in risks} == {(*key, i / 10) for key in endpoint_grid for i in range(1, 11)},
              "Risk coverage includes every saved endpoint and all ten retained fractions")
    ctx.check(all(r["retainedRows"] == math.ceil(3418 * r["requestedRetainedFraction"])
                  and close(r["actualRetainedFraction"], r["retainedRows"] / 3418)
                  and close(r["maeRelativeToAllRows"], r["maeEVPerAtom"] / r["allRowsMaeEVPerAtom"])
                  for r in risks), "Actual retained rows, fractions and risk ratios reconcile")
    ctx.check({(r["seed"], r["policy"], r["queries"], r["decile"]) for r in deciles} == {
        (*key, i) for key in endpoint_grid for i in range(1, 11)},
        "Uncertainty deciles retain all endpoint bins")
    for seed, policy, queries in sorted(endpoint_grid):
        rows = [r for r in deciles if (r["seed"], r["policy"], r["queries"]) == (seed, policy, queries)]
        ctx.check(sum(r["rows"] for r in rows) == 3418
                  and all(r["minDisagreementEVPerAtom"] <= r["meanDisagreementEVPerAtom"]
                          <= r["maxDisagreementEVPerAtom"] for r in rows),
                  "Decile population and disagreement bounds reconcile", seed=seed, policy=policy)
    ctx.check({(r["seed"], r["role"]) for r in roles} == {
        (seed, role) for seed in SEEDS for role in ["conservative", "optimistic"]}
              and all(r["queries"] == (35 if r["role"] == "conservative" else 15)
                      and close(r["precision"], r["nearStableHits"] / r["queries"]) for r in roles),
              "Full-policy role counts and precision preserve frozen seven-three allocation")
    aggregate_fields = {"maeEVPerAtom": "MAE_eV_atom", "rmseEVPerAtom": "RMSE_eV_atom",
        "disagreementAbsoluteErrorSpearman": "Spearman_disagreement_absolute_error",
        "interval90EmpiricalCoverage": "interval_90_empirical_coverage",
        "meanIntervalWidthEVPerAtom": "mean_interval_width_eV_atom", "calibrationScale": "calibration_q"}
    endpoint_aggregates = {}
    for policy in ["initial_shared"] + POLICIES:
        rows = sorted([r for r in metrics if r["policy"] == policy and
                       r["queries"] == (0 if policy == "initial_shared" else 50)], key=lambda r: r["seed"])
        ctx.check([r["seed"] for r in rows] == SEEDS, "Five uncertainty endpoint snapshots", policy=policy)
        endpoint_aggregates[policy] = {}
        for name, internal in aggregate_fields.items():
            stat = statistics([r[name] for r in rows])
            old = frozen["evaluation_endpoint_aggregates"][policy][internal]
            ctx.check(close(stat["mean"], old["mean"]) and close(stat["sampleStd"], old["sample_std"]),
                      "Uncertainty endpoint aggregate matches frozen summary", policy=policy, metric=name)
            endpoint_aggregates[policy][name] = stat
    ctx.add_json("uncertainty.json", {
        "schemaVersion": 1, "evaluationMetrics": metrics, "riskCoverage": risks,
        "deciles": deciles, "roles": roles,
        "summary": {"endpointAggregates": endpoint_aggregates,
                    "evaluationRowsPerSeed": integer(frozen["untouched_evaluation_rows_per_seed"]),
                    "featureScope": frozen["feature_scope"],
                    "riskCoverageMethod": frozen["risk_coverage_method"],
                    "decileMethod": frozen["uncertainty_bins_method"],
                    "roleScope": frozen["full_policy_role_scope"],
                    "wholeChemicalSystemSeparationWithinSeed": boolean(frozen["whole_chemical_system_separation_within_every_seed"]),
                    "crossSeedPopulationsOverlap": True,
                    "nominalIntervalCoverage": 0.9,
                    "newModelFits": 0, "newOracleQueries": 0,
                    "limits": frozen["scientific_limits"]},
        "sourceIds": [ctx.source_id(U + name) for name in ["summary.json", "evaluation_metrics.csv",
                      "risk_coverage.csv", "uncertainty_deciles.csv", "full_policy_role_diagnostics.csv"]]})


def draw_row(ctx, row):
    return {
        "candidateId": row["candidate_id"], "scope": row["scope"], "kind": row["kind"],
        "control": text_or_none(row["control"]), "arm": text_or_none(row["arm"]), "formula": row["formula"],
        "requestedSpacegroup": integer(row["requested_spacegroup"], nullable=True),
        "measuredSpacegroup": integer(row["measured_spacegroup"], nullable=True),
        "atoms": integer(row["n_atoms"]), "requestedAtoms": integer(row["requested_n_atoms"]),
        "actualCounts": counts(row["actual_counts"]), "exactCountsMatch": boolean(row["exact_counts_match"]),
        "minimumPeriodicDistanceAngstrom": number(row["minimum_periodic_distance_angstrom"], nullable=True),
        "geometryValid": boolean(row["geometry_valid"]), "valid": boolean(row["valid"]),
        "duplicateOf": text_or_none(row["duplicate_of"]),
        "correctRatioGeometryWithinCapDiagnosticOnly": boolean(row["correct_ratio_geometry_within_cap_diagnostic_only"]),
        "differentCellCountDiagnosticExcluded": boolean(row["different_cell_count_diagnostic_excluded"]),
        "largerCellDiagnosticExcluded": boolean(row["larger_cell_diagnostic_excluded"]),
        "sourceId": ctx.source_id(S + "generation_draws.csv"),
        "geometrySourceSha256": row["source_sha256"]}


def export_generation(ctx, frozen):
    cohorts = convert_rows(ctx, S + "generation_cohorts.csv", {
        "scope": ("scope", str), "kind": ("kind", str), "control": ("control", text_or_none),
        "arm": ("arm", text_or_none), "formula": ("formula", str), "draws": ("draws", integer),
        "exactValid": ("exact_valid", integer), "exactValidUnique": ("exact_valid_unique", integer),
        "validRequestedSpacegroup": ("valid_requested_spacegroup", integer),
        "excludedLargerCellDiagnostics": ("excluded_larger_cell_diagnostics", integer)})
    draws = [draw_row(ctx, r) for r in ctx.read_csv(S + "generation_draws.csv")]
    excluded = [draw_row(ctx, r) for r in ctx.read_csv(S + "excluded_larger_cell_diagnostics.csv")]
    prototypes = convert_rows(ctx, S + "prototype_baselines.csv", {
        "candidateId": ("candidate_id", str), "parentMaterialId": ("parent_material_id", str),
        "targetFormula": ("target_formula", str), "atoms": ("atoms", integer),
        "initialGeometryValid": ("initial_geometry_valid", boolean), "chgnetConverged": ("CHGNet_converged", boolean),
        "finalSpacegroup": ("final_spacegroup", integer), "chgnetEnergyEVPerAtom": ("CHGNet_energy_eV_per_atom", number),
        "freshDftSubmitted": ("fresh_DFT_submitted", boolean), "stableMaterialEstablished": ("stable_material_established", boolean)})
    pairs = convert_rows(ctx, S + "symmetry_energy_pairs.csv", {
        "control": ("control", str), "scope": ("scope", str), "quotaPerArm": ("quota_per_arm", integer),
        "nontrivialCandidateId": ("nontrivial_candidate_id", str), "p1CandidateId": ("p1_candidate_id", str),
        "p1MinusNontrivialChgnetEVPerAtom": ("P1_minus_nontrivial_CHGNet_eV_per_atom", number),
        "relaxedPairStructureMatch": ("relaxed_pair_structure_match", boolean),
        "energyDistributionEstablished": ("energy_distribution_established", boolean),
        "dftStabilityComparison": ("DFT_stability_comparison", boolean)})
    novelty = convert_rows(ctx, S + "composition_novelty.csv", {
        "formula": ("formula", str), "counts": ("counts", counts),
        "mpMatchingCompositionRecords": ("mp_matching_composition_records", integer),
        "wbmMatchingCompositionRecords": ("wbm_matching_composition_records", integer),
        "absentFromBothPinnedSnapshots": ("absent_from_both_pinned_snapshots", boolean),
        "globalCompositionNoveltyEstablished": ("global_composition_novelty_established", boolean),
        "generatorPretrainingOodEstablished": ("generator_pretraining_OOD_established", boolean),
        "dftConfirmedStability": ("DFT_confirmed_stability", boolean)})
    relaxed = []
    for row in ctx.read_csv(S + "relaxed_structures.csv"):
        matches = json.loads(row["matches_pinned_MP_same_composition_geometry_ids"])
        if not isinstance(matches, list) or not all(isinstance(value, str) for value in matches):
            raise ValueError("Catalog geometry matches must be a string array")
        relaxed.append({
            "candidateId": row["candidate_id"], "role": row["role"],
            "control": text_or_none(row["control"]), "arm": text_or_none(row["arm"]),
            "atoms": integer(row["actual_atoms"]), "finalFormula": row["final_formula"],
            "chgnetEnergyEVPerAtom": number(row["CHGNet_energy_eV_per_atom"], nullable=True),
            "optimizerSteps": integer(row["optimizer_steps"], nullable=True),
            "converged": boolean(row["converged"]),
            "filterFmaxEVPerAngstrom": number(row["filter_fmax_eV_per_angstrom"], nullable=True),
            "finalSpacegroup": integer(row["final_spacegroup_symprec_0p01"], nullable=True),
            "spacegroupSymprecAngstrom": 0.01,
            "matchesPinnedMpSameCompositionGeometryIds": matches,
            "sameCompositionMpGeometriesTested": integer(row["same_composition_MP_geometries_tested"]),
            "globalStructureNoveltyEstablished": boolean(row["global_structure_novelty_established"]),
            "newStableMaterialEstablished": boolean(row["new_stable_material_established"]),
            "sourceId": ctx.source_id(S + "relaxed_structures.csv"),
            "geometrySourceId": source_ref(ctx, row["source_final_structure"]),
            "geometrySourceSha256": row["source_sha256"]})
    ctx.check([len(cohorts), len(draws), len(excluded), len(prototypes), len(pairs), len(novelty)]
              == [12, 88, 12, 4, 2, 6], "Generation table counts preserved")
    ctx.check(len(relaxed) == 11 and len({r["candidateId"] for r in relaxed}) == 11
              and all(r["converged"] for r in relaxed),
              "All eleven selected model result records remain accessible")
    ctx.check(sum(r["role"] == "symmetry" for r in relaxed) == 4
              and sum(r["role"] == "prototype" for r in relaxed) == 4
              and sum(r["role"] == "same_composition_reference" for r in relaxed) == 3,
              "Model result roles preserve symmetry, prototype and reference counts")
    relaxed_by_id = {r["candidateId"]: r for r in relaxed}
    ctx.check(all(r["geometrySourceId"] is not None
                  and (r["filterFmaxEVPerAngstrom"] is None or r["filterFmaxEVPerAngstrom"] <= 0.05)
                  and not r["globalStructureNoveltyEstablished"]
                  and not r["newStableMaterialEstablished"] for r in relaxed),
              "Selected model results preserve verified sources, force criterion and novelty limits")
    ctx.check(all(close(p["p1MinusNontrivialChgnetEVPerAtom"],
                        relaxed_by_id[p["p1CandidateId"]]["chgnetEnergyEVPerAtom"] -
                        relaxed_by_id[p["nontrivialCandidateId"]]["chgnetEnergyEVPerAtom"])
                  for p in pairs), "Symmetry energy differences match individual model records")
    ctx.check(all(close(p["chgnetEnergyEVPerAtom"], relaxed_by_id[p["candidateId"]]["chgnetEnergyEVPerAtom"])
                  and p["chgnetConverged"] == relaxed_by_id[p["candidateId"]]["converged"]
                  for p in prototypes), "Prototype summary matches individual model records")
    new_draws = [d for d in draws if d["kind"] == "new_composition"]
    ctx.check(len(new_draws) == 48 and sum(d["valid"] for d in new_draws) == 0,
              "All fresh new-formula exact-count failures retained")
    by_id = {d["candidateId"]: d for d in draws}
    ctx.check(len(by_id) == 88 and all(e == by_id[e["candidateId"]] for e in excluded),
              "Excluded diagnostics are unchanged subset of actual draws")
    for cohort in cohorts:
        members = [d for d in draws if all(d[k] == cohort[k] for k in ["scope", "kind", "control", "arm", "formula"])]
        ctx.check(len(members) == cohort["draws"]
                  and sum(d["valid"] for d in members) == cohort["exactValid"]
                  and sum(d["valid"] and d["duplicateOf"] is None for d in members) == cohort["exactValidUnique"],
                  "Cohort counts recomputed from actual emitted draws", cohort=cohort)
    catalog = frozen["composition_novelty"]
    populations = {name: {"records": integer(value["records"]),
                          "uniqueCompositions": integer(value["unique_compositions"])}
                   for name, value in catalog["catalog_populations"].items()}
    ctx.add_json("generation.json", {
        "schemaVersion": 1, "cohorts": cohorts, "draws": draws,
        "excluded": excluded, "excludedScope": "12 new-formula larger-cell diagnostics; control diagnostic rows remain in draws.",
        "prototypes": prototypes, "relaxedStructures": relaxed,
        "modelEnergyScope": frozen["relaxed_structures"]["energy_scope"],
        "modelNoveltyScope": frozen["relaxed_structures"]["novelty_scope"],
        "symmetryPairs": pairs, "compositionNovelty": novelty,
        "catalogScope": {"mpSnapshot": catalog["MP_snapshot"], "wbmSnapshot": catalog["WBM_snapshot"],
                         "populations": populations, "scope": catalog["scope"]},
        "summary": {"actualCrystalFormerDraws": 88, "newFormulaDraws": 48, "newFormulaExactValid": 0,
                    "modelSelectedStructures": 11, "prototypeBaselines": 4,
                    "anataseMinusRutileChgnetEVPerAtom": number(frozen["relaxed_structures"]["reference_anatase_minus_rutile_CHGNet_eV_per_atom"]),
                    "primaryYieldDenominatorsUnchanged": True,
                    "scope": frozen["generation"]["scope"], "limits": frozen["claim_limits"]},
        "sourceIds": [ctx.source_id(S + name) for name in ["summary.json", "generation_cohorts.csv",
                      "generation_draws.csv", "excluded_larger_cell_diagnostics.csv", "prototype_baselines.csv", "relaxed_structures.csv",
                      "symmetry_energy_pairs.csv", "composition_novelty.csv"]]})


def membership(row):
    return {"inventorySystem": row["inventory_system"], "materialId": row["material_id"],
            "formula": row["formula"], "chemicalSystem": row["chemical_system"],
            "executionAtoms": integer(row["execution_n_sites"]),
            "spinReviewRequired": boolean(row["spin_review_required"]),
            "expensiveReferenceFlag": boolean(row["expensive_reference_flag"]),
            "elementalEndpointEntry": boolean(row["elemental_endpoint_entry"]),
            "acceptedFreshCompatibleQe": boolean(row["accepted_fresh_compatible_QE"]),
            "acceptedJobId": text_or_none(row["accepted_job_id"]), "status": row["status"],
            "blocksFullInventoryHull": boolean(row["blocks_full_inventory_hull"])}


def export_dft(ctx, frozen):
    jobs = []
    for row in ctx.read_csv(E + "fresh_DFT_evidence_table.csv"):
        jobs.append({"jobId": row["job_id"], "phase": integer(row["phase"]), "role": row["role"],
            "formula": row["formula"], "atoms": integer(row["n_atoms"]), "calculation": row["calculation"],
            "exitCode": integer(row["exit_code"], nullable=True), "jobDone": boolean(row["JOB_DONE"]),
            "terminalScfAccepted": boolean(row["terminal_SCF_accepted"]),
            "stationaryAtThisSetting": boolean(row["stationary_at_this_setting"]),
            "acceptedWithFinalGeometrySensitivity": boolean(row["accepted_with_final_geometry_sensitivity"]),
            "energyEVPerAtom": number(row["energy_eV_per_atom"], nullable=True),
            "maxForceEVPerAngstrom": number(row["max_force_eV_A"], nullable=True),
            "maxFullStressKbar": number(row["max_full_stress_kbar"], nullable=True),
            "cutoffRy": number(row["cutoff_Ry"]), "densityCutoffRy": number(row["density_cutoff_Ry"]),
            "kMesh": [integer(x) for x in row["k_mesh"].split("x")],
            "elapsedWallSeconds": number(row["elapsed_wall_seconds"]), "evidenceLevel": row["evidence_level"],
            "sourceId": ctx.source_id(E + "fresh_DFT_evidence_table.csv"),
            "resultSourceId": source_ref(ctx, row["source_result"])})
    references = [membership(r) for r in ctx.read_csv(E + "reference_inventory_completeness.csv")]
    missing = [membership(r) for r in ctx.read_csv(E + "missing_reference_inventory.csv")]
    accepted = [{"acceptedJobId": r["accepted_job_id"], "energyEVPerAtom": number(r["energy_eV_atom"]),
                 "maxForceEVPerAngstrom": number(r["force_eV_A"]), "maxFullStressKbar": number(r["full_stress_kbar"]),
                 "cutoffShiftEVPerAtom": number(r["cutoff_shift_eV_atom"]),
                 "kpointShiftEVPerAtom": number(r["kpoint_shift_eV_atom"])}
                for r in frozen["fresh_QE_relaxed_geometries_with_final_finite_checks"]]
    ctx.check([len(jobs), len(references), len(missing), len(accepted)] == [19, 218, 215, 3],
              "All DFT attempts, memberships and accepted geometries retained")
    ctx.check({r["acceptedJobId"] for r in accepted} ==
              {j["jobId"] for j in jobs if j["acceptedWithFinalGeometrySensitivity"]},
              "Three accepted geometry jobs remain distinct")
    ctx.check(len({r["materialId"] for r in references if r["acceptedFreshCompatibleQe"]}) == 2,
              "Three accepted geometries correspond to two source reference IDs")
    ctx.check(missing == [r for r in references if not r["acceptedFreshCompatibleQe"]],
              "Missing memberships are full inventory complement")
    coverage = {}
    for system, recorded in frozen["reference_coverage"].items():
        members = [r for r in references if r["inventorySystem"] == system]
        unavailable = [r for r in members if not r["acceptedFreshCompatibleQe"]]
        coverage[system] = {"frozenEntries": len(members), "acceptedFreshCompatibleQe": len(members) - len(unavailable),
                            "missing": len(unavailable), "fullInventoryComplete": False,
                            "missingSpinReviewEntries": sum(r["spinReviewRequired"] for r in unavailable),
                            "missingElementalEntries": sum(r["elementalEndpointEntry"] for r in unavailable)}
        ctx.check(all(coverage[system][new] == recorded[old] for new, old in [
            ("frozenEntries", "frozen_entries"), ("acceptedFreshCompatibleQe", "accepted_fresh_compatible_QE"),
            ("missing", "missing"), ("missingSpinReviewEntries", "missing_spin_review_entries"),
            ("missingElementalEntries", "missing_elemental_entries")]),
            "Reference coverage recomputed without double-counting memberships", system=system)
    decision = frozen["numerical_decision"]
    ctx.add_json("dft.json", {
        "schemaVersion": 1, "jobs": jobs, "referenceMemberships": references,
        "missingMemberships": missing, "acceptedGeometries": accepted, "coverage": coverage,
        "membershipScope": "Systems overlap: 218 inventory memberships are not 218 unique materials. Three accepted geometries include two calculations for known MgO and one source CaO reference.",
        "finiteCheckScope": frozen["finite_check_scope"],
        "knownMgoControl": {"candidateMinusReferenceEVPerAtom": number(frozen["known_MgO_candidate_minus_reference_eV_atom"]),
                            "energyOrderingResolved": boolean(frozen["known_MgO_energy_ordering_resolved"]),
                            "matchesReferenceStructure": boolean(frozen["known_MgO_final_reference_structure_match"])},
        "reaction": {"equation": frozen["primary_reaction"]["equation"],
                     "anchorWeightedEnergyEVPerAtom": number(frozen["primary_reaction"]["anchor_weighted_energy_eV_atom"]),
                     "candidateEnergyAvailable": False, "reactionEnergyAvailable": False},
        "perturbationValidationComplete": boolean(frozen["perturbation_validation_complete"]),
        "phononCalculationPerformed": boolean(frozen["phonon_calculation_performed"]),
        "fullHullEstablished": boolean(frozen["full_hull_established"]),
        "newStableMaterialEstablished": boolean(frozen["new_stable_material_established"]),
        "decision": {"decision": decision["decision"], "reason": decision["reason"],
                     "requiredAllowedUnfinishedJobs": integer(decision["required_allowed_unfinished_job_count"]),
                     "newNumericalJobsPhase6": integer(decision["new_numerical_jobs_dispatched_phase6"]),
                     "stopUtc": decision["numerical_stop_utc_unchanged"],
                     "earlyClosureDoesNotRelaxFailedChecks": boolean(decision["early_closure_does_not_relax_failed_checks"])},
        "sourceIds": [ctx.source_id(E + name) for name in ["summary.json", "fresh_DFT_evidence_table.csv",
                      "reference_inventory_completeness.csv", "missing_reference_inventory.csv"]]})


def export_tables(ctx: ExportContext) -> None:
    uncertainty = ctx.read_json(U + "summary.json")
    structures = ctx.read_json(S + "summary.json")
    evidence = ctx.read_json(E + "summary.json")
    policy_statistics, difference_statistics = export_replay(ctx, uncertainty)
    export_uncertainty(ctx, uncertainty)
    export_generation(ctx, structures)
    export_dft(ctx, evidence)
    claims = convert_rows(ctx, E + "claim_matrix.csv", {
        "claim": ("claim", str), "status": ("status", str), "scope": ("scope", str), "limitation": ("limitation", str)})
    budgets = convert_rows(ctx, E + "budget_reconciliation.csv", {
        "lane": ("lane", str), "cap": ("cap", number), "charged": ("charged", number),
        "remaining": ("remaining", number), "unit": ("unit", str), "interpretation": ("interpretation", str)})
    ctx.check(len(claims) == 10 and len(budgets) == 4, "Claim and budget rows retained")
    ctx.check(all(close(r["charged"] + r["remaining"], r["cap"]) for r in budgets),
              "Public budget arithmetic reconciles")
    ctx.add_json("summary.json", {
        "schemaVersion": 1, "projectName": "The Flamel Project",
        "researchTitle": "Uncertainty-Aware, Symmetry-Constrained Crystal Discovery",
        "hypothesis": "Explicit predictive uncertainty during symmetry-constrained generation may improve stable, novel crystal discovery in underrepresented chemical spaces.",
        "studyStatus": "frozen_prototype", "demoMode": "recorded_evidence_replay",
        "newStableMaterialEstablished": False,
        "pipeline": ["Target composition", "Symmetry-conditioned CrystalFormer", "Exact-cell and geometry gates",
                     "Frozen property predictor and uncertainty", "Acquisition with diversity", "CHGNet relaxation",
                     "Bounded Quantum ESPRESSO validation", "Evidence and claim audit"],
        "counts": {"replaySeeds": 5, "policies": 5, "historicalQueryEvents": 1250,
                   "distinctSelectedHistoricalMaterials": 720, "evaluationSnapshots": 130,
                   "actualCrystalFormerDraws": 88, "newFormulaDraws": 48, "newFormulaExactValid": 0,
                   "excludedNewFormulaLargerCellDiagnostics": 12, "modelSelectedStructures": 11,
                   "prototypeBaselines": 4, "sameCompositionModelReferences": 3,
                   "qeAttempts": 19, "acceptedRelaxedQeGeometries": 3,
                   "acceptedOriginalSourceReferenceIds": 2, "consolidatedResearchChecksPassed": 3587},
        "policyStatistics": policy_statistics, "fullMinusQualityHits": difference_statistics,
        "findings": ["The full acquisition policy retrieved fewer near-stable historical labels than quality ranking in all five frozen splits.",
                     "Symmetry-conditioned control samples had higher primary exact-cell yield, with one relaxed energy pair per composition.",
                     "None of the 48 new-formula transformer draws passed the frozen exact-cell gate.",
                     "All four prototype baselines converged under CHGNet; convergence does not establish stability.",
                     "The generated MgO DFT result recovers a known rock-salt reference; the perturbation and full competitor inventory remain incomplete."],
        "scientificLimits": uncertainty["scientific_limits"] + structures["claim_limits"],
        "claims": claims, "budgets": budgets,
        "numericalStudyFrozen": True, "newExperimentsInWebsiteExport": 0,
        "sourceIds": [ctx.source_id(U + "summary.json"), ctx.source_id(S + "summary.json"),
                      ctx.source_id(E + "summary.json"), ctx.source_id(E + "claim_matrix.csv"),
                      ctx.source_id(E + "budget_reconciliation.csv")]})
