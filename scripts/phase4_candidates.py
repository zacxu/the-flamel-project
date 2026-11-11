"""Freeze the six-formula initial-geometry shortlist for Phase 5 validation."""
from __future__ import annotations

import os
for _key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_key] = "2"
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "artifacts/phase4/selection"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    import joblib
    import numpy as np
    from pymatgen.core import Structure
    from research_features import describe_structure, FEATURE_NAMES
    from research_models import predict_bundle
    from research_acquisition import transform_diversity, distances_to_labeled, select_fresh_pair

    target = OUT / "fresh_shortlist.json"
    if target.exists():
        raise RuntimeError("Shortlist already committed; do not select again after validation")
    plan = load(ROOT / "artifacts/phase4/execution_plan.json")
    if sha(ROOT / plan["research_protocol"]["path"]) != plan["research_protocol"]["sha256"]:
        raise RuntimeError("Frozen research protocol changed")
    model_path = ROOT / plan["fresh_selector"]["path"]
    if sha(model_path) != plan["fresh_selector"]["sha256"]:
        raise RuntimeError("Original fresh selector changed")
    bundle = joblib.load(model_path)
    if list(bundle["feature_names"]) != list(FEATURE_NAMES):
        raise RuntimeError("Initial-geometry feature schemas differ")
    generation_protocol = load(ROOT / "artifacts/phase2/compositions/generation_protocol.json")
    run_plan = load(ROOT / "artifacts/phase4/generation/run_plan.json")
    cases = run_plan["new_cohorts"]
    formulas, chosen_all, all_features, feature_ids = [], [], [], []
    for case in generation_protocol["formulas"]:
        if case["cohort"] != "default":
            continue
        formula = case["formula"]
        if formula == "CaMg2O3":
            summary_path = ROOT / "artifacts/phase3/generation/early_CaMg2O3/summary.json"
        else:
            cohort = next(row for row in cases if row["kind"] == "new_composition" and row["formula"] == formula)
            summary_path = ROOT / cohort["output_dir"] / "summary.json"
        summary = load(summary_path)
        if summary["attempts"] != 8 or len(summary["results"]) != 8:
            raise RuntimeError("A default formula cohort is incomplete")
        representatives = summary["valid_unique_representatives"]
        ranking, selected = [], []
        if representatives:
            matrices = []
            for row in representatives:
                path = ROOT / row["structure_json"]
                structure = Structure.from_file(path)
                counts = {key: int(value) for key, value in structure.composition.as_dict().items()}
                if counts != case["exact_expanded_counts"] or len(structure) != case["evaluated_n_atoms"]:
                    raise RuntimeError("Representative fails frozen exact evaluated-cell rule")
                matrices.append(describe_structure(structure))
            X = np.vstack(matrices)
            mean, std, radius = predict_bundle(bundle, X)
            diversity = transform_diversity(X, bundle["normalization"])
            distance = distances_to_labeled(diversity, bundle["initial_training_diversity_features"])
            chosen, decisions = select_fresh_pair([r["candidate_id"] for r in representatives], mean, radius, diversity, distance)
            for row, mu, sigma, halfwidth, dist, features in zip(representatives, mean, std, radius, distance, X):
                record = {**row, "formula": formula, "source_structure_sha256": sha(ROOT / row["structure_json"]),
                          "predicted_mean_eV_atom": float(mu), "ensemble_std_eV_atom": float(sigma),
                          "calibrated_radius_eV_atom": float(halfwidth), "distance_to_initial_training": float(dist)}
                ranking.append(record)
                all_features.append(features)
                feature_ids.append(row["candidate_id"])
            selected = [{**ranking[int(index)], "selection": decision} for index, decision in zip(chosen, decisions)]
        formulas.append({"formula": formula, "source_summary": summary_path.relative_to(ROOT).as_posix(),
                         "source_summary_sha256": sha(summary_path), "primary_attempts": 8,
                         "valid_unique_candidates": ranking, "selected": selected})
        chosen_all.extend(selected)
    if len(chosen_all) > 12:
        raise RuntimeError("Fresh shortlist exceeds the original 12-slot allocation")
    # The empty early cohort remains empty. No later formula is substituted into
    # the predeclared CaMg2O3 DFT queue or the historical MgO fallback decision.
    OUT.mkdir(parents=True, exist_ok=True)
    feature_path = OUT / "initial_features.npz"
    matrix = np.vstack(all_features) if all_features else np.empty((0, 408), dtype=np.float32)
    np.savez_compressed(feature_path, X=matrix, candidate_ids=np.array(feature_ids, dtype=str))
    record = {
        "frozen_utc": datetime.now(timezone.utc).isoformat(), "status": "frozen_before_Phase5_CHGNet_or_DFT",
        "research_protocol_sha256": plan["research_protocol"]["sha256"],
        "fresh_selector_path": model_path.relative_to(ROOT).as_posix(), "fresh_selector_sha256": sha(model_path),
        "feature_source_sha256": sha(ROOT / "research_features.py"),
        "acquisition_source_sha256": sha(ROOT / "research_acquisition.py"),
        "selection_source_sha256": sha(Path(__file__)), "formulas": formulas, "selected_in_formula_and_pair_order": chosen_all,
        "selected_count": len(chosen_all), "initial_features": feature_path.relative_to(ROOT).as_posix(),
        "initial_features_sha256": sha(feature_path),
        "prediction_target": "Signed historical WBM distance to fixed MP hull; not compatible new QE hull energy",
        "initial_geometry_only": True, "adapted_or_other_seed_models_used": False,
        "CHGNet_or_QE_energies_used": False, "additional_generation_or_relaxations_in_selection": 0,
        "default_CaMg_DFT_queue_changed": False,
        "phase5_handoff": "Validate each selected candidate once in frozen within-formula order; retain exclusions/collapses without outcome-based replacement",
    }
    target.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "frozen", "formulas": len(formulas), "valid_unique": len(feature_ids), "selected": len(chosen_all)}))


if __name__ == "__main__":
    main()
