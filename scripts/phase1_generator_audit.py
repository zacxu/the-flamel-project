"""Validate saved Phase 1 artifacts without generating further candidates."""
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.analysis.structure_matcher import StructureMatcher

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase1/generator"
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
config = json.loads((OUT / "config.json").read_text(encoding="utf-8"))
ledger = [json.loads(line) for line in (OUT / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
started = [row for row in ledger if row["event"] == "attempt_started"]
completed = [row for row in ledger if row["event"] == "attempt_completed"]
assert len(started) == len(completed) == summary["attempts"] == 8
assert sorted(row["attempt_id"] for row in started) == list(range(8))
assert len({row["attempt_id"] for row in completed}) == 8
assert config["formula"] == "Mg4O4" and config["conditioning_formula"] == "MgO"
assert all((ROOT / row["raw_path"]).is_file() for row in completed)

matcher = StructureMatcher(**config["deduplication"])
checks = []
for row in summary["results"]:
    original = Structure.from_dict(json.loads((ROOT / row["structure_json"]).read_text(encoding="utf-8")))
    roundtrip = Structure.from_file(ROOT / row["cif"])
    assert original.composition == roundtrip.composition
    assert len(original) == len(roundtrip) == row["n_atoms"]
    assert matcher.fit(original, roundtrip)
    assert np.allclose(original.lattice.matrix, roundtrip.lattice.matrix, atol=1e-5)
    sg = SpacegroupAnalyzer(roundtrip, symprec=0.01, angle_tolerance=5.0).get_space_group_number()
    assert sg == row["measured_spacegroup"] == 225
    counts = {symbol: int(number) for symbol, number in roundtrip.composition.get_el_amt_dict().items()}
    assert counts == row["counts"]
    if row["valid"]:
        assert counts == {"Mg": 4, "O": 4} and len(roundtrip) == 8
    checks.append({"attempt_id": row["attempt_id"], "cif_roundtrip_pass": True,
                   "measured_spacegroup": sg, "exact_count_match": counts == {"Mg": 4, "O": 4}})

assert sum(check["exact_count_match"] for check in checks) == summary["valid_exact_count_structures"] == 7
assert len(list((OUT / "cifs").glob("*.cif"))) == 8
assert len(list(OUT.glob("raw_batch_*.npz"))) == 2
audit = {"audited_utc": datetime.now(timezone.utc).isoformat(),
         "no_additional_sample_attempts": True, "ledger_consistent": True,
         "cif_roundtrips": checks, "checks_passed": True,
         "notes": ["All eight outputs remain available, including the 12-atom Mg4O8 mismatch.",
                   "Seven exact-count outputs represent one rocksalt topology after structural deduplication.",
                   "This is known-control generation evidence, not energetic or novelty validation."]}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
with (OUT / "attempts.csv").open("w", newline="", encoding="utf-8") as stream:
    fields = ["attempt_id", "valid", "n_atoms", "counts", "volume_angstrom3", "minimum_distance_angstrom",
              "measured_spacegroup", "duplicate_of", "rejection_reasons", "cif"]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(summary["results"])
print(json.dumps({"checks_passed": True, "attempts": 8, "exact_count_valid": 7,
                  "unique_topologies": 1, "cif_roundtrips": 8}))
