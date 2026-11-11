"""Fixed initial-geometry descriptors shared by WBM and fresh crystal candidates.

The public entry point accepts a pymatgen Structure, never a labelled summary row.
No fitted state, target values, relaxed geometry, IDs, or prototype flags are read.
"""

from __future__ import annotations

import math
import string
import warnings

import numpy as np
from pymatgen.core import Element, Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


# Pymatgen 2025.10.7 repeatedly calls a deprecated gcd helper while making
# display formulas. Suppress that exact compatibility warning, not data errors.
warnings.filterwarnings(
    "ignore", message="gcd is deprecated.*", category=FutureWarning,
    module=r"pymatgen\.core\.composition",
)


SCHEMA_VERSION = "initial_geometry_v1"
SYMPREC_ANGSTROM = 0.01
ANGLE_TOLERANCE_DEGREES = 5.0
MISSING_ELEMENTAL_VALUE = 0.0
PROPERTY_SPECS = (
    ("atomic_number", "Z", "atomic_number"),
    ("atomic_mass", "atomic_mass", "u"),
    ("electronegativity", "X", "Pauling"),
    ("atomic_radius", "atomic_radius", "angstrom"),
)

_names = [f"atomic_fraction_Z{z:03d}" for z in range(1, 119)]
_units = ["fraction"] * 118
for name, _, unit in PROPERTY_SPECS:
    _names.extend(f"{name}_{stat}" for stat in ("mean", "std", "min", "max"))
    _units.extend([unit] * 4)
    _names.append(f"{name}_missing_atom_fraction")
    _units.append("fraction")
_names.extend([
    "n_sites", "initial_volume_per_atom", "initial_a_over_b", "initial_b_over_c",
    "initial_c_over_a", "initial_alpha", "initial_beta", "initial_gamma",
    "minimum_periodic_distance", "nearest_neighbor_mean", "nearest_neighbor_std",
    "nearest_neighbor_max",
])
_units.extend(["count", "angstrom^3/atom", "ratio", "ratio", "ratio", "degree", "degree", "degree"] + ["angstrom"] * 4)
_names.extend(f"initial_spacegroup_{number:03d}" for number in range(1, 231))
_units.extend(["indicator"] * 230)
_names.extend(["initial_symmetry_failed", "initial_inequivalent_site_count"])
_units.extend(["indicator", "count"])
_names.extend(f"initial_wyckoff_site_count_{letter}" for letter in string.ascii_lowercase)
_units.extend(["count"] * 26)
FEATURE_NAMES = tuple(_names)
FEATURE_UNITS = tuple(_units)
FEATURE_DIMENSION = len(FEATURE_NAMES)
assert FEATURE_DIMENSION == 408


def _clean_initial_structure(structure: Structure) -> Structure:
    if not isinstance(structure, Structure):
        raise TypeError("describe_structure requires a pymatgen Structure")
    if len(structure) == 0 or not structure.is_ordered:
        raise ValueError("A nonempty ordered structure is required")
    lattice = np.asarray(structure.lattice.matrix, dtype=np.float64)
    coords = np.asarray(structure.frac_coords, dtype=np.float64)
    if not np.isfinite(lattice).all() or not np.isfinite(coords).all():
        raise ValueError("Initial lattice and coordinates must be finite")
    if not math.isfinite(structure.volume) or structure.volume <= 0:
        raise ValueError("Initial cell must have positive finite volume")
    # Remove labels, charge and arbitrary site/structure properties. Wrapping is a
    # representation change only, not a relaxation or a learned transformation.
    return Structure(
        lattice=lattice,
        species=[site.specie.element if hasattr(site.specie, "element") else site.specie for site in structure],
        coords=np.mod(coords, 1.0),
        to_unit_cell=True,
        coords_are_cartesian=False,
    )


def _elemental_features(structure: Structure) -> tuple[list[float], dict[str, float]]:
    composition = structure.composition.element_composition
    fractions = {element: float(amount / composition.num_atoms) for element, amount in composition.items()}
    vector = np.zeros(118, dtype=np.float64)
    for element, weight in fractions.items():
        vector[element.Z - 1] = weight
    output = vector.tolist()
    missing = {}
    for name, attribute, _ in PROPERTY_SPECS:
        values, weights, missing_fraction = [], [], 0.0
        for element, weight in sorted(fractions.items(), key=lambda item: item[0].Z):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                value = getattr(element, attribute, None)
            if value is None or not math.isfinite(float(value)):
                value = MISSING_ELEMENTAL_VALUE
                missing_fraction += weight
            values.append(float(value))
            weights.append(weight)
        values_arr, weights_arr = np.asarray(values), np.asarray(weights)
        mean = float(np.dot(values_arr, weights_arr))
        std = float(np.sqrt(np.dot((values_arr - mean) ** 2, weights_arr)))
        output.extend([mean, std, float(values_arr.min()), float(values_arr.max()), missing_fraction])
        missing[name] = missing_fraction
    return output, missing


def _distance_features(structure: Structure) -> list[float]:
    # At least one lattice vector lies inside this sphere, so all shortest
    # nonzero self images are found without assuming coefficients in {-1,0,1}.
    _, distances, _, _ = structure.lattice.get_points_in_sphere(
        [[0.0, 0.0, 0.0]], [0.0, 0.0, 0.0], min(structure.lattice.abc) + 1e-7,
        zip_results=False,
    )
    nonzero = np.asarray(distances)[np.asarray(distances) > 1e-9]
    if nonzero.size == 0:
        raise ValueError("No nonzero periodic self image found")
    shortest_self_image = float(nonzero.min())
    matrix = np.asarray(structure.distance_matrix, dtype=np.float64)
    np.fill_diagonal(matrix, shortest_self_image)
    nearest = matrix.min(axis=1)
    if not np.isfinite(nearest).all():
        raise ValueError("Nonfinite periodic distances")
    return [float(nearest.min()), float(nearest.mean()), float(nearest.std()), float(nearest.max())]


def _symmetry_features(structure: Structure) -> tuple[list[float], dict[str, object]]:
    group_vector = np.zeros(230, dtype=np.float64)
    wyckoff_counts = np.zeros(26, dtype=np.float64)
    failure = 0.0
    unique_sites = 0.0
    group_number = None
    error = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            analyzer = SpacegroupAnalyzer(
                structure, symprec=SYMPREC_ANGSTROM,
                angle_tolerance=ANGLE_TOLERANCE_DEGREES,
            )
            dataset = analyzer.get_symmetry_dataset()
        if dataset is None:
            raise ValueError("spglib returned no symmetry dataset")
        group_number = int(dataset.number)
        if group_number not in range(1, 231):
            raise ValueError(f"Invalid initial space group {group_number}")
        if len(dataset.wyckoffs) != len(structure) or len(dataset.equivalent_atoms) != len(structure):
            raise ValueError("Symmetry site count differs from input")
        group_vector[group_number - 1] = 1.0
        unique_sites = float(len(set(int(index) for index in dataset.equivalent_atoms)))
        for letter in dataset.wyckoffs:
            if letter not in string.ascii_lowercase:
                raise ValueError(f"Unsupported Wyckoff letter {letter!r}")
            wyckoff_counts[string.ascii_lowercase.index(letter)] += 1.0
    except Exception as exception:
        # A fixed, explicit representation preserves every otherwise usable row.
        group_vector[:] = 0.0
        wyckoff_counts[:] = 0.0
        unique_sites = 0.0
        failure = 1.0
        group_number = None
        error = f"{type(exception).__name__}: {exception}"
    return [*group_vector, failure, unique_sites, *wyckoff_counts], {
        "initial_spacegroup": group_number,
        "symmetry_failed": bool(failure), "symmetry_error": error,
        "inequivalent_site_count": int(unique_sites),
    }


def describe_structure_with_metadata(structure: Structure) -> tuple[np.ndarray, dict[str, object]]:
    """Return the fixed descriptor and diagnostic metadata from initial input only."""
    initial = _clean_initial_structure(structure)
    elemental, missing = _elemental_features(initial)
    a, b, c = initial.lattice.abc
    alpha, beta, gamma = initial.lattice.angles
    cell = [float(len(initial)), initial.volume / len(initial), a / b, b / c, c / a, alpha, beta, gamma]
    distances = _distance_features(initial)
    symmetry, metadata = _symmetry_features(initial)
    features = np.asarray([*elemental, *cell, *distances, *symmetry], dtype=np.float32)
    if features.shape != (FEATURE_DIMENSION,) or not np.isfinite(features).all():
        raise ValueError("Descriptor shape or finite-value validation failed")
    metadata.update({
        "formula": initial.composition.formula,
        "reduced_formula": initial.composition.reduced_formula,
        "chemical_system": "-".join(sorted(element.symbol for element in initial.composition.elements)),
        "n_sites": len(initial), "missing_elemental_atom_fractions": missing,
    })
    return features, metadata


def describe_structure(structure: Structure) -> np.ndarray:
    """Map one ordered initial crystal to the fixed 408-value float32 descriptor.

    Elemental missing values use the fixed constant zero plus missing-fraction
    features. Symmetry failures use zero group/Wyckoff/count features and a flag.
    Invalid geometry raises an exception; callers must record that failure.
    """
    return describe_structure_with_metadata(structure)[0]
