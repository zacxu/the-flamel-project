"""One authorized balanced supplementary MgO pair; primary results stay fixed."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase4/generation/supplementary_mgo"
PRIMARY = ROOT / "artifacts/phase4/generation"
SAMPLER = ROOT / "scripts/phase4_supplementary_generate.py"
sys.path.insert(0, str(ROOT))
def utc(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rel(path): return path.relative_to(ROOT).as_posix()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")

def freeze():
    if (OUT / "run_plan.json").exists(): raise RuntimeError("Supplementary plan already frozen")
    assert read(PRIMARY / "sampling_complete.json")["actual_new_draws"] == 64
    primary = read(PRIMARY / "summary.json")
    assert read(PRIMARY / "audit.json")["status"] == "passed"
    p1 = next(item for item in primary["controls"] if item["control"] == "mgo_rocksalt" and item["arm"] == "p1")
    assert p1["valid_count"] == 0 and p1["attempts"] == 8
    plan = {"status": "frozen_before_supplementary_draws", "frozen_at_utc": utc(),
        "reason": "MgO P1 primary arm has zero exact-cell valid candidates; one balanced pair may enable the later within-formula relaxation comparison.",
        "authorization_scope": "Exactly four supplementary draws per MgO arm, once. No TiO2 topups, no formula stretch, no further draw regardless of outcome.",
        "primary_attempts_unchanged": 80, "primary_new_draws_phase4_unchanged": 64,
        "actual_new_supplementary_draws": 8, "charged_supplementary_slots": 8,
        "sampling_seed": 20261022, "batch_index": 2, "batch_size": 4,
        "key_rule": "jax.random.fold_in(jax.random.PRNGKey(20261022), 2)",
        "primary_batches_resampled": False,
        "sampler_source": {"path": rel(SAMPLER), "sha256": sha(SAMPLER), "snapshot": rel(OUT / "executed_sampler.py")},
        "base_primary_sampler_source": {"path": "scripts/phase3_generate.py", "sha256": sha(ROOT / "scripts/phase3_generate.py")},
        "orchestrator_source_sha256": sha(Path(__file__)),
        "frozen_primary_artifacts": [{"path": rel(PRIMARY / name), "sha256": sha(PRIMARY / name)}
                                      for name in ("run_plan.json", "sampling_complete.json", "summary.json", "audit.json")],
        "source_protocol": {"path": "artifacts/phase2/controls/matched_protocol.json",
                            "sha256": sha(ROOT / "artifacts/phase2/controls/matched_protocol.json")},
        "arms": [{"arm": arm, "spacegroup": group, "attempts": 4,
            "run_id": f"phase4_supplementary_mgo_rocksalt_{arm}",
            "candidate_ids": [f"phase4_supplementary_mgo_rocksalt_{arm}_attempt_{i:03d}" for i in range(8,12)],
            "output_dir": rel(OUT / arm)} for arm, group in (("nontrivial",225),("p1",1))],
        "cpu_affinity_mask": "0xF", "cohorts_concurrent": 1,
        "relaxation_selection": "No selection or relaxation here. Later seeded selection must use within-arm combined deduplicated pools and equal quotas, labelled supplementary."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "executed_sampler.py").write_bytes(SAMPLER.read_bytes())
    (OUT / "executed_orchestrator.py").write_bytes(Path(__file__).read_bytes())
    write(OUT / "run_plan.json", plan)
    print(json.dumps({"frozen": True, "plan_sha256": sha(OUT/"run_plan.json"), "draws":8}),flush=True)

def verify(plan):
    assert sha(SAMPLER) == plan["sampler_source"]["sha256"] == sha(OUT / "executed_sampler.py")
    assert sha(OUT / "executed_orchestrator.py") == plan["orchestrator_source_sha256"]
    for item in plan["frozen_primary_artifacts"] + [plan["source_protocol"], plan["base_primary_sampler_source"]]:
        assert sha(ROOT / item["path"]) == item["sha256"], item

def run():
    plan = read(OUT / "run_plan.json"); verify(plan)
    if (OUT / "dispatch_started.json").exists(): raise RuntimeError("Supplementary pair already dispatched; no repeated sampling")
    write(OUT / "dispatch_started.json", {"utc":utc(),"run_plan_sha256":sha(OUT/"run_plan.json")})
    results=[]
    for arm in plan["arms"]:
        verify(plan)
        command=[str(ROOT/".envs/generator/Scripts/python.exe"),"-u",str(SAMPLER),
            "--control","mgo_rocksalt","--arm",arm["arm"],"--run-id",arm["run_id"],
            "--output",arm["output_dir"],"--phase","4","--timeout-seconds","600"]
        write(OUT/f"dispatch_{arm['arm']}.json",{"utc":utc(),"command":command,"candidate_ids":arm["candidate_ids"]})
        with (OUT/f"supervisor_{arm['arm']}.log").open("wb") as stream:
            proc=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=False)
        directory=ROOT/arm["output_dir"]
        summary=read(directory/"summary.json") if (directory/"summary.json").exists() else {}
        result={"arm":arm["arm"],"returncode":proc.returncode,"completed_at_utc":utc(),
            "actual_attempts":summary.get("attempts",0),"valid_count":summary.get("valid_count",0),
            "valid_unique_count":summary.get("valid_unique_count",0)}
        results.append(result); write(OUT/"progress.json",{"arms":results});print(json.dumps(result),flush=True)
        if proc.returncode: raise RuntimeError("Supplementary failure retained; no automatic retry")
    write(OUT/"sampling_complete.json",{"utc":utc(),"arms":results,"actual_draws":8,"charged_attempts":8})

def audit():
    plan=read(OUT/"run_plan.json");verify(plan)
    os.environ["JAX_PLATFORMS"]="cpu"
    for key in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"):os.environ[key]="4"
    import ctypes
    if os.name=="nt":
        kernel=ctypes.WinDLL("kernel32",use_last_error=True);kernel.GetCurrentProcess.restype=ctypes.c_void_p
        kernel.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
        assert kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(),0xF)
    import numpy as np
    from pymatgen.core import Structure,Lattice,Composition
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.io.cif import CifParser
    from scipy.optimize import linear_sum_assignment
    sys.path.insert(0,str(ROOT/"vendor/CrystalFormer"))
    from crystalformer.src.wyckoff import symops,mult_table,wmax_table
    matrices,multiplicity,max_w=np.asarray(symops),np.asarray(mult_table),np.asarray(wmax_table)
    matcher=StructureMatcher(**read(ROOT/plan["source_protocol"]["path"])["validation"]["deduplication"])
    strict_matcher=StructureMatcher(ltol=1e-4,stol=1e-4,angle_tol=1e-3,primitive_cell=False,scale=False,attempt_supercell=False)
    checks=0
    def check(value,message):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError(message)
    def expand(raw):
        atoms,coords=[],[];g=int(raw["G"])
        for z,w,point in zip(raw["A"],raw["W"],raw["XYZ"]):
            z,w=int(z),int(w)
            if not z:continue
            general=int(max_w[g-1]);number=int(multiplicity[g-1,general])
            orbit=(matrices[g-1,general,:number]@np.r_[point,1.])%1.
            op=matrices[g-1,w,0];delta=orbit@op[:,:3].T+op[:,3]-orbit;delta-=np.rint(delta)
            generator=orbit[np.argmin((delta**2).sum(axis=1))];number=int(multiplicity[g-1,w])
            positions=(matrices[g-1,w,:number]@np.r_[generator,1.])%1.
            atoms.extend([z]*number);coords.extend(positions.tolist())
        return Structure(Lattice.from_parameters(*map(float,raw["L"])),atoms,coords)
    def minimum(structure):
        distances=structure.distance_matrix.copy();np.fill_diagonal(distances,np.inf)
        pairs=float(distances.min()) if len(structure)>1 else float("inf")
        reduced=structure.lattice.get_lll_reduced_lattice()
        images=reduced.get_points_in_sphere([[0.,0.,0.]],[0.,0.,0.],min(reduced.abc)+1e-7)
        return min(pairs,min(float(item[1]) for item in images if float(item[1])>1e-8))
    primary=read(PRIMARY/"summary.json");arms=[]
    for case in plan["arms"]:
        directory=ROOT/case["output_dir"];config=read(directory/"config.json");summary=read(directory/"summary.json")
        check(config["case"]["attempts"]==4 and config["sampling_batch_indices"]==[2],"wrong supplemental shape/key")
        check(config["case"]["sampling_seed"]==20261022 and config["case"]["spacegroup"]==case["spacegroup"],"seed/group changed")
        check(config["candidate_ids"]==case["candidate_ids"],"supplementary candidate IDs changed")
        ticket=read(directory/"reservation.json");check(ticket["attempts"]==4,"must reserve exactly four, not eight")
        check(read(directory/"finish.json")["status"]=="completed","supplementary arm incomplete")
        check(read(directory/"verification.json")["script_sha256"]==plan["sampler_source"]["sha256"],"executed sampler mismatch")
        ledger=[json.loads(line) for line in (directory/"ledger.jsonl").read_text(encoding="utf-8").splitlines()]
        check([r["candidate_id"] for r in ledger if r["event"]=="attempt_started"]==case["candidate_ids"],"supplementary dispatch not four unique candidates")
        check(len(summary["results"])==4 and len(summary["batch_timings"])==1 and summary["batch_timings"][0]["batch_index"]==2,"extra or missing batches")
        batch=np.load(directory/"raw_batch_02.npz");rows=[];representatives=[]
        for item in summary["results"]:
            index=item["attempt_id"];raw=read(ROOT/item["raw_json"])
            for name in ("G","XYZ","A","W","M","L"):check(np.array_equal(np.asarray(raw[name]),batch[name][index]),"raw JSON/NPZ differs")
            structure=Structure.from_dict(read(ROOT/item["structure_json"]));rebuilt=expand(raw)
            check(np.array_equal(rebuilt.atomic_numbers,structure.atomic_numbers) and np.allclose(rebuilt.lattice.matrix,structure.lattice.matrix,atol=1e-9) and np.allclose(rebuilt.frac_coords,structure.frac_coords,atol=1e-9),"raw expansion differs")
            cif=CifParser(ROOT/item["cif"],frac_tolerance=0).parse_structures(primitive=False)[0]
            check(strict_matcher.fit(structure,cif),"CIF roundtrip fails")
            check(np.allclose(structure.lattice.matrix,cif.lattice.matrix,atol=1e-6,rtol=0),"CIF lattice differs")
            check(structure.composition==cif.composition and len(structure)==len(cif),"CIF species/count differs")
            for atomic_number in sorted(set(structure.atomic_numbers)):
                si=[i for i,z in enumerate(structure.atomic_numbers) if z==atomic_number]
                ci=[i for i,z in enumerate(cif.atomic_numbers) if z==atomic_number]
                distances=structure.lattice.get_all_distances(structure.frac_coords[si],cif.frac_coords[ci])
                rj,cj=linear_sum_assignment(distances)
                check(bool((distances[rj,cj]<=1e-5).all()),"CIF periodic Cartesian coordinates differ")
            counts={k:int(v) for k,v in structure.composition.get_el_amt_dict().items()};distance=minimum(structure)
            exact=counts=={"Mg":4,"O":4} and len(structure)==8
            geometry=distance>=.75 and math.isfinite(structure.volume) and structure.volume>0
            valid=exact and geometry and len(structure)<=20
            check(valid==item["valid"],"primary validation gate changed")
            check(int(raw["G"])==case["spacegroup"]==config["case"]["spacegroup"],"raw group changed")
            check(SpacegroupAnalyzer(structure,symprec=.01,angle_tolerance=5.).get_space_group_number()==item["measured_spacegroup"],"measured symmetry differs")
            duplicate=next((candidate_id for candidate_id,other in representatives if matcher.fit(structure,other)),None) if valid else None
            if valid:
                check(duplicate==item["duplicate_of"],"within-supplement dedup differs")
                if duplicate is None:representatives.append((item["candidate_id"],structure))
            rows.append({**item,"structure_sha256":sha(ROOT/item["structure_json"]),"cif_sha256":sha(ROOT/item["cif"]),
                "raw_sha256":sha(ROOT/item["raw_json"]),"audited_valid":valid,"audited_duplicate_of":duplicate,
                "cif_roundtrip":True,"raw_expansion_verified":True,
                "reduced_formula_geometry_valid_within_atom_cap_diagnostic_only":structure.composition.reduced_composition==Composition("MgO") and geometry and len(structure)<=20})
        batch.close()
        primary_arm=next(item for item in primary["controls"] if item["control"]=="mgo_rocksalt" and item["arm"]==case["arm"])
        combined=[];combined_structures=[]
        for item in primary_arm["results"]+rows:
            if not item["audited_valid"]:continue
            structure=Structure.from_dict(read(ROOT/item["structure_json"]))
            if not any(matcher.fit(structure,other) for other in combined_structures):
                combined.append(item);combined_structures.append(structure)
        arms.append({"arm":case["arm"],"spacegroup":case["spacegroup"],"attempts":4,"charged_attempts":4,
            "valid_count":sum(item["audited_valid"] for item in rows),"valid_unique_count":len(representatives),
            "primary_valid_count":primary_arm["valid_count"],"primary_attempts":8,
            "combined_primary_plus_supplementary_attempts":12,"combined_valid_unique_count":len(combined),
            "combined_valid_unique_representatives":combined,"results":rows,"batch_timings":summary["batch_timings"],
            "summary_path":rel(directory/"summary.json"),"summary_sha256":sha(directory/"summary.json"),
            "recorded_run_wall_seconds":read(directory/"finish.json")["job_wall_seconds"],
            "reduced_formula_geometry_valid_within_atom_cap_diagnostic_only":sum(item["reduced_formula_geometry_valid_within_atom_cap_diagnostic_only"] for item in rows)})
    result={"status":"completed","audited_at_utc":utc(),"supplementary_only":True,"new_actual_draws":8,"charged_attempts":8,
        "primary_denominators_unchanged":True,"primary_run_plan_sha256":sha(PRIMARY/"run_plan.json"),
        "run_plan_sha256":sha(OUT/"run_plan.json"),"arms":arms,
        "balanced_later_relaxation_quota_per_arm":min(1,*(item["combined_valid_unique_count"] for item in arms)),
        "more_topups_authorized":False,"interpretation":"Extra yields are supplementary. Pooled relaxation comparisons must use equal within-formula quotas and seeded random selection before energies."}
    write(OUT/"summary.json",result)
    write(OUT/"audit.json",{"status":"passed","audited_at_utc":utc(),"checks_passed":checks,"model_draws_in_audit":0,
        "actual_supplementary_draws":8,"charged_supplementary_attempts":8,"four_slot_reservations_verified":True,
        "unused_batch_index_2_only":True,"primary_artifacts_unchanged":True,"summary_sha256":sha(OUT/"summary.json"),
        "cif_parser_options":{"frac_tolerance":0,"primitive":False},
        "cif_roundtrip_tolerances":{"lattice_matrix_absolute_angstrom":1e-6,"species_matched_periodic_cartesian_angstrom":1e-5},
        "audit_source_sha256":sha(Path(__file__))})
    print(json.dumps({"audit":"passed","checks":checks,"arms":[{"arm":item["arm"],"valid":item["valid_count"],"combined_unique":item["combined_valid_unique_count"]} for item in arms],"balanced_later_quota":result["balanced_later_relaxation_quota_per_arm"]}),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=["freeze","run","audit"])
    {"freeze":freeze,"run":run,"audit":audit}[parser.parse_args().action]()
