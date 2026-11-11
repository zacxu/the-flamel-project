"""Freeze label-blind Phase 2 composition catalogs, proposals, and controls.

Only composition/IDs/geometry metadata are used. No energy field is selected,
ranked, written to the composition indexes, or used for reference selection.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.request

import pandas as pd
from pymatgen.core import Element, Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from phase2_formula_rules import (PALETTE, normalized_counts, formula_counts,
    canonical_formula, chemical_system, enumerate_formulas, reserved_superset)
from phase2_json_columns import iter_column_records

ROOT = Path(__file__).resolve().parents[1]
MP = ROOT / "data/mp/2023-02-07-mp-computed-structure-entries.json.gz"
WBM = ROOT / "data/wbm/2023-12-13-wbm-summary.csv.gz"
DATA = ROOT / "data/catalogs"
ART = ROOT / "artifacts/phase2/catalogs"
COMPS = ROOT / "artifacts/phase2/compositions"
CONTROLS = ROOT / "artifacts/phase2/controls"
EXPECTED_MD5 = {MP.name: "76fc748db6b175bb80de4c276d27c235",
                WBM.name: "1555268d3aa59d20262cb9d01ce0994b"}
REGISTRY_REVISION = "2b7bff925a6aff10240cf6ef0f59149f51adff7b"


def now(): return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists() and path.name in {"selection.json", "matched_protocol.json"}:
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"Frozen artifact differs; refusing overwrite: {path}")
    else:
        path.write_text(text, encoding="utf-8")


def hashes(path):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(chunk); sha.update(chunk)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
            "md5": md5.hexdigest(), "sha256": sha.hexdigest()}


def ensure_mp(offline):
    metadata_path = DATA / "figshare_22715158_metadata.json"
    if not metadata_path.exists() and not offline:
        with urllib.request.urlopen("https://api.figshare.com/v2/articles/22715158", timeout=60) as response:
            metadata_path.write_bytes(response.read())
    if not MP.exists():
        if offline: raise FileNotFoundError(MP)
        # A fixed query avoids stale cached, expired object-store redirects.
        url = "https://ndownloader.figshare.com/files/40344436?phase2=20261022"
        temporary = MP.with_suffix(MP.suffix + ".partial")
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as output:
            size = response.headers.get("Content-Length")
            if size and int(size) > 1_000_000_000:
                raise RuntimeError("MP archive exceeds the one-GB download guard")
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 1_000_000_000: raise RuntimeError("Download exceeds one-GB guard")
                output.write(chunk)
        if hashes(temporary)["md5"] != EXPECTED_MD5[MP.name]: raise RuntimeError("MP download MD5 mismatch")
        temporary.rename(MP)


def build_catalogs():
    wb = pd.read_csv(WBM, usecols=["material_id", "formula"], dtype=str)
    if len(wb) != 256963 or wb.material_id.nunique() != 256963:
        raise RuntimeError("WBM full-population count/ID mismatch")
    wbm_set, wbm_ids = set(), set()
    wbm_path = DATA / "wbm_full_compositions.jsonl"
    with wbm_path.open("w", encoding="utf-8") as output:
        for row in wb.itertuples(index=False):
            counts = formula_counts(row.formula)
            wbm_set.add(counts); wbm_ids.add(row.material_id)
            output.write(json.dumps({"material_id": row.material_id, "formula": canonical_formula(counts),
                                     "counts": dict(counts), "chemical_system": chemical_system(counts)}) + "\n")
    mp_set, mp_ids, columns, control_geometries = set(), set(), Counter(), []
    mp_path = DATA / "mp_full_compositions.jsonl"
    cached_manifest = ART / "catalog_manifest.json"
    # Reuse only a fully audited prior index with the same raw-file fingerprint.
    if mp_path.exists() and cached_manifest.exists():
        prior = json.loads(cached_manifest.read_text(encoding="utf-8"))
        if prior.get("files", {}).get("mp", {}).get("sha256") == hashes(MP)["sha256"]:
            with mp_path.open(encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line); mp_set.add(normalized_counts(row["counts"])); mp_ids.add(row["material_id"])
            control_geometries = json.loads((DATA / "control_geometry_candidates.json").read_text(encoding="utf-8"))
            columns.update(prior["mp_column_counts"])
            return wbm_set, mp_set, {"wbm_rows": len(wb), "wbm_unique_compositions": len(wbm_set),
                "mp_rows": len(mp_ids), "mp_unique_compositions": len(mp_set),
                "mp_column_counts": dict(columns), "control_geometries": control_geometries}
    print(json.dumps({"event": "mp_catalog_scan_started", "utc": now()}), flush=True)
    with mp_path.open("w", encoding="utf-8") as output:
        for column, index, entry in iter_column_records(MP, {"material_id", "entry"}):
            columns[column] += 1
            if column != "entry": continue
            counts = normalized_counts(entry["composition"])
            material_id = entry["data"]["material_id"]
            if material_id in mp_ids: raise RuntimeError(f"Duplicate MP material ID: {material_id}")
            mp_ids.add(material_id); mp_set.add(counts)
            n_sites = len(entry["structure"]["sites"])
            row = {"material_id": material_id, "entry_id": entry["entry_id"],
                   "formula": canonical_formula(counts), "counts": dict(counts),
                   "chemical_system": chemical_system(counts), "n_sites": n_sites,
                   "raw_index": index}
            output.write(json.dumps(row) + "\n")
            if counts in {(("Mg", 1), ("O", 1)), (("O", 2), ("Ti", 1))} and n_sites <= 30:
                control_geometries.append({**row, "structure": entry["structure"]})
            if len(mp_ids) % 25000 == 0:
                print(json.dumps({"event": "mp_catalog_progress", "entries": len(mp_ids), "utc": now()}), flush=True)
    if len(mp_ids) != 154718 or columns["entry"] != 154718:
        raise RuntimeError(f"MP complete-population count mismatch: {len(mp_ids)}, {columns}")
    write_json(DATA / "control_geometry_candidates.json", control_geometries)
    return wbm_set, mp_set, {"wbm_rows": len(wb), "wbm_unique_compositions": len(wbm_set),
        "mp_rows": len(mp_ids), "mp_unique_compositions": len(mp_set),
        "mp_column_counts": dict(columns), "control_geometries": control_geometries}


def freeze_compositions(wbm_set, mp_set):
    records = enumerate_formulas()
    screened = []
    for counts, row in records.items():
        screened.append({**row, "present_in_full_wbm": counts in wbm_set,
                         "present_in_mp_snapshot": counts in mp_set,
                         "new_to_both_checked_catalogs": counts not in wbm_set and counts not in mp_set})
    screened.sort(key=lambda row: row["ranking_key"])
    absent = [row for row in screened if row["new_to_both_checked_catalogs"]]
    # Greedy system coverage is explicit: the best-ranked formula from each new
    # chemical system is admitted before considering another formula in that system.
    spread, used = [], set()
    for row in absent:
        if row["chemical_system"] not in used:
            spread.append(row); used.add(row["chemical_system"])
    selected, reserves = spread[:6], spread[6:14]
    payload = {"protocol_version": "phase2-label-blind-v1", "palette_oxidation_states": PALETTE,
        "oxygen_oxidation_state": -2, "formula_atom_cap": 20,
        "enumerated_formulas": len(records), "binary_formulas": sum(len(k) == 2 for k in records),
        "ternary_formulas": sum(len(k) == 3 for k in records), "new_to_both_count": len(absent),
        "new_to_both_chemical_systems": len(used), "screened_limit": 3000,
        "ranking_rule": ["reduced atom count ascending", "Sn redox-ambiguity penalty ascending",
                         "sum of atomic numbers per reduced formula ascending (tractability proxy)",
                         "canonical formula ascending", "one formula per chemical system before repeats"],
        "ranking_excluded": ["DFT energies", "hull distances", "band gaps", "model predictions", "candidate outcomes"],
        "selected": selected, "reserves": reserves, "stretch": reserves[:2],
        "selected_and_reserve_chemical_systems": sorted({row["chemical_system"] for row in selected + reserves}),
        "reserved_chemical_systems_all_seeds": reserved_superset(),
        "catalog_scope": ["full released WBM 256963 records", "MP 2023-02-07 archive, database release 2022.10.28"],
        "not_a_claim": "Absent from these snapshots is not global novelty or absence from generator training data.",
        "prototype_baseline_formula_subset": [row["formula"] for row in selected[:4]],
        "prototype_baseline_rule": "For first four selected formulas only; compatible exact stoichiometry and <=20-atom parent cell; common-oxidation-state-compatible element mapping, then summed absolute atomic-number distance, site count, numeric material ID, mapping tie-break. No energy filters. Missing templates mean no attempt."}
    with (COMPS / "enumerated_and_screened.jsonl").open("w", encoding="utf-8") as output:
        for row in screened: output.write(json.dumps(row, sort_keys=True) + "\n")
    write_json(COMPS / "selection.json", payload)
    print(json.dumps({"event": "selection_frozen", "selected": [{"formula": row["formula"], "system": row["chemical_system"]} for row in selected],
                      "reserves": [row["formula"] for row in reserves], "new_to_both": len(absent)}, indent=2), flush=True)
    return payload


def freeze_controls(candidates):
    decorated = []
    for row in candidates:
        structure = Structure.from_dict(row["structure"])
        analyzer = SpacegroupAnalyzer(structure, symprec=0.01, angle_tolerance=5.0)
        conventional = analyzer.get_conventional_standard_structure()
        sg = SpacegroupAnalyzer(conventional, symprec=0.01, angle_tolerance=5.0).get_space_group_number()
        decorated.append({**row, "measured_spacegroup": int(sg),
                          "conventional_n_sites": len(conventional), "conventional_structure": conventional})
    controls = []
    for reduced, target, sg, count, label in [("MgO", "Mg4O4", 225, 8, "mgo_rocksalt"),
                                            ("TiO2", "Ti2O4", 136, 6, "tio2_rutile")]:
        matches = [row for row in decorated if row["formula"] == reduced and row["measured_spacegroup"] == sg and row["conventional_n_sites"] == count]
        matches.sort(key=lambda row: (row["n_sites"], int(row["material_id"].split("-")[1])))
        if not matches: raise RuntimeError(f"No metadata-verified control for {label}")
        row = matches[0]; structure = row["conventional_structure"]
        structure.to(filename=str(CONTROLS / f"{label}_reference.cif"), fmt="cif")
        write_json(CONTROLS / f"{label}_reference.json", structure.as_dict())
        controls.append({"label": label, "material_id": row["material_id"], "entry_id": row["entry_id"],
            "source_raw_index": row["raw_index"], "conditioning_formula": reduced, "evaluated_formula": target,
            "exact_element_counts": {element: int(amount) for element, amount in structure.composition.get_el_amt_dict().items()},
            "evaluated_n_atoms": count, "chemical_system": row["chemical_system"],
            "nontrivial_spacegroup": sg, "comparison_spacegroup": 1,
            "reference_cif": f"artifacts/phase2/controls/{label}_reference.cif",
            "reference_json": f"artifacts/phase2/controls/{label}_reference.json",
            "selection_rule": "Composition, detected group, conventional cell count; then source site count and numeric material ID. No energy used.",
            "note": "MgO's exact SG225/eight-atom setting yields one rocksalt topology; do not count lattice strain as distinct phases." if sg == 225 else "Rutile has an internal oxygen-coordinate degree of freedom; this does not guarantee several distinct polymorphs."})
    phase1 = json.loads((ROOT / "artifacts/phase1/generator/config.json").read_text(encoding="utf-8"))
    protocol = {"version": "phase2-symmetry-controls-v1", "controls": controls,
        "source_revision": phase1["source_revision"], "checkpoint_revision": phase1["checkpoint_revision"],
        "checkpoint_sha256": phase1["checkpoint_sha256"], "seed": 20261022, "batch_size": 4,
        "temperature": 1.0, "top_p": 1.0, "primary_attempts_per_arm_per_formula": 8,
        "total_primary_attempts": 32, "phase1_mgo_nontrivial_attempts_already_consumed": 8,
        "remaining_primary_attempts": 24,
        "validation": {"exact_expanded_element_counts": True, "expanded_atom_cap": 20,
            "minimum_distance_angstrom": phase1["minimum_distance_angstrom"],
            "symprec_angstrom": 0.01, "angle_tolerance_degrees": 5.0,
            "deduplication": phase1["deduplication"]},
        "relaxation_selection": "Seeded random selection among valid unique outputs before energies; balanced within-formula quota. MgO at most one unique topology per arm; rutile up to four. No extra attempts in Phase 2.",
        "supplementary_topups": "Both arms equally, before final random relaxation selection; separate from first-eight primary yield denominator and within global 128 attempts.",
        "interpretation": "Sampling/conditioning contrast within same trained architecture; no generator-architecture causal claim."}
    write_json(CONTROLS / "matched_protocol.json", protocol)
    # Candidate reference inventory only; parent ranking contains no energy.
    references = []
    for formula, sg, label in [("MgO", 225, "rocksalt"), ("TiO2", 136, "rutile"),
                               ("TiO2", 141, "anatase"), ("TiO2", 61, "brookite")]:
        matches = sorted([row for row in decorated if row["formula"] == formula and row["measured_spacegroup"] == sg],
                         key=lambda row: (row["conventional_n_sites"], int(row["material_id"].split("-")[1])))
        allowed = [row for row in matches if row["conventional_n_sites"] <= 20]
        chosen = allowed[0] if allowed else None
        ref = {"phase": label, "formula": formula, "spacegroup": sg, "eligible_at_most_20_atoms": bool(chosen),
               "minimum_catalog_conventional_sites": matches[0]["conventional_n_sites"] if matches else None,
               "material_id": chosen["material_id"] if chosen else None}
        if chosen:
            path = CONTROLS / f"same_composition_{label}_reference.cif"
            chosen["conventional_structure"].to(filename=str(path), fmt="cif")
            ref["reference_cif"] = path.relative_to(ROOT).as_posix()
        references.append(ref)
    write_json(CONTROLS / "same_composition_reference_plan.json", {"maximum_attempts": 4, "references": references,
               "missing_or_oversize_reference": "No replacement selected from energies; slot remains unused unless separately predeclared."})


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--offline", action="store_true"); args = parser.parse_args()
    for directory in (MP.parent, DATA, ART, COMPS, CONTROLS): directory.mkdir(parents=True, exist_ok=True)
    ensure_mp(args.offline)
    files = {}
    for key, path in [("mp", MP), ("wbm", WBM)]:
        files[key] = hashes(path)
        if files[key]["md5"] != EXPECTED_MD5[path.name]: raise RuntimeError(f"Checksum mismatch: {path}")
    wbm_set, mp_set, metadata = build_catalogs()
    manifest = {"created_utc": now(), "registry_revision": REGISTRY_REVISION,
        "registry_file": f"data/wbm/data-files-{REGISTRY_REVISION}.yml", "files": files,
        **{key: value for key, value in metadata.items() if key != "control_geometries"},
        "wbm_columns_selected": ["material_id", "formula"],
        "mp_fields_selected": ["composition", "entry_id", "data.material_id", "structure", "raw index"],
        "excluded_from_ranking": ["energy", "correction", "energy_adjustments", "all DFT labels"],
        "mp_source": "Figshare file 40344436; MP database release 2022.10.28, queried 2023-02-07",
        "coverage": "Complete records in the two downloaded snapshots, not a current or universal materials catalog."}
    write_json(ART / "catalog_manifest.json", manifest)
    freeze_compositions(wbm_set, mp_set)
    freeze_controls(metadata["control_geometries"])
    from phase2_catalogs_finalize import main as finalize
    finalize()
    print(json.dumps({"event": "catalog_and_control_freeze_completed", "utc": now(), "counts": {key:value for key,value in metadata.items() if key != "control_geometries"}}, indent=2))


if __name__ == "__main__": main()
