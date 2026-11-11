"""Read-only Phase 6 analysis of frozen generation and final structures.

This script does not import a predictor, generator, relaxation worker or QE
runner. All numerical values come from saved structures and accepted results.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
import math
import os
from pathlib import Path
import sys
import warnings

import numpy as np
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Composition, Structure
from pymatgen.io.cif import CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase6/structures"
sys.path.insert(0, str(ROOT / "scripts"))
from phase2_formula_rules import normalized_counts

CHECKS = []
SOURCES = {}


def path(value):
    candidate = Path(value)
    return candidate if candidate.is_absolute() else ROOT / candidate


def sha(value):
    source = path(value)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    result = digest.hexdigest()
    SOURCES[source.relative_to(ROOT).as_posix()] = result
    return result


def read(value):
    sha(value)
    return json.loads(path(value).read_text(encoding="utf-8"))


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True,
                                     allow_nan=False) + "\n", encoding="utf-8")


def check(value, message):
    CHECKS.append({"check": message, "passed": bool(value)})


def close(a, b, tolerance=1e-8):
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=tolerance)


def counts(structure):
    return {key: int(round(value)) for key, value in
            structure.composition.get_el_amt_dict().items()}


def structure(value):
    source = path(value)
    if source.suffix == ".json":
        return Structure.from_dict(read(value))
    sha(value)
    return CifParser(source, frac_tolerance=0).parse_structures(primitive=False)[0]


def minimum_distance(crystal):
    distances = crystal.distance_matrix.copy()
    np.fill_diagonal(distances, np.inf)
    pair = float(distances.min()) if len(crystal) > 1 else float("inf")
    reduced = crystal.lattice.get_lll_reduced_lattice()
    images = reduced.get_points_in_sphere([[0., 0., 0.]], [0., 0., 0.],
                                          min(reduced.abc) + 1e-7)
    self_image = min(float(item[1]) for item in images if float(item[1]) > 1e-8)
    return min(pair, self_image)


def sg(crystal, symprec=.01):
    return int(SpacegroupAnalyzer(crystal, symprec=symprec,
                                 angle_tolerance=5).get_space_group_number())


def save_csv(name, rows):
    if not rows:
        raise ValueError(f"Refusing empty table {name}")
    fields = list(rows[0])
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (json.dumps(value, sort_keys=True)
                                   if isinstance(value, (dict, list)) else value)
                             for key, value in row.items()})


def generation_analysis(protocol):
    primary = read("artifacts/phase4/generation/summary.json")
    extra = read("artifacts/phase4/generation/supplementary_mgo/summary.json")
    run_plan = read("artifacts/phase4/generation/run_plan.json")
    cases = {row["run_id"]: row for row in
             run_plan["reused_cohorts"] + run_plan["new_cohorts"]}
    matcher = StructureMatcher(**protocol["deduplication"])
    draw_rows, cohort_rows, diagnostic_rows = [], [], []
    cohort_cache = {}

    for cohort in primary["cohorts"] + extra["arms"]:
        supplementary = cohort in extra["arms"]
        scope = "supplementary_topup_only" if supplementary else "primary_first8"
        case = ({"exact_counts": {"Mg": 4, "O": 4}, "spacegroup": cohort["spacegroup"]}
                if supplementary else cases[cohort["run_id"]])
        expected = case["exact_counts"]
        representatives = []
        fresh_rows = []
        for item in cohort["results"]:
            candidate_id = item["candidate_id"]
            crystal = structure(item["structure_json"])
            check(sha(item["structure_json"]) == item["structure_sha256"],
                  f"Saved source structure hash {candidate_id}")
            observed = counts(crystal)
            exact = observed == expected and len(crystal) == sum(expected.values())
            distance = minimum_distance(crystal)
            geometry = bool(math.isfinite(crystal.volume) and crystal.volume > 0
                            and distance >= protocol["minimum_distance_angstrom"])
            valid = exact and geometry and len(crystal) <= protocol["expanded_atom_cap"]
            same_formula = normalized_counts(observed) == normalized_counts(expected)
            diagnostic = same_formula and geometry and len(crystal) <= 20
            measured = sg(crystal)
            duplicate = next((prior_id for prior_id, prior in representatives
                              if matcher.fit(crystal, prior)), None) if valid else None
            if valid and duplicate is None:
                representatives.append((candidate_id, crystal))
            check(observed == item["counts"] and len(crystal) == item["n_atoms"],
                  f"Actual expanded composition/count {candidate_id}")
            check(valid == item["audited_valid"], f"Exact frozen validity {candidate_id}")
            check(measured == item["measured_spacegroup"], f"Saved sampled symmetry {candidate_id}")
            check(diagnostic == item["reduced_formula_geometry_valid_within_atom_cap_diagnostic_only"],
                  f"Diagnostic classification {candidate_id}")
            check(duplicate == item["audited_duplicate_of"], f"Frozen topology deduplication {candidate_id}")
            row = {"candidate_id": candidate_id, "scope": scope,
                   "kind": "control" if supplementary else cohort["kind"],
                   "control": "mgo_rocksalt" if supplementary else cohort.get("control"),
                   "arm": cohort.get("arm"), "formula": "Mg4O4" if supplementary else cohort["formula"],
                   "requested_spacegroup": case["spacegroup"], "measured_spacegroup": measured,
                   "n_atoms": len(crystal), "requested_n_atoms": sum(expected.values()),
                   "actual_counts": observed, "exact_counts_match": exact,
                   "minimum_periodic_distance_angstrom": distance, "geometry_valid": geometry,
                   "valid": valid, "duplicate_of": duplicate,
                   "correct_ratio_geometry_within_cap_diagnostic_only": diagnostic,
                   "different_cell_count_diagnostic_excluded": diagnostic and not exact,
                   "larger_cell_diagnostic_excluded": diagnostic and not exact and len(crystal) > sum(expected.values()),
                   "source_structure": Path(item["structure_json"]).as_posix(),
                   "source_sha256": sha(item["structure_json"])}
            fresh_rows.append(row)
            if row["kind"] == "new_composition" and diagnostic and not exact:
                check(len(crystal) > sum(expected.values()),
                      "New-formula non-exact ratio diagnostic has strictly larger cell " + candidate_id)
                diagnostic_rows.append(row)
        check(len(fresh_rows) == (4 if supplementary else 8),
              f"Unchanged draw denominator {scope}/{cohort.get('run_id', cohort.get('arm'))}")
        check(sum(row["valid"] for row in fresh_rows) == cohort["valid_count"],
              f"Frozen valid total {scope}/{cohort.get('run_id', cohort.get('arm'))}")
        check(len(representatives) == cohort["valid_unique_count"],
              f"Frozen unique total {scope}/{cohort.get('run_id', cohort.get('arm'))}")
        draw_rows.extend(fresh_rows)
        cohort_rows.append({"scope": scope, "kind": fresh_rows[0]["kind"],
                            "control": fresh_rows[0]["control"], "arm": cohort.get("arm"),
                            "formula": fresh_rows[0]["formula"], "draws": len(fresh_rows),
                            "exact_valid": sum(row["valid"] for row in fresh_rows),
                            "exact_valid_unique": len(representatives),
                            "valid_requested_spacegroup": sum(row["valid"] and
                                                              row["measured_spacegroup"] == row["requested_spacegroup"]
                                                              for row in fresh_rows),
                            "excluded_larger_cell_diagnostics": sum(row["larger_cell_diagnostic_excluded"]
                                                                     for row in fresh_rows)})
        cohort_cache[(scope, fresh_rows[0]["control"], cohort.get("arm"))] = fresh_rows

    controls = [row for row in cohort_rows if row["kind"] == "control" and row["scope"] == "primary_first8"]
    formulas = [row for row in cohort_rows if row["kind"] == "new_composition"]
    check(len(draw_rows) == 88 and len(controls) == 4, "All 88 actual draws retained; four primary control arms")
    check(sum(row["draws"] for row in formulas) == 48 and len(formulas) == 6,
          "Six fixed new formulas and 48 unchanged primary draws")
    check(sum(row["exact_valid"] for row in formulas) == 0, "No admitted fresh transformer new-formula candidate")
    check(len(diagnostic_rows) == 12, "Twelve larger-cell diagnostics remain excluded")
    check({row["formula"] for row in diagnostic_rows} == {row["formula"] for row in formulas},
          "Larger-cell diagnostics cover all six attempted formulas")
    save_csv("generation_draws.csv", draw_rows)
    save_csv("generation_cohorts.csv", cohort_rows)
    save_csv("excluded_larger_cell_diagnostics.csv", diagnostic_rows)
    return {"actual_transformer_draws": 88, "primary_control_arms": controls,
            "supplementary_control_arms": [row for row in cohort_rows if row["scope"] != "primary_first8"],
            "new_formula_cohorts": formulas, "new_formula_primary_draws": 48,
            "new_formula_exact_valid": 0, "excluded_larger_cell_diagnostics": len(diagnostic_rows),
            "primary_yield_denominators_unchanged": True,
            "scope": "Sampling group contrast within one fixed trained architecture; no architecture causality claim"}, diagnostic_rows


def catalog_analysis():
    manifest = read("artifacts/phase2/catalogs/catalog_manifest.json")
    frozen_inventory = read("artifacts/phase2/catalogs/artifact_inventory.json")
    frozen_hashes = {item["path"]: item["sha256"] for item in frozen_inventory["files"]}
    geometry_index = "data/catalogs/control_geometry_candidates.json"
    check(sha(geometry_index) == frozen_hashes[geometry_index],
          "Pinned complete same-composition control geometry index")
    known_controls = read(geometry_index)
    expected_control_ids = {key: {row["material_id"] for row in known_controls
                                  if normalized_counts(row["counts"]) == key}
                            for key in {normalized_counts(row["counts"]) for row in known_controls}}
    for item in manifest["files"].values():
        check(sha(item["path"]) == item["sha256"], "Pinned raw snapshot " + item["path"])
    selection = read("artifacts/phase2/compositions/selection.json")
    targets = selection["selected"]
    catalogs = {}
    catalog_counts = {}
    control_coverage = {}
    for name, expected in (("mp", 154718), ("wbm", 256963)):
        source = f"data/catalogs/{name}_full_compositions.jsonl"
        check(sha(source) == frozen_hashes[source], "Pinned complete composition index " + name)
        observed, ids, population = set(), set(), 0
        target_ids = {normalized_counts(row["counts"]): [] for row in targets}
        control_ids = {key: set() for key in expected_control_ids}
        all_control_ids = {key: set() for key in expected_control_ids}
        with path(source).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                key = normalized_counts(row["counts"])
                population += 1
                observed.add(key)
                ids.add(row["material_id"])
                if key in target_ids:
                    target_ids[key].append(row["material_id"])
                if key in control_ids:
                    all_control_ids[key].add(row["material_id"])
                    if name == "mp" and row["n_sites"] <= 30:
                        control_ids[key].add(row["material_id"])
        check(population == expected and len(ids) == expected, f"Complete {name} population and unique IDs")
        check(len(observed) == manifest[name + "_unique_compositions"], f"Complete {name} unique compositions")
        if name == "mp":
            check(control_ids == expected_control_ids,
                  "Saved control geometries exhaust same-composition MP entries with original source <=30 sites")
            for key, ids in all_control_ids.items():
                control_coverage[Composition(dict(key)).reduced_formula] = {
                    "full_snapshot_composition_entries": len(ids),
                    "saved_geometries_tested": len(control_ids[key]),
                    "saved_geometry_source_site_cap": 30,
                    "not_tested_larger_source_geometry_ids": sorted(ids - control_ids[key])}
        catalogs[name] = target_ids
        catalog_counts[name] = {"records": population, "unique_compositions": len(observed)}
    rows = []
    for target in targets:
        key = normalized_counts(target["counts"])
        record = {"formula": target["formula"], "counts": target["counts"],
                  "mp_matching_composition_records": len(catalogs["mp"][key]),
                  "wbm_matching_composition_records": len(catalogs["wbm"][key]),
                  "absent_from_both_pinned_snapshots": not catalogs["mp"][key] and not catalogs["wbm"][key],
                  "global_composition_novelty_established": False,
                  "generator_pretraining_OOD_established": False,
                  "DFT_confirmed_stability": False}
        check(record["absent_from_both_pinned_snapshots"] == target["new_to_both_checked_catalogs"],
              "Independent frozen-catalog composition absence " + target["formula"])
        rows.append(record)
    save_csv("composition_novelty.csv", rows)
    return {"catalog_populations": catalog_counts, "composition_rechecks": rows,
            "saved_control_geometry_coverage": control_coverage,
            "raw_snapshot_hashes_verified": True,
            "index_scope": "All rows in hash-pinned complete composition indexes linked to audited raw archives",
            "MP_snapshot": manifest["mp_source"],
            "WBM_snapshot": "Full released WBM 256963-row snapshot, not the experiment's filtered replay subset",
            "scope": "Absence in these two historical catalogs only; no current/global novelty claim and no proof of generator-pretraining OOD"}


def final_structure_analysis(protocol):
    summary = read("artifacts/phase5/chgnet/summary.json")
    saved_catalog = read("data/catalogs/control_geometry_candidates.json")
    catalog_geometries = [(row["material_id"], normalized_counts(row["counts"]),
                           Structure.from_dict(row["structure"])) for row in saved_catalog]
    check(Counter(row["formula"] for row in saved_catalog) == {"MgO": 15, "TiO2": 34},
          "Saved <=30-source-site same-composition MP geometry subset: 15 MgO and 34 TiO2")
    matcher = StructureMatcher(**protocol["deduplication"])
    rows, structures = [], {}
    for item in summary["results"]:
        result = read(item["result_path"])
        final = structure(result["final_structure"])
        check(sha(result["final_structure"]) == result["final_structure_sha256"],
              "Final relaxed source hash " + item["candidate_id"])
        formula = normalized_counts(counts(final))
        matching = [material_id for material_id, key, prior in catalog_geometries
                    if key == formula and matcher.fit(final, prior)]
        measured = sg(final)
        check(len(final) == result["atoms"], "Final atom normalization " + item["candidate_id"])
        check(close(result["energy_total_eV"] / len(final), result["energy_eV_per_atom"]),
              "Saved energy divided by actual expanded sites " + item["candidate_id"])
        check(measured == result["final_spacegroup"], "Final measured relaxed group " + item["candidate_id"])
        check(result["converged"] and result["final_filter_fmax_eV_A"] <= .05,
              "Saved CHGNet cell-filter convergence " + item["candidate_id"])
        rows.append({"candidate_id": item["candidate_id"], "role": item["role"],
                     "control": item.get("control"), "arm": item.get("arm"),
                     "actual_atoms": len(final), "final_formula": final.composition.reduced_formula,
                     "CHGNet_energy_eV_per_atom": result["energy_eV_per_atom"],
                     "optimizer_steps": result["optimizer_steps"], "converged": result["converged"],
                     "filter_fmax_eV_per_angstrom": result["final_filter_fmax_eV_A"],
                     "final_spacegroup_symprec_0p01": measured,
                     "matches_pinned_MP_same_composition_geometry_ids": matching,
                     "same_composition_MP_geometries_tested": sum(key == formula for _, key, _ in catalog_geometries),
                     "global_structure_novelty_established": False,
                     "new_stable_material_established": False,
                     "source_final_structure": Path(result["final_structure"]).as_posix(),
                     "source_sha256": sha(result["final_structure"])})
        structures[item["candidate_id"]] = final
    check(len(rows) == 11 and sum(row["role"] == "prototype" for row in rows) == 4
          and sum(row["role"] == "same_composition_reference" for row in rows) == 3,
          "All eleven selected relaxed structures, four prototypes and three references")
    check(sum(bool(row["matches_pinned_MP_same_composition_geometry_ids"])
              for row in rows if row["role"] == "symmetry" and row["arm"] == "nontrivial") == 2,
          "Both selected symmetry-conditioned controls recover known catalog phases")
    pair_rows = []
    for control, scope in (("mgo_rocksalt", "supplementary_primary_plus_topup_pool"),
                           ("tio2_rutile", "primary_first8_per_arm")):
        pair = [row for row in rows if row["role"] == "symmetry" and row["control"] == control]
        high = next(row for row in pair if row["arm"] == "nontrivial")
        low = next(row for row in pair if row["arm"] == "p1")
        difference = low["CHGNet_energy_eV_per_atom"] - high["CHGNet_energy_eV_per_atom"]
        pair_rows.append({"control": control, "scope": scope, "quota_per_arm": 1,
                          "nontrivial_candidate_id": high["candidate_id"], "p1_candidate_id": low["candidate_id"],
                          "P1_minus_nontrivial_CHGNet_eV_per_atom": difference,
                          "relaxed_pair_structure_match": bool(matcher.fit(structures[high["candidate_id"]],
                                                                           structures[low["candidate_id"]])),
                          "energy_distribution_established": False, "DFT_stability_comparison": False})
    lookup = {row["candidate_id"]: row for row in rows}
    anatase_minus_rutile = lookup["reference_anatase"]["CHGNet_energy_eV_per_atom"] - lookup["reference_rutile"]["CHGNet_energy_eV_per_atom"]
    check(close(anatase_minus_rutile, summary["reference_anatase_minus_rutile_eV_atom"]),
          "TiO2 reference ordering reproduced within one composition")
    prototype_rows = []
    for item in protocol["deterministic_prototype_candidates"]:
        parent_input = structure(item["cif"])
        check(sha(item["cif"]) == item["cif_sha256"], "Frozen prepared prototype " + item["candidate_id"])
        check(normalized_counts(counts(parent_input)) == normalized_counts(Composition(item["target_formula"]).get_el_amt_dict()),
              "Prepared prototype target composition " + item["candidate_id"])
        result = lookup[item["candidate_id"]]
        check(counts(parent_input) == counts(structures[item["candidate_id"]]),
              "Prototype relaxation preserves full atom counts " + item["candidate_id"])
        prototype_rows.append({"candidate_id": item["candidate_id"], "parent_material_id": item["parent_material_id"],
                               "target_formula": item["target_formula"], "atoms": len(parent_input),
                               "initial_geometry_valid": minimum_distance(parent_input) >= .75,
                               "CHGNet_converged": result["converged"],
                               "final_spacegroup": result["final_spacegroup_symprec_0p01"],
                               "CHGNet_energy_eV_per_atom": result["CHGNet_energy_eV_per_atom"],
                               "fresh_DFT_submitted": False, "stable_material_established": False})
    save_csv("relaxed_structures.csv", rows)
    save_csv("symmetry_energy_pairs.csv", pair_rows)
    save_csv("prototype_baselines.csv", prototype_rows)
    return {"relaxed_selections": len(rows), "CHGNet_converged": len(rows),
            "new_relaxation_launches_in_phase6": 0, "structures": rows, "symmetry_pairs": pair_rows,
            "prototype_baselines": prototype_rows, "reference_anatase_minus_rutile_CHGNet_eV_per_atom": anatase_minus_rutile,
            "matcher_settings": protocol["deduplication"],
            "energy_scope": "Within-composition CHGNet predictions only; raw cross-composition energies do not define stability",
            "novelty_scope": "Saved original-source <=30-site MP geometry subset tested: 15 of 23 MgO entries and 34 of 44 TiO2 entries. Larger-source-cell geometries not tested; unmatched outputs do not establish global novelty"}, structures


def dft_analysis():
    old = read("artifacts/phase3/qe/summary.json")
    anchor = read("artifacts/phase4/qe/summary.json")
    perturbation = read("artifacts/phase5/qe/summary.json")
    candidate_job = old["accepted_candidate_job_id"]
    reference_job = old["accepted_reference_job_id"]
    candidate_base = f"artifacts/phase3/qe/{candidate_job}"
    reference_base = f"artifacts/phase3/qe/{reference_job}"
    candidate = structure(candidate_base + "/final_geometry.json")
    reference = structure(reference_base + "/final_geometry.json")
    candidate_result = read(candidate_base + "/result.json")["result"]
    reference_result = read(reference_base + "/result.json")["result"]
    matcher = StructureMatcher(ltol=.01, stol=.01, angle_tol=.5,
                               primitive_cell=True, scale=False, attempt_supercell=True)
    equivalent = bool(matcher.fit(candidate, reference))
    displacement = matcher.get_rms_dist(candidate, reference)
    difference = candidate_result["energy_eV_per_atom"] - reference_result["energy_eV_per_atom"]
    check(equivalent, "Accepted generated DFT MgO matches known independently relaxed reference")
    check(sg(candidate) == sg(reference) == 225, "Both accepted DFT MgO structures have rock-salt group 225")
    check(close(difference, old["known_MgO_comparison"]["raw_candidate_minus_reference_eV_per_atom"]),
          "Same-composition accepted DFT energy difference reproduced")
    check(abs(difference) <= .01 and old["full_numerical_convergence"],
          "Known DFT control within fixed comparison tolerance and finite numerical checks")
    inventory = read("artifacts/phase2/dft/reference_inventory_all_profiles.json")
    completed = set(anchor["completed_original_source_reference_ids"])
    coverage, inventory_rows = {}, []
    for system, expected, accepted in (("Ca-Mg-O", 161, 2), ("Mg-O", 57, 1)):
        records = [row for row in inventory["records"] if system in row["memberships"]]
        actual = [row for row in records if row["material_id"] in completed]
        check(len(records) == expected and len(actual) == accepted,
              "Complete frozen competitor inventory and accepted reference coverage " + system)
        coverage[system] = {"frozen_entries": len(records), "accepted_original_source_references": len(actual),
                            "accepted_material_ids": [row["material_id"] for row in actual],
                            "uncomputed_original_source_entries": len(records) - len(actual),
                            "full_inventory_hull_established": False}
        for row in records:
            check(sha(row["execution_geometry_path"]) == row["execution_geometry_sha256"],
                  "Frozen original-source competitor geometry " + row["material_id"] + "/" + system)
            inventory_rows.append({"system": system, "material_id": row["material_id"],
                                   "formula": row["reduced_formula"], "original_source_atoms": row["source_n_sites"],
                                   "accepted_fresh_QE_reference": row["material_id"] in completed,
                                   "source_geometry": row["execution_geometry_path"],
                                   "source_sha256": row["execution_geometry_sha256"]})
    check(not perturbation["full_frozen_inventory_hull_established"] and not perturbation["fresh_CaMg2O3_candidate_submitted"],
          "No hull completion or post-outcome prototype promotion")
    check(perturbation["accepted_perturbation_job_id"] is None and perturbation["perturbation_validation_incomplete"],
          "Time-limited MgO perturbation remains unaccepted")
    save_csv("competitor_inventory_coverage.csv", inventory_rows)
    result = {"known_control": {"formula": "MgO", "candidate_job_id": candidate_job,
                                "reference_job_id": reference_job, "candidate_atoms": len(candidate),
                                "reference_atoms": len(reference), "structure_match": equivalent,
                                "normalized_RMS_and_max_distance": list(displacement),
                                "candidate_spacegroup": sg(candidate), "reference_spacegroup": sg(reference),
                                "candidate_energy_eV_per_atom": candidate_result["energy_eV_per_atom"],
                                "reference_energy_eV_per_atom": reference_result["energy_eV_per_atom"],
                                "candidate_minus_reference_eV_per_atom": difference,
                                "comparison_tolerance_eV_per_atom": .01, "energy_ordering_resolved": False,
                                "finite_cutoff_and_kpoint_validation_passed": True,
                                "outcome": "Known rock-salt recovery, numerically indistinguishable energy"},
              "competitor_coverage": coverage, "perturbation_validation_incomplete": True,
              "perturbation_accepted_terminal_geometry": False, "phonon_check_performed": False,
              "local_minimum_proven": False, "new_DFT_confirmed_stable_materials": 0,
              "new_QE_jobs_in_phase6": 0,
              "scope": "Static PBE known-control comparison, not full thermodynamic stability or finite-temperature stability"}
    return result, candidate


def plot_structures(structures, dft_crystal, diagnostics):
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    initial_path = "artifacts/phase1/generator/structure_000.json"
    excluded = next(row for row in diagnostics if row["formula"] == "CaMg2O3")
    panels = [
        ("a  Generated MgO control", structure(initial_path),
         "CrystalFormer; 8 atoms; SG 225\nKnown composition, before relaxation", initial_path, "generated"),
        ("b  DFT MgO recovery", dft_crystal,
         "Accepted PBE result; known rock-salt\nMatches reference; no new material", "artifacts/phase3/qe/p3_candidate_mgo_fallback_90/final_geometry.json", "DFT"),
        ("c  CaMg2O3 prototype", structures["prototype_CaMg2O3"],
         "CHGNet relaxed; 6 atoms; SG 164\nNo fresh DFT or stability validation", "artifacts/phase5/chgnet/prototype_CaMg2O3/final.json", "CHGNet"),
        ("d  Excluded CaMg2O3 draw", structure(excluded["source_structure"]),
         f"Correct ratio; {excluded['n_atoms']} atoms vs 6 required\nExcluded from frozen exact-cell experiment", excluded["source_structure"], "generated_excluded")]
    colors = {"O": "#d34a45", "Mg": "#7563ae", "Ca": "#d99337"}
    fig = plt.figure(figsize=(14, 5.0), facecolor="white")
    provenance = []
    for index, (title, crystal, caption, source, state) in enumerate(panels, start=1):
        ax = fig.add_subplot(1, 4, index, projection="3d")
        vectors = crystal.lattice.matrix
        corners = np.asarray(list(product([0, 1], repeat=3)), float)
        for a, corner in enumerate(corners):
            for b in range(a + 1, len(corners)):
                if np.count_nonzero(corner != corners[b]) == 1:
                    points = np.asarray([corner, corners[b]]) @ vectors
                    ax.plot(*points.T, color="#89939c", lw=.85, alpha=.8)
        coords = (crystal.frac_coords % 1.) @ vectors
        for symbol in sorted(set(site.specie.symbol for site in crystal)):
            points = coords[[site.specie.symbol == symbol for site in crystal]]
            ax.scatter(*points.T, s=68 if symbol == "O" else 130, color=colors[symbol],
                       edgecolor="white", linewidth=.7, depthshade=True)
        bounds = np.vstack((corners @ vectors, coords))
        low, high = bounds.min(axis=0), bounds.max(axis=0)
        span = max(float((high-low).max()), 1)
        center = (high+low)/2
        for setter, value in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), center):
            setter(value-span*.56, value+span*.56)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=22, azim=-58)
        ax.set_axis_off()
        ax.set_title(title, fontsize=11, weight="bold", pad=10)
        ax.text2D(.5, -.025, caption, transform=ax.transAxes, ha="center", va="top", fontsize=9)
        provenance.append({"panel": index, "title": title, "structure_path": source,
                           "sha256": sha(source), "state": state, "actual_atoms": len(crystal),
                           "caption": caption})
    legend = [Line2D([0], [0], marker="o", color="w", markerfacecolor=colors[symbol],
                     markersize=8, label=symbol) for symbol in ("Mg", "Ca", "O")]
    fig.legend(handles=legend, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(.5, .052))
    fig.suptitle("Frozen structure examples and their validation status", fontsize=15, weight="bold", y=.98)
    fig.text(.5, .013, "Actual saved unit cells; ball sizes are illustrative. Catalog absence and MLIP convergence do not establish a stable material.",
             ha="center", fontsize=9, color="#444444")
    fig.subplots_adjust(left=.015, right=.985, top=.89, bottom=.22, wspace=.02)
    for suffix in ("png", "pdf"):
        fig.savefig(OUT / f"representative_structures.{suffix}", dpi=220, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    write("figure_provenance.json", {"panels": provenance, "periodic_images_added": False,
                                     "new_inference_or_geometry_optimization": False})
    return "artifacts/phase6/structures/representative_structures.png"


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    OUT.mkdir(parents=True, exist_ok=True)
    sha(Path(__file__))
    protocol = read("artifacts/phase2/compositions/generation_protocol.json")
    generation, diagnostics = generation_analysis(protocol)
    composition = catalog_analysis()
    relaxed, structures = final_structure_analysis(protocol)
    dft, dft_crystal = dft_analysis()
    shortlist = read("artifacts/phase4/selection/fresh_shortlist.json")
    check(len(shortlist["formulas"]) == 6 and all(not row["selected"] for row in shortlist["formulas"]),
          "Original empty new-formula transformer shortlist preserved")
    figure = plot_structures(structures, dft_crystal, diagnostics)
    check(path(figure).stat().st_size > 10000, "Representative actual-structure PNG generated")
    check((OUT / "representative_structures.pdf").stat().st_size > 5000,
          "Standalone exportable actual-structure PDF generated")
    summary = {"phase": 6, "status": "complete", "completed_utc": datetime.now(timezone.utc).isoformat(),
               "generation": generation, "composition_novelty": composition, "relaxed_structures": relaxed,
               "DFT_validation": dft, "representative_structure_figure": figure,
               "new_generator_draws": 0, "new_predictor_fits_or_predictions": 0,
               "new_CHGNet_launches": 0, "new_QE_jobs": 0,
               "claim_limits": ["Within-architecture sampling contrast only; one energy pair per composition",
                                "MgO topup results supplementary; primary first-eight denominators unchanged",
                                "New-to-reference composition means absent only from two pinned historical catalogs",
                                "P1 geometry unmatched to pinned same-composition subset does not prove global novelty",
                                "Prototype CHGNet convergence and absolute raw energies are not formation energies or hull stability",
                                "No fresh candidate CaMg2O3 QE result; 159 primary and 56 fallback reference entries uncomputed",
                                "Known MgO recovery is not discovery; perturbation incomplete; no phonon local-minimum proof"],
               "audit_path": "artifacts/phase6/structures/audit.json"}
    write("summary.json", summary)
    write("source_hashes.json", {"files": [{"path": name, "sha256": digest}
                                           for name, digest in sorted(SOURCES.items())]})
    failed = [row for row in CHECKS if not row["passed"]]
    write("audit.json", {"status": "passed" if not failed else "failed", "phase": 6,
                         "checks_total": len(CHECKS), "checks_passed": len(CHECKS)-len(failed),
                         "failed_checks": failed, "checks": CHECKS,
                         "script_sha256": sha(Path(__file__)), "new_scientific_oracle_calls": 0,
                         "source_hash_count": len(SOURCES), "summary_sha256": sha(OUT / "summary.json")})
    print(json.dumps({"status": "passed" if not failed else "failed", "checks": len(CHECKS),
                      "failed": failed, "pair_energies": relaxed["symmetry_pairs"],
                      "final_catalog_matches": [{"id": row["candidate_id"], "matches": row["matches_pinned_MP_same_composition_geometry_ids"]}
                                                for row in relaxed["structures"]]}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
