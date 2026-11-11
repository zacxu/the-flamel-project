"""Frozen, label-free acquisition and initial-only diversity utilities.

No function in this module can read a dataset, oracle or DFT result. Calibration
receives only the calibration labels explicitly supplied by its caller.
"""
from __future__ import annotations

import math
import numpy as np

POLICIES = ("random", "quality", "quality_diversity", "uncertainty", "full")
THRESHOLD_EV_ATOM = 0.05
ENERGY_SCALE_EV_ATOM = 0.05
UNCERTAINTY_FLOOR_EV_ATOM = 0.01
DIVERSITY_WEIGHT = 0.5
DIVERSITY_DIMENSIONS = 150
INTERVAL_ALPHA = 0.1


def finite_matrix(values, name):
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite two-dimensional array")
    return array


def fit_diversity_normalization(initial_training_features):
    """Fit once on initial training features, without labels or pool statistics."""
    matrix = finite_matrix(initial_training_features, "initial_training_features")[:, :DIVERSITY_DIMENSIONS]
    if matrix.shape[1] != DIVERSITY_DIMENSIONS or len(matrix) == 0:
        raise ValueError("Expected at least 150 columns and one training row")
    center = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale < 1e-12] = 1.0
    return {"center": center, "scale": scale}


def transform_diversity(features, normalization):
    matrix = finite_matrix(features, "features")[:, :DIVERSITY_DIMENSIONS]
    center = np.asarray(normalization["center"])
    scale = np.asarray(normalization["scale"])
    if matrix.shape[1] != DIVERSITY_DIMENSIONS or center.shape != (DIVERSITY_DIMENSIONS,) or scale.shape != center.shape:
        raise ValueError("Diversity schema mismatch")
    if not np.isfinite(center).all() or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError("Invalid normalization")
    return np.clip((matrix - center) / scale, -5.0, 5.0)


def distances_to_labeled(candidates, labeled, chunk_size=256):
    """Minimum RMS Euclidean distance, clipped at one; no labels are inputs."""
    candidates = finite_matrix(candidates, "candidates")
    labeled = finite_matrix(labeled, "labeled")
    if candidates.shape[1] != DIVERSITY_DIMENSIONS or labeled.shape[1] != DIVERSITY_DIMENSIONS or len(labeled) == 0:
        raise ValueError("Expected matching 150-dimensional features and nonempty labeled set")
    result = np.empty(len(candidates))
    labeled_norm = np.einsum("ij,ij->i", labeled, labeled)
    for start in range(0, len(candidates), chunk_size):
        part = candidates[start:start+chunk_size]
        square = np.einsum("ij,ij->i", part, part)[:, None] + labeled_norm[None, :] - 2 * part @ labeled.T
        result[start:start+len(part)] = np.minimum(1.0, np.sqrt(np.maximum(0, square.min(axis=1)) / DIVERSITY_DIMENSIONS))
    return result


def calibrate_uncertainty(calibration_y, calibration_mean, calibration_std, alpha=INTERVAL_ALPHA):
    """Empirical finite-sample-rank residual scaling; no arbitrary-OOD guarantee."""
    y = np.asarray(calibration_y, dtype=np.float64)
    mean = np.asarray(calibration_mean, dtype=np.float64)
    std = np.asarray(calibration_std, dtype=np.float64)
    if y.ndim != 1 or y.shape != mean.shape or y.shape != std.shape or len(y) == 0:
        raise ValueError("Calibration arrays must have matching nonempty one-dimensional shapes")
    if not all(np.isfinite(x).all() for x in (y, mean, std)) or np.any(std < 0) or not 0 < alpha < 1:
        raise ValueError("Invalid calibration values")
    rank = math.ceil((len(y) + 1) * (1 - alpha))
    if rank > len(y):
        raise ValueError("Insufficient calibration rows for a finite requested quantile")
    residual_ratios = np.abs(y - mean) / np.maximum(std, UNCERTAINTY_FLOOR_EV_ATOM)
    q = float(np.partition(residual_ratios, rank-1)[rank-1])
    return {"q": q, "rank_1_based": rank, "n": len(y), "alpha": alpha,
            "floor_eV_atom": UNCERTAINTY_FLOOR_EV_ATOM,
            "coverage_scope": "Empirical calibration; chemical-system shift may violate exchangeability"}


def uncertainty_radius(ensemble_std, calibration):
    std = np.asarray(ensemble_std, dtype=np.float64)
    if not np.isfinite(std).all() or np.any(std < 0) or calibration["q"] < 0:
        raise ValueError("Invalid uncertainty input")
    return calibration["q"] * np.maximum(std, UNCERTAINTY_FLOOR_EV_ATOM)


def select_batch(policy, material_ids, predicted_mean, calibrated_radius,
                 diversity_features, distance_to_known, rng, batch_size=10):
    """Return selected rows and decision evidence, without accepting oracle labels.

    Full policy takes seven conservative choices, then three optimistic choices.
    Diversity is updated after every choice against the current batch as well as
    previously labeled structures. Other policies use the same candidate views.
    """
    if policy not in POLICIES or batch_size != 10:
        raise ValueError("Frozen protocol requires a named policy and batch size ten")
    ids = np.asarray(material_ids, dtype=str)
    mean = np.asarray(predicted_mean, dtype=np.float64)
    radius = np.asarray(calibrated_radius, dtype=np.float64)
    distance = np.asarray(distance_to_known, dtype=np.float64).copy()
    features = finite_matrix(diversity_features, "diversity_features")
    n = len(ids)
    if n < batch_size or len(set(ids)) != n or any(x.shape != (n,) for x in [mean, radius, distance]):
        raise ValueError("Candidate arrays must align, have unique IDs and contain ten rows")
    if features.shape != (n, DIVERSITY_DIMENSIONS) or not all(np.isfinite(x).all() for x in [mean, radius, distance]):
        raise ValueError("Invalid candidate feature/prediction values")
    if np.any(radius < 0) or np.any(distance < 0) or np.any(distance > 1):
        raise ValueError("Radius must be nonnegative and diversity distance in [0,1]")
    available = np.ones(n, dtype=bool)
    random_order = rng.permutation(n) if policy == "random" else None
    selected = []
    decisions = []
    for step in range(batch_size):
        if policy == "random":
            index = int(random_order[step])
            role, score = "random", None
        else:
            if policy == "quality":
                scores, role = (THRESHOLD_EV_ATOM - mean) / ENERGY_SCALE_EV_ATOM, "quality"
            elif policy == "quality_diversity":
                scores, role = (THRESHOLD_EV_ATOM - mean) / ENERGY_SCALE_EV_ATOM + DIVERSITY_WEIGHT * distance, "quality_diversity"
            elif policy == "uncertainty":
                scores, role = radius / ENERGY_SCALE_EV_ATOM, "uncertainty"
            else:
                sign, role = (-1, "conservative") if step < 7 else (1, "optimistic")
                scores = (THRESHOLD_EV_ATOM - mean + sign * radius) / ENERGY_SCALE_EV_ATOM + DIVERSITY_WEIGHT * distance
            candidates = np.flatnonzero(available)
            order = np.lexsort((ids[candidates], -scores[candidates]))
            index = int(candidates[order[0]])
            score = float(scores[index])
        decisions.append({"material_id": str(ids[index]), "position": step,
                          "role": role, "score": score,
                          "predicted_mean_eV_atom": float(mean[index]),
                          "calibrated_radius_eV_atom": float(radius[index]),
                          "diversity_distance_at_selection": float(distance[index])})
        selected.append(index)
        available[index] = False
        new_distance = np.minimum(1.0, np.linalg.norm(features-features[index], axis=1) / np.sqrt(DIVERSITY_DIMENSIONS))
        distance = np.minimum(distance, new_distance)
    return np.array(selected, dtype=int), decisions


def select_fresh_pair(material_ids, predicted_mean, calibrated_radius,
                      diversity_features, distance_to_initial_training):
    """Choose at most two unique valid candidates within one fresh formula.

    The caller supplies only already geometry/stoichiometry-validated, deduplicated
    candidates. This small prototype shortlist is separate from the replay's 7/3
    query-policy comparison. It never accepts CHGNet or DFT energies.
    """
    ids = np.asarray(material_ids, dtype=str)
    n = len(ids)
    if n == 0:
        return np.array([], dtype=int), []
    mean = np.asarray(predicted_mean, dtype=np.float64)
    radius = np.asarray(calibrated_radius, dtype=np.float64)
    distance = np.asarray(distance_to_initial_training, dtype=np.float64).copy()
    features = finite_matrix(diversity_features, "diversity_features")
    if len(set(ids)) != n or any(x.shape != (n,) for x in [mean, radius, distance]) or features.shape != (n, 150):
        raise ValueError("Fresh candidate arrays must align and IDs must be unique")
    if not all(np.isfinite(x).all() for x in [mean, radius, distance]) or np.any(radius < 0) or np.any(distance < 0) or np.any(distance > 1):
        raise ValueError("Invalid fresh predictions, uncertainty or diversity")
    available = np.ones(n, dtype=bool)
    chosen, decisions = [], []
    for index_in_pair in range(min(2, n)):
        sign, role = (-1, "conservative") if index_in_pair == 0 else (1, "optimistic")
        scores = (THRESHOLD_EV_ATOM - mean + sign * radius) / ENERGY_SCALE_EV_ATOM + DIVERSITY_WEIGHT * distance
        options = np.flatnonzero(available)
        index = int(options[np.lexsort((ids[options], -scores[options]))[0]])
        chosen.append(index)
        decisions.append({"material_id": str(ids[index]), "role": role, "score": float(scores[index]),
                          "predicted_mean_eV_atom": float(mean[index]), "calibrated_radius_eV_atom": float(radius[index]),
                          "diversity_distance_at_selection": float(distance[index])})
        available[index] = False
        distance = np.minimum(distance, np.minimum(1.0, np.linalg.norm(features-features[index], axis=1) / np.sqrt(150)))
    return np.asarray(chosen, dtype=int), decisions
