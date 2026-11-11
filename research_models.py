"""Frozen Phase 3 ensemble helpers with explicit, caller-authorized labels only."""

from __future__ import annotations

import time
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from threadpoolctl import threadpool_limits

from research_acquisition import calibrate_uncertainty, uncertainty_radius


def fit_ensemble(X, y, paired_seed, round_index, estimator_kwargs, members=5):
    """Fit independent outer-bootstrap members in sequence, using two CPU threads."""
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] != 408 or y.shape != (len(X),):
        raise ValueError("Expected aligned n-by-408 features and n explicit labels")
    if not np.isfinite(X).all() or not np.isfinite(y).all() or members != 5:
        raise ValueError("Frozen ensemble requires finite inputs and five members")
    fitted, audit = [], []
    with threadpool_limits(limits=2):
        for member_index in range(members):
            state = np.random.SeedSequence([int(paired_seed), int(round_index), member_index, 11]).generate_state(2, dtype=np.uint32)
            bootstrap_seed, estimator_seed = (int(value) for value in state)
            indices = np.random.default_rng(bootstrap_seed).integers(0, len(X), size=len(X))
            estimator = ExtraTreesRegressor(**estimator_kwargs, random_state=estimator_seed)
            start = time.perf_counter()
            estimator.fit(X[indices], y[indices])
            elapsed = time.perf_counter() - start
            fitted.append(estimator)
            audit.append({
                "member_index": member_index, "bootstrap_seed": bootstrap_seed,
                "estimator_seed": estimator_seed, "bootstrap_indices": indices.tolist(),
                "fit_seconds": elapsed, "training_rows": len(X),
                "bootstrap_unique_rows": len(np.unique(indices)),
            })
    return fitted, audit


def predict_ensemble(members, X):
    X = np.asarray(X, dtype=np.float32)
    if X.ndim != 2 or X.shape[1] != 408 or not np.isfinite(X).all():
        raise ValueError("Prediction requires finite n-by-408 initial-only features")
    if len(members) != 5:
        raise ValueError("Expected the five frozen ensemble members")
    with threadpool_limits(limits=2):
        predictions = np.stack([member.predict(X) for member in members], axis=0)
    return predictions.mean(axis=0), predictions.std(axis=0, ddof=1)


def calibrate_members(members, X_calibration, y_calibration):
    mean, std = predict_ensemble(members, X_calibration)
    return calibrate_uncertainty(y_calibration, mean, std)


def predict_bundle(bundle, X):
    """Shared fresh/replay API; the caller supplies no labels during prediction."""
    mean, std = predict_ensemble(bundle["members"], X)
    return mean, std, uncertainty_radius(std, bundle["calibration"])
