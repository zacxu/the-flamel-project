"""Freeze the Phase 2 DFT plan and audit templates. No executable is launched."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from ase.io import read
from pymatgen.core import Structure

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "phase2" / "dft"


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def save(name, data):
    (ART / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    inventory = json.loads((ART / "primary_reference_plan.json").read_text())
    fallback = json.loads((ART / "fallback_Mg-O_reference_plan.json").read_text())
    rows = inventory["records"]
    indexed = {row["material_id"]: row for row in rows}
    large_primary = sum(row["execution_n_sites"] > 20 for row in rows)
    large_fallback = sum(row["execution_n_sites"] > 20 for row in fallback["records"])
    max_source_sites = max(row["execution_n_sites"] for row in rows)
    selection_path = ROOT / "artifacts" / "phase2" / "compositions" / "selection.json"
    selection = json.loads(selection_path.read_text())
    selected = next(row for row in selection["selected"] if row["formula"] == "CaMg2O3")
    assert selected["new_to_both_checked_catalogs"]
    assert not selected["present_in_full_wbm"] and not selected["present_in_mp_snapshot"]
    anchors = [indexed["mp-2605"], indexed["mp-1265"]]
    assert [row["reduced_formula"] for row in anchors] == ["CaO", "MgO"]
    assert all(row["space_group_number_symprec_0p01"] == 225 for row in anchors)
    ledger_path = ROOT / "artifacts" / "phase1" / "qe" / "qe_jobs.jsonl"
    jobs = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    consumed = sum(row["elapsed_wall_seconds"] for row in jobs)
    protocol = {
        "functional": "PBE", "pseudopotential_library": "SSSP 1.3.0 PBE efficiency",
        "pseudopotential_rule": "Same checksum-identified file per element across every candidate/reference",
        "initial_common_ecutwfc_Ry": 50.0, "initial_common_ecutrho_Ry": 400.0,
        "cutoff_sensitivity_pairs_Ry": [[50, 400], [60, 480], [75, 600]],
        "initial_reciprocal_spacing_inv_angstrom": 0.60,
        "reciprocal_spacing_probe_inv_angstrom": [0.60, 0.45, 0.35],
        "k_grid_rule": "ceil(|reciprocal lattice vector including 2*pi| / spacing), at least 1; unshifted; never assume the starting mesh is converged",
        "conv_thr_Ry": 1e-8, "scf_must_converge": True, "electron_maxstep": 100,
        "forc_conv_thr_Ry_per_Bohr": 8e-4, "force_target_eV_per_angstrom": 0.0205688269904,
        "etot_conv_thr_Ry": 1e-5, "press_conv_thr_kbar": 0.5,
        "final_stress_acceptance": "For solids require both abs(scalar pressure)<=0.5 kbar AND max(abs(full3x3 stress tensor minus zero target))<=0.5 kbar; tighten/continue if either fails. A small hydrostatic trace alone does not establish shear convergence. Molecular fixed-box stress is not a solid acceptance test.",
        "solid_relaxation": "vc-relax, BFGS atomic and cell, target pressure zero, cell_dofree all",
        "final_constraints": "nosym=true, noinv=true; no imposed Wyckoff/space-group constraint; report any exception",
        "perturbation_check": "Where budget permits, deterministic seed 260022, 0.01-A random atomic displacement and 0.5-percent cell strain, followed by unconstrained re-relaxation; not a phonon test",
        "spin": {"balanced_CaMg2O3_candidate_and_MgO_CaO_anchors": "nonmagnetic starting hypothesis; if signs of metallicity or spin instability arise, review before acceptance",
                 "Mg_and_Ca_metals": "nonmagnetic starting hypothesis; cold smearing, degauss 0.01 Ry, probe 0.005 and 0.0025 Ry and comparable dense k meshes",
                 "isolated_O2": "triplet: nspin=2, total magnetization 2 muB, nbnd=8, fixed occupations, bond initialized 1.23 A",
                 "O2_box_sizes_A": [12, 15, 18],
                 "unknown_reference_phases": "Source moment >0.1muB OR O/cation counts other than balanced MO are flagged. Nonmagnetic templates alone do not establish a ground-spin reference; inspect and test appropriate spin/occupation branches before acceptance"},
        "numerical_acceptance": [
            "Electronic SCF, ionic force and (solid) pressure criteria must all pass; process exit and JOB DONE alone are insufficient",
            "QE forc_conv_thr is a component criterion; independently verify maximum atomic force-vector norm <=0.0205688269904 eV/A, tightening the continuation threshold if necessary",
            "At fixed final geometries, increase cutoffs and k density separately; require each reference/candidate used in a phase comparison to have recorded sensitivity checks",
            "After accepting final cutoff/k settings, recompute forces and the full stress tensor at those same settings. If max force-vector norm or any residual stress component fails acceptance, continue geometry/cell relaxation at the accepted settings and repeat checks before accepting the energy. Small energy shifts alone do not establish stationarity",
            "Target last-step changes in relevant per-atom and reaction energies <=0.005 eV/atom; extend refinement if not met and mark any untested value incomplete",
            "For O2, require vacuum/bond/spin/cutoff checks; solid oxygen catalog phases remain in the inventory and are not silently replaced by gas",
            "For metals inspect smearing/entropy contributions and demonstrate the final small-smearing result is insensitive within the stated energy tolerance",
            "Finite-k/cutoff sensitivity is a measured convergence diagnostic, not a rigorous total DFT error bound",
            "Do not label a sign as resolved when its margin is comparable to achieved sensitivity; use at least a 5-meV/atom guard band and enlarge it for larger observed shifts"
        ],
        "completeness": [
            "All 161 catalog entries are retained; none is excluded using source energy, hull distance or candidate outcome",
            "Every QE template uses its original source cell. Original site properties/magnetic-order metadata are retained in source JSON, but are not automatically converted to QE spin settings: moment/order-flagged references require explicit spin initialization/review before execution and acceptance. Primitive copies are informational and unverified. Any later reduction requires tight geometry/supercell equivalence and unambiguous property/magnetic-order mapping, otherwise retain the source cell",
            "This reference geometry inventory covers the named MP2022 snapshot only. WBM supplies the broader composition-absence check and replay, but additional WBM structures are not included in this fresh QE reference inventory. Even complete recalculation supports only the frozen MP-inventory statement, not all known/published phases",
            "A full frozen-inventory assessment needs compatible converged energies and reviewed spin/occupations for every required entry or a documented exact geometry equivalence",
            "An unfinished/failed/large/spin-ambiguous reference blocks a complete-inventory hull claim; list it explicitly",
            "Compare every completed generated structure with each other as well as against the reference-only hull",
            "MP/VASP stored energies, WBM targets and CHGNet energies are never substituted for fresh compatible QE reference energies"
        ],
        "executor_requirements": {"simultaneous_QE_jobs": 1, "OMP_NUM_THREADS": 4,
            "MKL_NUM_THREADS": 4, "OPENBLAS_NUM_THREADS": 1,
            "default_QE_max_seconds": 900, "outer_process_timeout_seconds": 930,
            "O2_max_seconds": 1200, "O2_outer_timeout_seconds": 1230,
            "resume_policy": "Preserve restart files and append every attempt, including failures, to the Phase1 QE job ledger",
            "additional_global_stop": "All numerical experiments stop at execution hour18",
            "path_staging": "Before execution create job-local scratch/pseudo directories and copy only checksum-verified required UPFs from the manifest"},
        "stable_claim_scope": "Approximate zero-temperature, target-zero-pressure PBE energetics under the documented oxygen convention; neither phonon stability, finite-temperature Gibbs stability nor experimental synthesizability"
    }
    save("numerical_protocol.json", protocol)
    budget = {"total_cumulative_qe_walltime_seconds": 21600,
              "consumed_QE_walltime_seconds": consumed, "remaining_QE_walltime_seconds": 21600-consumed,
              "existing_QE_jobs": len(jobs), "existing_QE_ledger_sha256": digest(ledger_path),
              "phase2_QE_jobs_executed": 0,
              "pilot_grounding": {"phase1_MgO_2_atom_SCF_wall_seconds": jobs[0]["elapsed_wall_seconds"],
                  "pilot_irreducible_k_points": 8, "pilot_threads": 4,
                  "limitation": "A symmetric two-atom, 13-iteration SCF timing is not a relaxation, spin, molecule, metallic, large-cell or nosym workload forecast"},
              "planning_allocations_seconds": {"reference_geometries_and_anchors": 9000,
                  "one_or_two_candidate_relaxations": 5400,
                  "cutoff_k_smearing_O2_vacuum_spin_sensitivity": 5400,
                  "failure_and_restart_reserve": 1800-consumed},
              "allocation_rule": "Planning envelopes only; no cap can be increased. A recorded reallocation is allowed inside the global cap before outcomes are used as selection criteria.",
              "feasibility_gate": "After first Phase3 reference/candidate jobs, forecast remaining queue from observed phase/size/k-mesh timings. Stop adding jobs if convergence and references cannot fit. Prefer one complete limited-set comparison over two incomplete cases.",
              "all_161_reference_only_average_budget_seconds": 9000/161,
              "execution_over_20_source_sites": large_primary,
              "execution_max_source_sites": max_source_sites,
              "full_inventory_forecast": f"Not promised: 161 original source cells, {large_primary} >20-atom phases, maximum{max_source_sites} atoms and unresolved spin cases make a full convergence-checked recalculation unlikely within the 9000-second reference envelope.",
              "fallback_full_inventory_forecast": f"Mg-O still has57 source cells and{large_fallback} >20-atom phases; fallback means a smaller same-composition/limited-reference study, not an automatic complete hull"}
    save("budget_forecast.json", budget)
    queue = []
    anchor_ids = ["mp-2605", "mp-1265", "mp-153", "mp-45"]
    for row in sorted(rows, key=lambda row: (anchor_ids.index(row["material_id"]) if row["material_id"] in anchor_ids else 4,
                                            row["qe_input_n_sites"], row["material_id"])):
        queue.append({"material_id": row["material_id"], "formula": row["reduced_formula"],
                      "chemical_system": row["chemical_system"], "primitive_n_sites": row["primitive_n_sites"],
                      "QE_input_n_sites": row["qe_input_n_sites"], "QE_input_geometry": row["qe_input_geometry"],
                      "QE_input_cell_policy": row["qe_input_cell_policy"],
                      "space_group": row["space_group_number_symprec_0p01"],
                      "priority": "mandatory_direct_oxide_anchor" if row["material_id"] in anchor_ids[:2] else
                          "elemental_metal_control" if row["material_id"] in anchor_ids[2:] else "conditional_remaining_complete_inventory",
                      "large_over_20_sites": row["qe_input_n_sites"] > 20,
                      "spin_or_occupation_review_required": row.get("settings", {}).get("spin_review_required_before_reference_acceptance", True),
                      "phase2_status": "not_run", "input_template": row.get("input_template")})
    with (ART / "reference_queue.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(queue[0]))
        writer.writeheader()
        writer.writerows(queue)
    plan = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
            "primary_system": "Ca-Mg-O", "primary_formula": "CaMg2O3", "primary_formula_n_atoms": 6,
            "formula_selection_manifest": str(selection_path.relative_to(ROOT)),
            "formula_selection_sha256": digest(selection_path), "formula_catalog_absence": selected,
            "primary_reference_inventory": "artifacts/phase2/dft/primary_reference_plan.json",
            "primary_all_entries": len(rows), "fallback_system": "Mg-O", "fallback_all_entries": len(fallback["records"]),
            "reference_inventory_scope": "MP2022 snapshot only; additional WBM structures are not included in the fresh QE inventory, and this is not a universal all-known-phase hull",
            "fallback_reference_inventory": "artifacts/phase2/dft/fallback_Mg-O_reference_plan.json",
            "known_reference_controls": {"CaO_rocksalt": "mp-2605", "MgO_rocksalt": "mp-1265",
                                         "Mg_hcp": "mp-153", "Ca_fcc": "mp-45"},
            "direct_reaction": {"equation": "CaMg2O3 -> CaO + 2 MgO", "mole_coefficients": {"CaMg2O3": -1, "CaO": 1, "MgO": 2},
                                "delta_definition": "e_candidate - (1/3)*e_CaO - (2/3)*e_MgO, all energies eV/atom",
                                "reference_weights_exact": {"CaO": "1/3", "MgO": "2/3"},
                                "total_energy_equivalent": "(E_candidate_per_6_atom_formula - E_CaO_per_2_atom_formula - 2*E_MgO_per_2_atom_formula)/6",
                                "positive_resolved_margin": "Candidate is unstable against this explicit compatible decomposition",
                                "negative_resolved_margin": "Candidate beats these two anchors only; not a full161-entry stability result"},
            "initial_execution_queue": queue[:4],
            "O2_templates": ["artifacts/phase2/dft/input_templates/O2_triplet_box_12A", "artifacts/phase2/dft/input_templates/O2_triplet_box_15A", "artifacts/phase2/dft/input_templates/O2_triplet_box_18A"],
            "numerical_protocol": "artifacts/phase2/dft/numerical_protocol.json", "budget": "artifacts/phase2/dft/budget_forecast.json",
            "early_candidate_freeze": "Phase3 must freeze early cohort IDs/geometry hashes/pool snapshot/selector/tie-breaks before candidate QE outcomes; no claim that they are best from a later completed pool. Retain failed attempts and reserve use.",
            "phase2_QE_jobs_executed": 0, "phase2_CHGNet_jobs_executed": 0,
            "reference_source_energies_used": False,
            "no_result_claim": "All Phase2 energies are pending; neither candidates nor reference phases were evaluated in Phase2"}
    save("reference_plan.json", plan)
    checks = []
    template_sources = {}
    for cohort_name in ["primary_reference_plan.json", "fallback_Mg-O_reference_plan.json"]:
        cohort = json.loads((ART / cohort_name).read_text())
        for row in cohort["records"]:
            assert (ROOT / row["primitive_geometry"]).is_file()
            assert (ROOT / row["primitive_cif"]).is_file()
            assert digest(ROOT / row["primitive_geometry"]) == row["geometry_sha256"]
            assert digest(ROOT / row["execution_geometry_path"]) == row["execution_geometry_sha256"]
            if row.get("input_template"):
                template_sources[ROOT / row["input_template"]] = ROOT / row["execution_geometry_path"]
    for path in sorted((ART / "input_templates").rglob("pw.in")):
        atoms = read(path, format="espresso-in")
        settings = json.loads(path.with_name("settings.json").read_text())
        assert len(atoms) == settings["nat"]
        assert np.isfinite(atoms.positions).all() and atoms.get_volume() > 0
        assert settings["conv_thr_Ry"] == 1e-8 and settings["nosym"]
        assert settings["ecutwfc_Ry"] == 50 and settings["ecutrho_Ry"] == 400
        source_path = template_sources.get(path, path.with_name("geometry.json"))
        source_geometry = Structure.from_file(source_path)
        assert len(atoms) == len(source_geometry)
        assert atoms.get_chemical_symbols() == [site.specie.symbol for site in source_geometry]
        assert np.allclose(atoms.cell.array, source_geometry.lattice.matrix, atol=1e-9, rtol=0)
        assert np.allclose(atoms.positions, source_geometry.cart_coords, atol=1e-8, rtol=0)
        checks.append({"template": str(path.relative_to(ROOT)), "n_atoms": len(atoms), "ase_input_parse": "passed", "sha256": digest(path),
                       "execution_source_geometry": str(source_path.relative_to(ROOT)), "template_matches_original_source": True})
    audit = {"phase2_jobs_executed": 0, "QE_ledger_unchanged_sha256": digest(ledger_path),
             "template_count": len(checks), "template_checks": checks,
             "primary_reference_geometry_count": len(rows), "fallback_geometry_count": len(fallback["records"]),
             "all_geometry_files_exist_and_hash_match": True, "all_template_parses_passed": True,
             "all_reference_template_geometries_match_original_source_cells": True,
             "template_readiness": "Syntax/geometry parsing only, not QE electronic, spin or numerical convergence validation"}
    save("phase2_dft_audit.json", audit)
    report = f"""# Phase 2 DFT plan: Ca-Mg-O / CaMg2O3

The primary composition is **CaMg2O3 (six reduced atoms)**, selected by the shared
label-blind composition protocol and absent from both named frozen WBM and MP
composition catalogs. This is catalog-scoped absence, not global novelty.

The complete MP2022 reference inventory contains **161 entries** across Ca, Mg,
O, Ca-Mg, Ca-O, Mg-O and Ca-Mg-O. All source/primitive JSON geometries and CIFs
are retained under data/references/mp_2022_10_28. Tight geometry-only matching
found no aliases; no source energy or hull filtering was used. Twenty-one entries
have more than20 informational primitive atoms, including a150-atom CaMg149 phase. Known
ternaries include CaMg3O4 and CaMgO3; spin/occupancy-ambiguous references are flagged.
The alternate Mg-O inventory contains57 entries, including14 over20 atoms.
For execution, ALL original source cells are retained: {large_primary} primary
and {large_fallback} fallback cells exceed20 atoms; the largest primary source
cell has{max_source_sites} atoms. Primitive copies are informational and unverified,
never used for QE. In particular mp-1183575 retains its original4-atom CaMg cell.
Source site properties are preserved in JSON; magnetic-order metadata still needs
explicit QE spin initialization/review before any flagged reference is executed.
Neither inventory is promised to be fully recalculated within the six-hour cap.
These reference geometries cover the named MP snapshot only: additional WBM
structures are not part of the fresh QE reference inventory. WBM is used for
composition absence and the separate replay. A complete MP-inventory result
would still not establish stability against every known or published phase.

The first small reference queue is CaO rocksalt mp-2605, MgO rocksalt mp-1265,
Mg hcp mp-153 and Ca fcc mp-45, selected by documented prototypes, not source
energies. All other phases remain visible in reference_queue.csv. The primary
candidate has an explicit test reaction **CaMg2O3 -> CaO +2MgO**:

    delta [eV/atom] = e_candidate - e_CaO/3 - 2e_MgO/3

A clearly positive value demonstrates instability against that reaction. A clearly
negative value only beats those two binary anchors. It is not stability against the
full161-entry reference inventory. Candidate-vs-candidate competition must also
be checked. Margins comparable to the measured numerical sensitivity remain
unresolved; start with a5-meV/atom guard and enlarge it when actual shifts require.

Templates use PBE, the same checksum-identified UPF per element, shared starting
50/400-Ry cutoffs, reciprocal spacing0.60/A with denser probes, electronic1e-8Ry,
force8e-4Ry/Bohr (~0.02057eV/A), pressure0.5kbar, and unconstrained solid-cell
relaxation with nosym/noinv. The inputs are starting templates, not converged
production settings. Cutoff/k/smearing/spin/vacuum checks must be executed later.
After choosing final cutoff/k settings, recheck force vectors and full stress at
those exact settings. Continue geometry/cell relaxation if stationarity fails,
then repeat checks before accepting energies; small energy shifts alone are insufficient.
For solids, final acceptance requires both absolute scalar pressure<=0.5kbar and
every residual stress-tensor component<=0.5kbar in absolute value; a small trace
cannot hide shear. Independently check maximum atomic force-vector norm<=0.02057eV/A.
O2 triplet templates have fixed12/15/18-A boxes and fixed total magnetization2muB;
solid-oxygen entries are retained independently. Missing spin review blocks a
complete reference claim. No MP/VASP, WBM or CHGNet energy is mixed into QE.

The existing QE ledger has{len(jobs)} known-phase job consuming
{consumed:.6f}s, leaving{21600-consumed:.6f}s. Budget planning allocates9000s for
references/anchors,5400s for one or two candidates,5400s for numerical checks,
and{1800-consumed:.6f}s for failures/restarts. These are ceilings/planning envelopes,
not promised runtimes. The2.104-second symmetric two-atom SCF pilot cannot predict
larger nonsymmetric relaxations or molecular/spin workloads. Run one QE job with
four threads at a time and append every attempt to the existing QE ledger.

**No QE or CHGNet calculation ran in Phase2.** All{len(checks)} QE input templates
were parsed with ASE, and geometry/hash checks passed. This validates input
syntax/geometry, not electronic convergence or stability. Stage checksum-verified
UPFs and scratch directories when creating actual Phase3 jobs.

Entry points:

    .envs/analysis/Scripts/python.exe -W ignore::FutureWarning scripts/phase2_dft.py inventory
    .envs/analysis/Scripts/python.exe -W ignore::FutureWarning scripts/phase2_dft.py prepare --system Ca-Mg-O
    .envs/analysis/Scripts/python.exe scripts/phase2_dft_finalize.py

The frozen plan is reference_plan.json; numerical_protocol.json and
budget_forecast.json contain acceptance and stopping rules. Primary and fallback
reference_plan files retain every entry and template. Phase3 must freeze early
candidate IDs and pool provenance before candidate DFT outcomes.

Source geometry archive: https://figshare.com/files/40344436, MP2022 export,
MD5 76fc748db6b175bb80de4c276d27c235. SSSP source:
https://archive.materialscloud.org/record/2023.65. QE input definitions:
https://www.quantum-espresso.org/Doc/INPUT_PW.html.
"""
    (ART / "README.md").write_text(report, encoding="utf-8")
    print(json.dumps({"primary": "Ca-Mg-O", "formula": "CaMg2O3", "references": len(rows),
                      "template_count": len(checks), "QE_jobs_in_phase2": 0,
                      "remaining_QE_walltime_seconds": 21600-consumed}, indent=2))


if __name__ == "__main__":
    main()
