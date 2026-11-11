"""Freeze composition sampling settings and energy-blind prototype templates."""
from __future__ import annotations
import ast
import csv
import hashlib
from itertools import permutations
import json
from pathlib import Path
import sys

from pymatgen.core import Element, Structure

from phase2_json_columns import iter_column_records

ROOT = Path(__file__).resolve().parents[1]
COMPS = ROOT / "artifacts/phase2/compositions"
CATALOGS = ROOT / "artifacts/phase2/catalogs"
MP = ROOT / "data/mp/2023-02-07-mp-computed-structure-entries.json.gz"


def artifact_inventory():
    roots = [ROOT / "data/mp", ROOT / "data/catalogs", CATALOGS, COMPS,
             ROOT / "artifacts/phase2/controls"]
    inventory_path = CATALOGS / "artifact_inventory.json"
    files = {path for directory in roots for path in directory.rglob("*")
             if path.is_file() and path != inventory_path and path.suffix != ".log"}
    files.update(ROOT / "scripts" / filename for filename in ["phase2_catalogs.py", "phase2_catalogs_finalize.py",
                 "phase2_formula_rules.py", "phase2_json_columns.py"])
    rows = []
    for path in sorted(files):
        sha = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                sha.update(block)
        rows.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                     "sha256": sha.hexdigest()})
    inventory = {"scope": "All files in the catalog/composition/control lane plus its four scripts",
                 "excluded": ["This inventory itself", "Live stdout/stderr .log files"], "files": rows}
    inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"artifact_inventory_files": len(rows), "path": inventory_path.relative_to(ROOT).as_posix()}))


def immutable_json(path, value):
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"Frozen file differs: {path}")
    else:
        path.write_text(text, encoding="utf-8")


def budget_clarification_write(path, value, expected_legacy):
    """Apply only the explicitly authorized Phase 2 budget clarification.

    Existing scientific settings must match exactly after removing the listed
    accounting-only fields. Repeated runs reuse identical amended artifacts.
    """
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous == value:
            return
        if previous != expected_legacy:
            raise RuntimeError(f"Refusing a change beyond the authorized budget clarification: {path}")
    path.write_text(text, encoding="utf-8")


def prototype_candidate_records(prototypes):
    candidates = []
    for plan in prototypes["plans"]:
        if not plan["eligible_for_attempt"]:
            continue
        selected = plan["selected"]
        path = ROOT / selected["prototype_candidate_cif"]
        candidates.append({"candidate_id": path.stem, "target_formula": plan["target_formula"],
                           "parent_material_id": selected["material_id"],
                           "cif": path.relative_to(ROOT).as_posix(),
                           "cif_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "structure_budget_charge": 1})
    assert len({row["candidate_id"] for row in candidates}) == len(candidates)
    assert len({row["cif_sha256"] for row in candidates}) == len(candidates)
    return candidates


def generation_protocol(selection, prototypes):
    # Validate the actual pinned space-group table instead of relying on names.
    table = ROOT / "vendor/CrystalFormer/crystalformer/data/wyckoff_list.csv"
    with table.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    positions = ast.literal_eval(rows[1]["Wyckoff Positions"])[::-1]
    multiplicities = [len(position) for position in positions]
    single_letters = [chr(97 + index) for index, size in enumerate(multiplicities) if size == 1]
    double_letters = [chr(97 + index) for index, size in enumerate(multiplicities) if size == 2]
    if len(single_letters) < 3 or not double_letters:
        raise RuntimeError("Pinned SG2 table does not support the declared count witness")
    phase1 = json.loads((ROOT / "artifacts/phase1/generator/config.json").read_text(encoding="utf-8"))
    formulas = []
    for index, row in enumerate(selection["selected"] + selection["reserves"]):
        witness, next_single = [], 0
        for element, count in sorted(row["counts"].items()):
            if count % 2:
                witness.append({"element": element, "wyckoff_letter": single_letters[next_single], "multiplicity": 1})
                next_single += 1
            for _ in range(count // 2):
                witness.append({"element": element, "wyckoff_letter": double_letters[0], "multiplicity": 2})
        expanded = {element: sum(site["multiplicity"] for site in witness if site["element"] == element)
                    for element in row["counts"]}
        assert expanded == row["counts"] and len(witness) <= 20
        formulas.append({"formula": row["formula"], "chemical_system": row["chemical_system"],
            "cohort": "default" if index < 6 else "stretch_or_reserve",
            "conditioning_formula": row["formula"], "evaluated_formula": row["formula"],
            "exact_expanded_counts": row["counts"], "evaluated_n_atoms": row["n_atoms_reduced"],
            "spacegroup": 2, "spacegroup_symbol": "P-1", "formula_unit_scale": 1,
            "count_compatibility_witness": witness, "sampling_seed": 20261022 + 1000 + index,
            "attempts": 8, "batch_size": 4, "batches": 2, "key_schedule": "jax.random.fold_in(PRNGKey(sampling_seed), batch_index)"})
    protocol = {"version": "phase2-new-composition-generation-v1",
        "selection_sha256": hashlib.sha256((COMPS / "selection.json").read_bytes()).hexdigest(),
        "source_revision": phase1["source_revision"], "checkpoint_revision": phase1["checkpoint_revision"],
        "checkpoint_sha256": phase1["checkpoint_sha256"], "model_initialization_seed": 42,
        "temperature": 1.0, "top_p": 1.0, "spacegroup_policy": "Fixed SG2 for every new composition, chosen before candidate outcomes.",
        "multiplicity_table_sha256": hashlib.sha256(table.read_bytes()).hexdigest(),
        "spacegroup_2_wyckoff_multiplicities_alphabetical": multiplicities,
        "compatibility_limit": "Counts only: distinct one-fold sites handle odd amounts and independent two-fold general orbits handle pairs; this does not guarantee non-overlap, successful sampling, or stable chemistry.",
        "exact_count_filter": True, "expanded_atom_cap": 20, "minimum_distance_angstrom": 0.75,
        "symprec_angstrom": 0.01, "angle_tolerance_degrees": 5.0,
        "deduplication": phase1["deduplication"], "formulas": formulas,
        "phase2_samples_generated": 0, "global_generation_cap_including_phase1": 128,
        "control_protocol": "artifacts/phase2/controls/matched_protocol.json",
        "budgets": {"default_new_attempts": 48, "stretch_new_attempts": 64,
                    "control_attempts_including_phase1": 32, "default_total": 80, "stretch_total": 96},
        "no_post_outcome_group_changes": True}
    legacy = json.loads(json.dumps(protocol))
    candidates = prototype_candidate_records(prototypes)
    prepared = len(candidates)
    protocol.update({"version": "phase2-new-composition-generation-v2-budget-clarification",
        "budget_clarification": "The approved shared 128-structure cap includes deterministic prototype-substitution candidates. Four were prepared once in Phase 2; copies, versions and reference geometries add no new candidates. CF primary denominators are unchanged.",
        "phase2_crystalformer_draws": 0,
        "phase2_deterministic_prototype_candidates_prepared": prepared,
        "phase2_structure_candidates_prepared": prepared,
        "deterministic_prototype_candidates": candidates,
        "global_structure_candidate_cap_including_phase1": 128})
    # Preserve the legacy field as an explicitly CF-only zero, for readers of v1.
    protocol["phase2_samples_generated_scope"] = "phase2_samples_generated counts CrystalFormer draws only; deterministic candidates are separately charged below."
    protocol["budgets"] = {"control_attempts_including_phase1": 32,
        "default_new_attempts": 48, "stretch_new_attempts": 64,
        "default_crystalformer_total": 80, "stretch_crystalformer_total": 96,
        "deterministic_prototype_candidates": prepared,
        "default_total": 80 + prepared, "stretch_total": 96 + prepared,
        "default_remaining_headroom": 128 - 80 - prepared,
        "stretch_remaining_headroom": 128 - 96 - prepared,
        "crystalformer_attempts_consumed_at_phase2_end": 8,
        "prototype_candidates_consumed_at_phase2_end": prepared,
        "total_candidates_consumed_at_phase2_end": 8 + prepared,
        "remaining_structure_capacity_at_phase2_end": 128 - 8 - prepared}
    budget_clarification_write(COMPS / "generation_protocol.json", protocol, legacy)
    return protocol


def prototype_templates(selection):
    targets = selection["selected"][:4]
    shortlist = {target["formula"]: [] for target in targets}
    element_cache = {}

    def element(symbol):
        if symbol not in element_cache:
            element_cache[symbol] = Element(symbol)
        return element_cache[symbol]

    with (ROOT / "data/catalogs/mp_full_compositions.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            parent = json.loads(line)
            parent_counts = parent["counts"]
            if "O" not in parent_counts or len(parent_counts) != 3 or parent["n_sites"] > 20:
                continue
            metals = sorted(set(parent_counts) - {"O"})
            if not all(element(symbol).is_metal for symbol in metals): continue
            for target in targets:
                if parent["n_sites"] != target["n_atoms_reduced"]:
                    continue
                if parent_counts["O"] != target["counts"]["O"]: continue
                target_metals = sorted(set(target["counts"]) - {"O"})
                charges = target["oxidation_state_witnesses"][0]
                for assigned in permutations(target_metals):
                    mapping = dict(zip(metals, assigned))
                    if any(parent_counts[source] != target["counts"][dest] for source, dest in mapping.items()): continue
                    if any(charges[dest] not in element(source).common_oxidation_states for source, dest in mapping.items()): continue
                    distance = sum(abs(element(source).Z - element(dest).Z) for source, dest in mapping.items())
                    key = [distance, parent["n_sites"], int(parent["material_id"].split("-")[1]), sorted(mapping.items())]
                    shortlist[target["formula"]].append({"parent": parent, "mapping": {**mapping, "O": "O"},
                                                        "ranking_key": key, "assumed_cation_charges": charges})
    for options in shortlist.values(): options.sort(key=lambda row: row["ranking_key"])
    # Keep a few geometric eligibility fallbacks. Eligibility uses geometry/counts,
    # not energies, and all retained source structures are ordinary dictionaries.
    inspected = {name: options[:8] for name, options in shortlist.items()}
    needed = {row["parent"]["material_id"] for options in inspected.values() for row in options}
    geometries = {}
    if needed:
        for _, _, entry in iter_column_records(MP, {"entry"}):
            material_id = entry["data"]["material_id"]
            if material_id in needed:
                geometries[material_id] = entry["structure"]
                if len(geometries) == len(needed): break
    plans = []
    for target in targets:
        chosen, rejection_log = None, []
        for option in inspected[target["formula"]]:
            identifier = option["parent"]["material_id"]
            structure = Structure.from_dict(geometries[identifier])
            if not structure.is_ordered:
                rejection_log.append({"material_id": identifier, "reason": "disordered_parent"}); continue
            structure.replace_species(option["mapping"])
            actual = {symbol: int(number) for symbol, number in structure.composition.get_el_amt_dict().items()}
            if actual != target["counts"] or len(structure) != target["n_atoms_reduced"]:
                rejection_log.append({"material_id": identifier, "reason": "exact_expanded_counts_mismatch"}); continue
            path = COMPS / f"prototype_{target['formula']}.cif"
            structure.to(filename=str(path), fmt="cif")
            parent_path = COMPS / f"prototype_parent_{identifier}.cif"
            Structure.from_dict(geometries[identifier]).to(filename=str(parent_path), fmt="cif")
            chosen = {"material_id": identifier, "entry_id": option["parent"]["entry_id"],
                      "parent_formula": option["parent"]["formula"], "parent_n_sites": option["parent"]["n_sites"],
                      "element_mapping": option["mapping"], "ranking_key": option["ranking_key"],
                      "assumed_cation_charges": option["assumed_cation_charges"],
                      "prototype_candidate_cif": path.relative_to(ROOT).as_posix(),
                      "parent_cif": parent_path.relative_to(ROOT).as_posix()}
            break
        plans.append({"target_formula": target["formula"], "target_exact_counts": target["counts"],
                      "maximum_relaxation_attempts": 1, "compatible_template_count": len(shortlist[target["formula"]]),
                      "selected": chosen, "eligible_for_attempt": bool(chosen), "geometry_rejections": rejection_log,
                      "missing_template_behavior": "No attempt; do not select a replacement formula from validation outcomes."})
    payload = {"version": "phase2-prototype-baseline-v1", "formula_subset": [target["formula"] for target in targets],
        "maximum_relaxation_attempts": 4, "phase2_relaxations_executed": 0,
        "rule": "Exact reduced stoichiometry AND exact target atom count in source cell, <=20 atoms; O fixed; assigned target cation charge must be common for parent element; then summed absolute atomic-number distance, parent site count, numeric MP material ID, mapping. Ordered geometry only. No energy use.",
        "element_metadata_source": "pymatgen Element atomic number/is_metal/common_oxidation_states; formal-charge plausibility heuristic, not measured charge.",
        "plans": plans}
    immutable_json(COMPS / "prototype_plan.json", payload)
    return payload


def main():
    selection = json.loads((COMPS / "selection.json").read_text(encoding="utf-8"))
    prototypes = prototype_templates(selection)
    generation = generation_protocol(selection, prototypes)
    # Independent no-energy catalog membership proof for selected/reserve formulas.
    canonical = lambda counts: tuple(sorted((symbol, int(number)) for symbol, number in counts.items()))
    catalog_sets = {}
    catalog_counts = {}
    for name in ("wbm", "mp"):
        formulas, identifiers = set(), set()
        with (ROOT / f"data/catalogs/{name}_full_compositions.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                assert not any(key in record for key in ("energy", "e_above_hull", "e_form", "target"))
                formulas.add(canonical(record["counts"])); identifiers.add(record["material_id"])
        catalog_sets[name] = formulas; catalog_counts[name] = {"records": len(identifiers), "unique_compositions": len(formulas)}
    for row in selection["selected"] + selection["reserves"]:
        assert canonical(row["counts"]) not in catalog_sets["wbm"] | catalog_sets["mp"]
        assert row["chemical_system"] in selection["reserved_chemical_systems_all_seeds"]
        assert all(sum(row["counts"][symbol] * charge for symbol, charge in witness.items()) == 0
                   for witness in row["oxidation_state_witnesses"])
    for control in json.loads((ROOT / "artifacts/phase2/controls/matched_protocol.json").read_text(encoding="utf-8"))["controls"]:
        structure = Structure.from_file(ROOT / control["reference_cif"])
        assert len(structure) == control["evaluated_n_atoms"]
        assert {symbol: int(number) for symbol, number in structure.composition.get_el_amt_dict().items()} == control["exact_element_counts"]
    audit = {"checks_passed": True, "catalog_counts": catalog_counts,
        "enumerated": selection["enumerated_formulas"], "absent_both": selection["new_to_both_count"],
        "selected": len(selection["selected"]), "reserves": len(selection["reserves"]),
        "reserved_system_superset": len(selection["reserved_chemical_systems_all_seeds"]),
        "all_proposals_charge_balanced_and_absent_both": True,
        "all_proposals_within_reserved_superset": True, "energy_fields_used_for_selection": [],
        "new_formula_sg2_count_witnesses": len(generation["formulas"]),
        "eligible_prototype_baselines": sum(row["eligible_for_attempt"] for row in prototypes["plans"]),
        "samples_relaxations_dft_executed_in_phase2": 0}
    legacy_audit = json.loads(json.dumps(audit))
    audit.pop("samples_relaxations_dft_executed_in_phase2")
    audit.update({"crystalformer_draws_in_phase2": 0,
        "deterministic_prototype_candidates_prepared_in_phase2": len(generation["deterministic_prototype_candidates"]),
        "relaxations_executed_in_phase2": 0, "dft_jobs_executed_in_phase2": 0,
        "shared_structure_candidates_consumed_at_phase2_end": generation["budgets"]["total_candidates_consumed_at_phase2_end"],
        "shared_structure_capacity_remaining_at_phase2_end": generation["budgets"]["remaining_structure_capacity_at_phase2_end"],
        "cf_primary_denominators_unchanged": True})
    budget_clarification_write(CATALOGS / "audit.json", audit, legacy_audit)
    print(json.dumps(audit, indent=2))
    artifact_inventory()


if __name__ == "__main__":
    if "--inventory-only" in sys.argv:
        artifact_inventory()
    elif "--budget-clarification-only" in sys.argv:
        frozen_selection = json.loads((COMPS / "selection.json").read_text(encoding="utf-8"))
        frozen_prototypes = json.loads((COMPS / "prototype_plan.json").read_text(encoding="utf-8"))
        amended = generation_protocol(frozen_selection, frozen_prototypes)
        previous_audit = json.loads((CATALOGS / "audit.json").read_text(encoding="utf-8"))
        if "samples_relaxations_dft_executed_in_phase2" in previous_audit:
            corrected = dict(previous_audit)
            corrected.pop("samples_relaxations_dft_executed_in_phase2")
            corrected.update({"crystalformer_draws_in_phase2": 0,
                "deterministic_prototype_candidates_prepared_in_phase2": len(amended["deterministic_prototype_candidates"]),
                "relaxations_executed_in_phase2": 0, "dft_jobs_executed_in_phase2": 0,
                "shared_structure_candidates_consumed_at_phase2_end": amended["budgets"]["total_candidates_consumed_at_phase2_end"],
                "shared_structure_capacity_remaining_at_phase2_end": amended["budgets"]["remaining_structure_capacity_at_phase2_end"],
                "cf_primary_denominators_unchanged": True})
            budget_clarification_write(CATALOGS / "audit.json", corrected, previous_audit)
        artifact_inventory()
        print(json.dumps({"budgets": amended["budgets"], "prototype_candidate_ids":
                          [row["candidate_id"] for row in amended["deterministic_prototype_candidates"]]}, indent=2))
    else:
        main()
