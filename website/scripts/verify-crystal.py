"""Independent numerical/CIF verification; reads saved original bytes, never calls a model."""
from __future__ import annotations
import hashlib
import csv
import json
from pathlib import Path
import sys
import warnings

import numpy as np
from pymatgen.core import Lattice, Structure
from pymatgen.io.cif import CifFile, CifParser

# Existing pymatgen's future gcd migration does not affect these numerical checks.
warnings.filterwarnings("ignore", message="gcd is deprecated.*", category=FutureWarning)

WEBSITE = Path(__file__).resolve().parents[1]
ROOT = WEBSITE.parent
CHECKS = []

def check(name, condition):
    assert bool(condition), name
    CHECKS.append({"check": name, "passed": True})

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
inventory = json.loads((WEBSITE / "reports/W1_EXPORT.json").read_text(encoding="utf-8"))["inputAllowlist"]
with (ROOT / "artifacts/phase6/structures/relaxed_structures.csv").open(encoding="utf-8", newline="") as stream:
    recorded_models = {row["candidate_id"]: row for row in csv.DictReader(stream)}
source_compositions = {}
for item in payload["fixtures"]:
    stage = item["stage"]
    name = stage["stageId"]
    g = stage["geometry"]
    raw_path = ROOT / item["sourcePath"]
    original_bytes = raw_path.read_bytes()
    check(f"Independent original source hash {name}", hashlib.sha256(original_bytes).hexdigest() == stage["sourceSha256"] == inventory[item["sourcePath"]]["sha256"])
    original = json.loads(original_bytes)
    saved = Structure.from_dict(original)
    source_compositions[name] = saved.composition.reduced_composition
    check(f"Saved display never promotes novelty, OOD or stable-material status {name}", not any(stage["novelty"][k] for k in ["globalStructureNoveltyEstablished", "globalCompositionNoveltyEstablished", "generatorPretrainingOODEstablished"]) and not stage["dftValidation"]["newStableMaterialEstablished"] and not stage["dftValidation"]["fullHullEstablished"] and not stage["symmetry"]["newSymmetryInferencePerformed"])
    if stage["stage"] == "model_relaxed":
        row = recorded_models[stage["candidateId"]]
        check(f"Pinned-subset geometry matching is preserved from original result, not recomputed {name}", stage["novelty"]["matchesPinnedGeometryIds"] == json.loads(row["matches_pinned_MP_same_composition_geometry_ids"]) and stage["novelty"]["sameCompositionGeometriesTested"] == int(row["same_composition_MP_geometries_tested"]))
        check(f"Stage-specific saved SG and recorded tolerance {name}", stage["symmetry"]["spacegroupNumber"] == int(row["final_spacegroup_symprec_0p01"]) and stage["symmetry"]["symprecAngstrom"] == .01 and stage["symmetry"]["angleToleranceDegrees"] == 5.)
    basis = np.asarray(original["lattice"]["matrix"])
    frac = np.asarray([s["abc"] for s in original["sites"]])
    check(f"Independent helper row-basis Cartesian positions {name}", np.allclose(item["cartesian"], frac @ basis, atol=1e-12, rtol=0))
    check(f"Independent helper inverse roundtrip {name}", np.allclose((np.asarray(item["cartesian"]) @ np.linalg.inv(basis)), frac, atol=1e-12, rtol=0))
    check(f"Independent helper periodic all-pairs distances {name}", np.allclose(item["distances"], saved.distance_matrix, atol=1e-8, rtol=0))
    check(f"Independent saved volume {name}", abs(np.linalg.det(basis) - g["volumeAngstrom3"]) < 1e-8)
    cif = item["cif"]
    check(f"CIF generated text hash {name}", hashlib.sha256(cif.encode()).hexdigest() == item["cifSha256"])
    block = next(iter(CifFile.from_str(cif).data.values())).data
    check(f"CIF exact raw coordinate columns and site order {name}", np.array_equal(np.asarray([[float(block[k][i]) for k in ["_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z"]] for i in range(len(saved))]), frac))
    check(f"CIF exact raw original basis metadata {name}", np.array_equal(np.asarray([[float(block[k][i]) for k in ["_flamel_lattice_x_angstrom", "_flamel_lattice_y_angstrom", "_flamel_lattice_z_angstrom"]] for i in range(3)]), basis))
    check(f"CIF exact occupancy {name}", np.array_equal([float(n) for n in block["_atom_site_occupancy"]], [s["species"][0]["occu"] for s in original["sites"]]))
    check(f"CIF source species in original site order {name}", block["_atom_site_type_symbol"] == [s["species"][0]["element"] for s in original["sites"]])
    check(f"CIF provenance fields {name}", all(block[k] == value for k, value in [("_flamel_stage_id", name), ("_flamel_source_id", stage["sourceId"]), ("_flamel_source_sha256", stage["sourceSha256"]), ("_flamel_data_release_id", payload["dataReleaseId"])]))
    check(f"CIF explicit-site encoding does not promote recorded SG {name}", block["_space_group_IT_number"] == "1" and block["_space_group_symop_operation_xyz"] == ["x,y,z"])
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        # Disable rational snapping so full precision is tested rather than silently repaired.
        parsed = CifParser.from_str(cif, frac_tolerance=0).parse_structures(primitive=False, symmetrized=False)[0]
    check(f"Pymatgen CIF physical atom count {name}", len(parsed) == len(saved))
    check(f"Pymatgen CIF species composition {name}", parsed.composition == saved.composition)
    check(f"Pymatgen CIF metric tensor {name}", np.allclose(parsed.lattice.metric_tensor, saved.lattice.metric_tensor, atol=1e-10, rtol=0))
    check(f"Pymatgen CIF lattice parameters {name}", np.allclose(parsed.lattice.parameters, saved.lattice.parameters, atol=1e-10, rtol=0))
    check(f"Pymatgen CIF volume {name}", abs(parsed.volume - saved.volume) < 1e-8)
    # Labels bind site identity after the parser's legal species ordering/wrapping.
    by_label = {s.label: s for s in parsed}
    check(f"Pymatgen CIF preserves physical site labels {name}", set(by_label) == set(block["_atom_site_label"]))
    restored = []
    for i, source_site in enumerate(saved):
        label = block["_atom_site_label"][i]
        site = by_label[label]
        check(f"Pymatgen CIF site species and occupancy {name}/{i}", site.species == source_site.species)
        # Pymatgen wraps; compare integer translations, not raw Cartesian orientation.
        difference = site.frac_coords - source_site.frac_coords
        check(f"Pymatgen CIF fractional site modulo lattice translations {name}/{i}", np.allclose(difference, np.rint(difference), atol=1e-12, rtol=0))
        restored.append(site.frac_coords)
    parsed_ordered = Structure(parsed.lattice, [s.species for s in saved], restored)
    check(f"Pymatgen CIF all periodic pair distances {name}", np.allclose(parsed_ordered.distance_matrix, saved.distance_matrix, atol=1e-8, rtol=0))
for edge in payload["edgeCases"]:
    distance = Lattice(edge["lattice"], pbc=edge["pbc"]).get_distance_and_image(edge["a"], edge["b"])[0]
    check(f"Independent pymatgen exact skew-cell edge case {edge['name']}", abs(distance - edge["distance"]) < 1e-12)
stages = {item["stage"]["stageId"]: item["stage"] for item in payload["fixtures"]}
for comparison in payload["comparisons"]:
    left, right = stages[comparison["left"]], stages[comparison["right"]]
    a, b = left["energy"], right["energy"]
    expected = bool(a and b and source_compositions[left["stageId"]] == source_compositions[right["stageId"]] and a["engine"] == b["engine"] and a["unit"] == b["unit"] and a["settingsScope"] == b["settingsScope"] and a["settings"] == b["settings"])
    check(f"Independent energy comparison eligibility {left['stageId']} -> {right['stageId']}", comparison["compatible"] == expected)
    check(f"Independent energy comparison delta {left['stageId']} -> {right['stageId']}", comparison["deltaEVPerAtom"] == (b["value"] - a["value"] if expected else None))
report = {"status": "passed", "scope": "Independent NumPy and pymatgen original-source/CIF read-only checks", "checks": CHECKS}
(WEBSITE / ".cache/w4-cif-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"Independent NumPy/pymatgen: {len(CHECKS)} geometry/CIF/energy checks passed.")
