"""Validate actual W4 browser-downloaded CIF bytes against pinned saved source files.

No generated test fixture, rendering helper or CIF export function is imported.
The browser files must be copied into reports/structure-downloads/ before running.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import warnings

import numpy as np
from pymatgen.core import Structure
from pymatgen.io.cif import CifFile, CifParser

warnings.filterwarnings("ignore", message="gcd is deprecated.*", category=FutureWarning)
WEBSITE = Path(__file__).resolve().parents[1]
ROOT = WEBSITE.parent
CHECKS = []


def check(condition, description):
    CHECKS.append({"check": description, "passed": bool(condition)})
    if not condition:
        raise ValueError(description)


def sha(value):
    return hashlib.sha256(value).hexdigest()


baseline = json.loads((WEBSITE / "reports/W4_BASELINE.json").read_text(encoding="utf-8"))
export = json.loads((WEBSITE / "reports/W1_EXPORT.json").read_text(encoding="utf-8"))
# Read the exact release wired into the UI, never the mutable discovery pointer.
release_source = (WEBSITE / "src/data/release.ts").read_text(encoding="utf-8")
release = json.loads(re.search(r"export const DATA_RELEASE = (\{.*?\}) as const;", release_source, re.S).group(1))
manifest_bytes = (WEBSITE / "public" / release["manifestPath"]).read_bytes()
check(sha(manifest_bytes) == release["manifestSha256"] == baseline["manifestSha256"], "Browser UI uses the same hash-pinned saved data manifest")
check(release["dataReleaseId"] == baseline["dataReleaseId"] == export["dataReleaseId"], "Download validation binds the current UI release to the frozen W4 baseline")
manifest = json.loads(manifest_bytes)
source_by_id = {value["sourceId"]: value for value in export["inputAllowlist"].values()}


def read_public(logical):
    file = next(entry for entry in manifest["files"] if entry["logicalName"] == logical)
    content = (WEBSITE / "public/research" / file["path"]).read_bytes()
    check(sha(content) == file["sha256"], "Pinned saved registry payload hash: " + logical)
    return json.loads(content)


index = read_public("structures/index.json")
stages = {entry["stageId"]: entry for entry in index["stages"]}
for name, expected in baseline["sourceHashes"].items():
    check(sha((ROOT / name).read_bytes()) == expected, "Frozen original input before actual download verification: " + name)

files = sorted((WEBSITE / "reports/structure-downloads").glob("*.cif"))
check(len(files) >= 6, "At least six actual browser CIF downloads are retained for distinct scientific examples")
downloads = []
coverage = set()
for file in files:
    downloaded_bytes = file.read_bytes()
    text = downloaded_bytes.decode("utf-8-sig")
    check(not re.search(r"[A-Za-z]:[\\/]|\\Users\\|/Users/", text, re.I), "Browser CIF contains no absolute local paths: " + file.name)
    blocks = CifFile.from_str(text).data
    check(len(blocks) == 1, "One explicit saved structure per browser CIF: " + file.name)
    block = next(iter(blocks.values())).data
    stage_id = block.get("_flamel_stage_id")
    check(stage_id in stages, "Browser CIF identifies an actual recorded saved stage: " + file.name)
    stage = read_public(stages[stage_id]["logicalFile"])
    source = source_by_id[stage["sourceId"]]
    original_bytes = (ROOT / source["path"]).read_bytes()
    check(sha(original_bytes) == stage["sourceSha256"] == source["sha256"] == baseline["sourceHashes"][source["path"]], "Browser CIF comparison uses original hash-bound geometry: " + stage_id)
    original = json.loads(original_bytes)
    saved = Structure.from_dict(original)
    basis = np.asarray(original["lattice"]["matrix"])
    fractional = np.asarray([site["abc"] for site in original["sites"]])
    name = stage_id
    check(stage_id in file.name, "Browser filename retains the selected stage identity: " + file.name)
    expected_metadata = {
        "_flamel_study_id": stage["studyId"],
        "_flamel_data_release_id": release["dataReleaseId"],
        "_flamel_candidate_id": stage["candidateId"],
        "_flamel_stage_id": stage_id,
        "_flamel_stage_kind": stage["stage"],
        "_flamel_method": stage["method"],
        "_flamel_source_id": stage["sourceId"],
        "_flamel_source_sha256": stage["sourceSha256"],
        "_flamel_excluded": "yes" if stage["eligibility"]["excluded"] else "no",
        "_flamel_exact_cell_eligible": "?" if stage["eligibility"]["exactCellEligible"] is None else "yes" if stage["eligibility"]["exactCellEligible"] else "no",
        "_flamel_queue_selected": "yes" if stage["eligibility"]["queueSelected"] else "no",
        "_flamel_physical_sites": str(len(saved)),
        "_flamel_global_novelty_established": "no",
        "_flamel_new_stable_material_established": "no",
        "_flamel_pbc_a": "yes", "_flamel_pbc_b": "yes", "_flamel_pbc_c": "yes",
    }
    for key, expected in expected_metadata.items():
        check(block.get(key) == expected, f"Browser CIF saved provenance/eligibility {name}: {key}")
    for key, value in [("_flamel_recorded_spacegroup_number", stage["symmetry"]["spacegroupNumber"]),
                       ("_flamel_recorded_symprec_angstrom", stage["symmetry"]["symprecAngstrom"]),
                       ("_flamel_recorded_angle_tolerance_degrees", stage["symmetry"]["angleToleranceDegrees"])]:
        check((block.get(key) == "?" if value is None else float(block.get(key)) == value), f"Browser CIF retains stage-specific SG/tolerance, including null: {name}/{key}")
    check(block["_space_group_IT_number"] == "1" and block["_space_group_symop_operation_xyz"] == ["x,y,z"], "Browser CIF P1 explicit-site representation does not invent symmetry expansion: " + name)
    raw_fractional = np.asarray([[float(block[key][i]) for key in ["_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z"]] for i in range(len(saved))])
    check(np.array_equal(raw_fractional, fractional), "Browser CIF preserves full-precision raw unwrapped fractional coordinates in source order: " + name)
    raw_basis = np.asarray([[float(block[key][i]) for key in ["_flamel_lattice_x_angstrom", "_flamel_lattice_y_angstrom", "_flamel_lattice_z_angstrom"]] for i in range(3)])
    check(np.array_equal(raw_basis, basis), "Browser CIF custom metadata preserves exact full-precision source basis rows: " + name)
    expected_species = [site["species"][0]["element"] for site in original["sites"]]
    expected_occupancies = [site["species"][0]["occu"] for site in original["sites"]]
    expected_labels = [f"{element}_{i}" for i, element in enumerate(expected_species)]
    check(block["_atom_site_type_symbol"] == expected_species, "Browser CIF exact saved species order: " + name)
    check(np.array_equal([float(value) for value in block["_atom_site_occupancy"]], expected_occupancies), "Browser CIF exact saved occupancies: " + name)
    check(block["_atom_site_label"] == expected_labels, "Browser CIF site-index labels preserve identity: " + name)
    check(np.allclose(raw_fractional @ raw_basis, [site["xyz"] for site in original["sites"]], rtol=0, atol=1e-8), "Browser CIF original basis and coordinates reproduce original Cartesian sites: " + name)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        parsed = CifParser.from_str(text, frac_tolerance=0).parse_structures(primitive=False, symmetrized=False)[0]
    check(len(parsed) == len(saved), "Independent parser preserves browser CIF physical atom count: " + name)
    check(parsed.composition == saved.composition, "Independent parser preserves browser CIF composition: " + name)
    check(np.allclose(parsed.lattice.metric_tensor, saved.lattice.metric_tensor, rtol=0, atol=1e-10), "Independent parser preserves browser CIF standard cell metric: " + name)
    check(np.allclose(parsed.lattice.parameters, saved.lattice.parameters, rtol=0, atol=1e-10), "Independent parser preserves browser CIF standard lengths and angles: " + name)
    check(abs(parsed.volume - saved.volume) < 1e-8, "Independent parser preserves browser CIF cell volume: " + name)
    by_label = {site.label: site for site in parsed}
    check(set(by_label) == set(expected_labels), "Independent parser retains browser CIF source site labels: " + name)
    ordered_fractional = []
    for i, label in enumerate(expected_labels):
        site = by_label[label]
        check(site.species == saved[i].species, f"Independent browser CIF site species/occupancy: {name}/{i}")
        delta = site.frac_coords - saved[i].frac_coords
        check(np.allclose(delta, np.rint(delta), rtol=0, atol=1e-12), f"Independent browser CIF site coordinate modulo integer wrapping: {name}/{i}")
        ordered_fractional.append(site.frac_coords)
    ordered = Structure(parsed.lattice, [site.species for site in saved], ordered_fractional)
    check(np.allclose(ordered.distance_matrix, saved.distance_matrix, rtol=0, atol=1e-8), "Independent parser preserves browser CIF all periodic pair distances: " + name)
    if stage_id == "phase1_mgo_attempt_000--accepted_dft" and len(saved) == 8:
        coverage.add("accepted_generated_MgO_8_atoms")
    if stage["candidateId"] == "prototype_CaMg2O3" and len(saved) == 6:
        coverage.add("separate_CaMg2O3_prototype_6_atoms")
    if stage["eligibility"]["excluded"] and len(saved) == 12:
        coverage.add("excluded_transformer_CaMg2O3_12_atoms")
    gram = basis @ basis.T
    if stage["candidateId"] == "phase4_tio2_rutile_p1_attempt_000" and not np.allclose(gram, np.diag(np.diag(gram)), rtol=0, atol=1e-6):
        coverage.add("nonorthogonal_TiO2_P1")
    if stage_id == "qe_source_reference_mgo_mp1265--accepted_dft" and len(saved) == 2:
        coverage.add("independent_source_MgO_2_atoms")
    if stage_id == "qe_source_reference_cao_mp2605--accepted_dft" and len(saved) == 2:
        coverage.add("independent_source_CaO_2_atoms")
    downloads.append({"file": str(file.relative_to(WEBSITE)).replace("\\", "/"), "sha256": sha(downloaded_bytes),
                      "bytes": len(downloaded_bytes), "stageId": stage_id, "candidateId": stage["candidateId"],
                      "sourceId": stage["sourceId"], "sourceSha256": stage["sourceSha256"],
                      "physicalAtoms": len(saved), "excluded": stage["eligibility"]["excluded"]})

expected_coverage = {"accepted_generated_MgO_8_atoms", "separate_CaMg2O3_prototype_6_atoms", "excluded_transformer_CaMg2O3_12_atoms", "nonorthogonal_TiO2_P1", "independent_source_MgO_2_atoms", "independent_source_CaO_2_atoms"}
check(coverage == expected_coverage, "Actual browser downloads cover all six requested distinct geometry/stage examples")
check(len({item["stageId"] for item in downloads}) >= 6, "Actual browser downloads contain at least six distinct saved stages")
for name, expected in baseline["sourceHashes"].items():
    check(sha((ROOT / name).read_bytes()) == expected, "Frozen original input after actual download verification: " + name)

report = {"phase": "W4", "status": "passed", "generatedAt": datetime.now(timezone.utc).isoformat(),
          "scope": "Actual browser-downloaded CIF bytes independently parsed and compared directly to original saved source geometry; no generated test fixture or rendering/export helper imported.",
          "newExperiments": 0, "dataReleaseId": release["dataReleaseId"], "manifestSha256": release["manifestSha256"],
          "counts": {"files": len(downloads), "distinctSavedStages": len({item["stageId"] for item in downloads}), "checks": len(CHECKS)},
          "coverage": sorted(coverage), "downloads": downloads, "checks": CHECKS,
          "limits": ["Standard CIF cells preserve lattice metric, not arbitrary Cartesian orientation; exact source basis rows are independently preserved as custom metadata.", "P1 is an explicit-site serialization; recorded stage symmetry remains separate metadata and no symmetry inference is performed."]}
(WEBSITE / "reports/W4_DOWNLOAD_VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"W4 actual browser CIF downloads verified: {len(CHECKS)} checks across {len(downloads)} files and six distinct scientific examples.")
