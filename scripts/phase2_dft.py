"""Freeze energy-blind reference inventories and QE templates; never launch jobs."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Structure, Lattice
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from phase2_json_columns import iter_column_records
from phase2_dft_inputs import write_template

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "phase2" / "dft"
REFERENCES = ROOT / "data" / "references" / "mp_2022_10_28"
SOURCE = ROOT / "data" / "mp" / "2023-02-07-mp-computed-structure-entries.json.gz"
SOURCE_MD5 = "76fc748db6b175bb80de4c276d27c235"
SYSTEMS = {"Ca-Mg-O": {"Ca", "Mg", "O"}, "Mg-O-Zn": {"Mg", "O", "Zn"}, "Mg-O": {"Mg", "O"}}


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def inventory():
    if digest(SOURCE, "md5") != SOURCE_MD5:
        raise RuntimeError("MP source does not match frozen official registry MD5")
    ART.mkdir(parents=True, exist_ok=True)
    REFERENCES.mkdir(parents=True, exist_ok=True)
    records = []
    examined = 0
    material_ids = {}
    for column, index, entry in iter_column_records(SOURCE, {"material_id", "entry"}):
        if column == "material_id":
            material_ids[index] = str(entry)
            continue
        examined += 1
        elements = set(entry["composition"])
        memberships = [name for name, allowed in SYSTEMS.items() if elements <= allowed]
        if not memberships:
            continue
        material_id = material_ids[index]
        if not material_id.startswith("mp-") or not material_id[3:].isdigit():
            raise ValueError(f"Unexpected material ID: {material_id}")
        # Deliberately do not copy or inspect entry energy/corrections or hull labels.
        structure = Structure.from_dict(entry["structure"])
        primitive = structure.get_primitive_structure(tolerance=1e-5, use_site_props=True)
        primitive.remove_oxidation_states()
        source_path = REFERENCES / f"{material_id}.source.json"
        primitive_path = REFERENCES / f"{material_id}.primitive.json"
        cif_path = REFERENCES / f"{material_id}.primitive.cif"
        save(source_path, structure.as_dict())
        save(primitive_path, primitive.as_dict())
        primitive.to(filename=str(cif_path))
        try:
            spacegroup = SpacegroupAnalyzer(primitive, symprec=0.01).get_space_group_number()
        except Exception:
            spacegroup = None
        moments = primitive.site_properties.get("magmom", [])
        moment_max = max((float(np.linalg.norm(value)) for value in moments if value is not None), default=0.0)
        formula = primitive.composition.reduced_formula
        row = {"material_id": material_id, "source_entry_id": entry["entry_id"], "source_row": index,
               "memberships": memberships, "elements": sorted(elements),
               "chemical_system": "-".join(sorted(elements)),
               "composition": primitive.composition.as_dict(), "reduced_formula": formula,
               "source_n_sites": len(structure), "primitive_n_sites": len(primitive),
               "space_group_number_symprec_0p01": spacegroup,
               "ordered": primitive.is_ordered,
               "max_source_site_moment_muB": moment_max,
               "spin_review_required": moment_max > 0.1,
               "source_geometry": str(source_path.relative_to(ROOT)),
               "primitive_geometry": str(primitive_path.relative_to(ROOT)),
               "primitive_cif": str(cif_path.relative_to(ROOT)),
               "geometry_sha256": digest(primitive_path),
               "phase2_qe_status": "not_run",
               "larger_than_preferred_10_atom_candidate_cap": len(primitive) > 10,
               "expensive_reference_flag": len(primitive) > 20}
        records.append(row)
    records.sort(key=lambda row: row["material_id"])
    # Merge only geometric duplicates, never select a representative by source energy.
    matcher = StructureMatcher(ltol=1e-4, stol=1e-3, angle_tol=0.01,
                               primitive_cell=True, scale=False, attempt_supercell=False)
    representatives = collections.defaultdict(list)
    for row in records:
        geometry = Structure.from_file(ROOT / row["primitive_geometry"])
        duplicate = None
        for representative_id, representative in representatives[row["reduced_formula"]]:
            if matcher.fit(geometry, representative):
                duplicate = representative_id
                break
        row["geometry_representative_id"] = duplicate or row["material_id"]
        row["geometry_duplicate"] = duplicate is not None
        if duplicate is None:
            representatives[row["reduced_formula"]].append((row["material_id"], geometry))
    source = {"path": str(SOURCE.relative_to(ROOT)), "md5": digest(SOURCE, "md5"),
              "sha256": digest(SOURCE), "bytes": SOURCE.stat().st_size,
              "source_url": "https://figshare.com/files/40344436",
              "catalog_snapshot": "MP v2022.10.28, exported 2023-02-07",
              "total_entries_examined": examined,
              "geometry_alias_tolerances": {"ltol": 1e-4, "stol": 1e-3, "angle_tol_degrees": 0.01, "scale": False},
              "selection": "Every record with an element set contained in each named system; no source energy/hull filter"}
    save(ART / "reference_inventory_all_profiles.json", {"source": source, "records": records})
    profiles = {}
    for name in SYSTEMS:
        selected = [row for row in records if name in row["memberships"]]
        unique = [row for row in selected if not row["geometry_duplicate"]]
        profiles[name] = {"all_catalog_entries": len(selected), "geometric_representatives": len(unique),
                          "by_chemical_system": dict(collections.Counter(row["chemical_system"] for row in selected)),
                          "all_formula_count": len({row["reduced_formula"] for row in selected}),
                          "max_primitive_sites": max((row["primitive_n_sites"] for row in selected), default=0),
                          "representatives_over_20_sites": [row["material_id"] for row in unique if row["primitive_n_sites"] > 20],
                          "representatives_spin_review": [row["material_id"] for row in unique if row["spin_review_required"]],
                          "representative_site_counts": sorted(row["primitive_n_sites"] for row in unique),
                          "source_energies_used": False}
    save(ART / "system_tractability_profiles.json", {"source": source, "profiles": profiles})
    print(json.dumps({"profiles": profiles}, indent=2), flush=True)


def stage_pseudos(elements):
    directory = ROOT / "data" / "pseudopotentials"
    metadata = json.loads((directory / "SSSP_1.3.0_PBE_efficiency.json").read_text())
    archive = directory / "SSSP_1.3.0_PBE_efficiency.tar.gz"
    if digest(archive, "md5") != "a58f1b3373f330179fd0832c48bb9a52":
        raise RuntimeError("SSSP archive checksum mismatch")
    result = {}
    with tarfile.open(archive, "r:gz") as bundle:
        for element in sorted(elements):
            info = dict(metadata[element])
            matches = [member for member in bundle.getmembers() if Path(member.name).name == info["filename"]]
            if len(matches) != 1:
                raise ValueError(f"Non-unique pseudopotential: {element}")
            target = directory / info["filename"]
            if not target.exists():
                target.write_bytes(bundle.extractfile(matches[0]).read())
            if digest(target, "md5") != info["md5"]:
                raise RuntimeError(f"Pseudopotential MD5 mismatch: {element}")
            info.update({"path": str(target.relative_to(ROOT)), "sha256": digest(target)})
            result[element] = info
    return result


def prepare(system):
    combined = json.loads((ART / "reference_inventory_all_profiles.json").read_text())
    # Execution conservatively retains every original source cell. Existing
    # primitive files are informational only and carry no equivalence proof.
    for row in combined["records"]:
        source_geometry = Structure.from_file(ROOT / row["source_geometry"])
        moments = source_geometry.site_properties.get("magmom", [])
        moment_max = max((float(np.linalg.norm(value)) for value in moments if value is not None), default=0.0)
        row.update({"qe_input_geometry": row["source_geometry"],
                    "execution_geometry_path": row["source_geometry"],
                    "execution_geometry_sha256": digest(ROOT / row["source_geometry"]),
                    "execution_n_sites": len(source_geometry),
                    "qe_input_n_sites": len(source_geometry),
                    "qe_geometry_sha256": digest(ROOT / row["source_geometry"]),
                    "qe_input_cell_policy": "original source cell; no primitive reduction used for execution",
                    "primitive_equivalence_verified_for_execution": False,
                    "primitive_copy_role": "informational unverified reduction only; never used for QE input",
                    "max_source_site_moment_muB": moment_max,
                    "spin_review_required": moment_max > 0.1,
                    "source_site_properties": list(source_geometry.site_properties),
                    "expensive_reference_flag": len(source_geometry) > 20})
    combined["source"]["QE_execution_cell_policy"] = "Original source cells for every entry; site properties preserved; no primitive reduction used"
    save(ART / "reference_inventory_all_profiles.json", combined)
    profiles_path = ART / "system_tractability_profiles.json"
    profiles = json.loads(profiles_path.read_text())
    for name in SYSTEMS:
        members = [row for row in combined["records"] if name in row["memberships"]]
        profiles["profiles"][name].update({
            "execution_cell_policy": "all original source cells; primitive counts informational only",
            "execution_source_site_counts": sorted(row["execution_n_sites"] for row in members),
            "execution_max_source_sites": max(row["execution_n_sites"] for row in members),
            "execution_over_20_source_sites": [row["material_id"] for row in members if row["execution_n_sites"] > 20]})
    save(profiles_path, profiles)
    rows = [row for row in combined["records"] if system in row["memberships"]]
    fallback = [row for row in combined["records"] if "Mg-O" in row["memberships"]]
    pseudos = stage_pseudos(SYSTEMS[system] | {"Mg", "O"})
    save(ART / "pseudopotentials.json", {"library": "SSSP_1.3.0_PBE_efficiency", "elements": pseudos})
    for cohort, selected in (("primary", rows), ("fallback_Mg-O", fallback)):
        plan = []
        for row in selected:
            item = dict(row)
            if row["geometry_duplicate"]:
                item["planned_treatment"] = "retained alias; representative geometry must be validated before energy reuse"
            else:
                geometry = Structure.from_file(ROOT / row["qe_input_geometry"])
                directory = ART / "input_templates" / cohort / row["material_id"]
                # Unary metals and non-charge-balanced metal-rich phases need occupation review.
                oxygen = row["composition"].get("O", 0)
                cations = sum(value for key, value in row["composition"].items() if key != "O")
                metallic = ("O" not in row["elements"]) or (oxygen < cations)
                review_spin = row["spin_review_required"] or (oxygen > 0 and oxygen != cations)
                settings = write_template(directory, geometry, pseudos, prefix=row["material_id"].replace("-", "_"),
                                          metallic=metallic, spin_review_required=review_spin)
                item["input_template"] = str((directory / "pw.in").relative_to(ROOT))
                item["settings"] = settings
                item["planned_treatment"] = "recalculate geometry and energy in QE; review occupancy/spin before accepting"
            plan.append(item)
        save(ART / f"{cohort}_reference_plan.json", {"system": system if cohort == "primary" else "Mg-O",
             "source": combined["source"], "records": plan, "qe_jobs_executed_in_phase2": 0})
    for box in (12.0, 15.0, 18.0):
        oxygen = Structure(Lattice.cubic(box), ["O", "O"],
                           [[0.5, 0.5, 0.5 - 1.23/(2*box)], [0.5, 0.5, 0.5 + 1.23/(2*box)]])
        directory = ART / "input_templates" / f"O2_triplet_box_{box:g}A"
        save(directory / "geometry.json", oxygen.as_dict())
        oxygen.to(filename=str(directory / "geometry.cif"))
        write_template(directory, oxygen, pseudos, prefix=f"o2_box_{int(box)}", calculation="relax",
                       molecular_oxygen=True, vacuum_angstrom=box, max_seconds=1200)
    save(ART / "selection_freeze.json", {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
         "primary_chemical_system": system, "fallback_chemical_system": "Mg-O",
         "selection_basis": "Catalog absence coverage and complete geometry inventory size; no target energies used",
         "candidate_selection_status": "candidate IDs/ranking not available until Phase3; no outcome-dependent replacements permitted",
         "qe_jobs_executed_in_phase2": 0, "source_energies_or_hull_values_used": False})
    print(json.dumps({"prepared_primary": system, "reference_entries": len(rows),
                      "fallback_entries": len(fallback), "qe_jobs_executed": 0}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("inventory", "prepare"))
    parser.add_argument("--system", choices=tuple(SYSTEMS), default="Ca-Mg-O")
    args = parser.parse_args()
    if args.command == "inventory":
        inventory()
    else:
        prepare(args.system)
