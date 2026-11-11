"""Run a predeclared bounded sequence of fixed-geometry cutoff/k-point probes."""
from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

from phase3_qe import ROOT, ART, digest, prepare, execute, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-job", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--final-geometry-check", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=150)
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 900:
        raise ValueError("Probe timeout must be between one and 900 seconds")
    base = json.loads((ART / args.base_job / "result.json").read_text())
    if not base["result"]["job_scf_accepted"]:
        raise RuntimeError("Cannot probe a failed base geometry")
    geometry = ART / args.base_job / "final_geometry.json"
    probes = [("cut60", 1.2, 0.60), ("cut75", 1.5, 0.60), ("k045", 1.5, 0.45), ("k035", 1.5, 0.35)]
    if args.final_geometry_check:
        accepted_cutoff = base["provenance"]["settings"]["ecutwfc_Ry"]
        lower = max(value for value in [50, 60, 75, 90, 105] if value < accepted_cutoff)
        probes = [(f"final_cut{lower}", lower / 50, 0.35),
                  ("final_k045", accepted_cutoff / 50, 0.45)]
    results = []
    for suffix, multiplier, spacing in probes:
        job_id = f"p3_{args.label}_{suffix}"
        parsed_args = SimpleNamespace(job_id=job_id, reference_id=None,
            geometry=str(geometry.relative_to(ROOT)), expected_geometry_sha256=digest(geometry),
            selection_manifest=base["provenance"].get("selection_manifest"), role="sensitivity", calculation="scf",
            cutoff_multiplier=multiplier, k_spacing=spacing, max_seconds=args.max_seconds,
            outer_timeout=args.max_seconds + 30)
        directory, staged = prepare(parsed_args)
        status = execute(directory, staged)
        result = json.loads((directory / "result.json").read_text())
        results.append({"job_id": job_id, "settings": staged["settings"],
                        "elapsed_wall_seconds": result["elapsed_wall_seconds"], "result": result["result"]})
        if status != 0:
            break
    summary = {"base_job": args.base_job, "fixed_geometry_sha256": digest(geometry), "probes": results,
               "interpretation": "Fixed geometry checks; final accepted setting must also satisfy force/full-stress stationarity. If re-relaxed, repeat convergence checks at the new final geometry."}
    save(ART / f"{args.label}_sensitivity.json", summary)
    print(json.dumps({"label": args.label, "completed_probes": len(results),
                      "jobs": [{"job_id": row["job_id"], "energy_eV_per_atom": row["result"].get("energy_eV_per_atom"),
                                "max_stress_kbar": row["result"].get("max_absolute_residual_stress_component_kbar"),
                                "stationary": row["result"].get("job_stationary_at_this_setting")} for row in results]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
