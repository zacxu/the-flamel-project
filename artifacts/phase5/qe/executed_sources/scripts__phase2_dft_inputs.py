"""Create audited QE input templates only. This module never launches a job."""
from __future__ import annotations

import math
from pathlib import Path

from pymatgen.core import Structure

RY_BOHR_TO_EV_ANGSTROM = 25.711033738


def k_grid(structure: Structure, spacing_inv_angstrom: float = 0.60):
    """Comparable reciprocal spacing including 2*pi, not identical cell-wise meshes."""
    return [max(1, math.ceil(length / spacing_inv_angstrom))
            for length in structure.lattice.reciprocal_lattice.abc]


def qe_input(structure: Structure, pseudos: dict, *, prefix: str,
             calculation="vc-relax", molecular_oxygen=False, metallic=False,
             spin_review_required=False, cutoff_multiplier=1.0,
             k_spacing=0.60, vacuum_angstrom=None, max_seconds=900):
    """Return input+settings for Phase 3; all requested settings remain auditable.

    Non-O2 templates use a nonmagnetic starting hypothesis. Unknown/magnetic
    reference phases are flagged for review and cannot be silently accepted as
    complete reference calculations based on this template alone.
    """
    if not structure.is_ordered:
        raise ValueError("Disordered structures require an explicit ordered model")
    if molecular_oxygen and (structure.composition.as_dict() != {"O": 2.0}):
        raise ValueError("O2 triplet template must contain exactly two oxygen atoms")
    if calculation not in {"scf", "relax", "vc-relax"}:
        raise ValueError("Unsupported calculation type")
    if molecular_oxygen and calculation == "vc-relax":
        raise ValueError("The isolated molecule box must not undergo cell relaxation")
    elements = sorted({site.specie.symbol for site in structure})
    required = {element: pseudos[element] for element in elements}
    # A shared 50/400-Ry starting floor is the maximum SSSP recommendation in
    # the frozen Ca-Mg-O system, including its elemental references.
    ecutwfc = max(50.0, max(row["cutoff_wfc"] for row in required.values())) * cutoff_multiplier
    ecutrho = max(400.0, max(row["cutoff_rho"] for row in required.values())) * cutoff_multiplier
    grid = [1, 1, 1] if molecular_oxygen else k_grid(structure, k_spacing)
    settings = {
        "calculation": calculation, "input_dft": "PBE", "nat": len(structure),
        "ecutwfc_Ry": ecutwfc, "ecutrho_Ry": ecutrho,
        "k_mesh": grid, "k_spacing_start_inv_angstrom": None if molecular_oxygen else k_spacing,
        "conv_thr_Ry": 1e-8, "forc_conv_thr_Ry_per_Bohr": 8e-4,
        "forc_conv_thr_eV_per_angstrom": 8e-4 * RY_BOHR_TO_EV_ANGSTROM,
        "force_threshold_interpretation": "QE threshold applies to Cartesian components; independently check final max vector norm <=0.0205688269904 eV/A and tighten continuation if needed",
        "etot_conv_thr_Ry": 1e-5, "press_conv_thr_kbar": 0.5,
        "final_max_force_vector_norm_eV_per_angstrom": 0.0205688269904,
        "final_max_absolute_residual_stress_component_kbar": 0.5 if not molecular_oxygen else None,
        "scf_must_converge": True, "electron_maxstep": 100,
        "nstep": 80, "nosym": True, "noinv": True,
        "nspin": 2 if molecular_oxygen else 1,
        "tot_magnetization_muB": 2 if molecular_oxygen else None,
        "occupations": "smearing" if metallic else "fixed",
        "smearing": "cold" if metallic else None,
        "degauss_Ry": 0.01 if metallic else None,
        "vacuum_box_angstrom": vacuum_angstrom,
        "max_seconds": max_seconds,
        "spin_review_required_before_reference_acceptance": spin_review_required,
        "production_ready": False,
        "acceptance_note": "Starting numerical template only: cutoff, k mesh, spin and reference completeness require recorded Phase 3 checks",
    }
    control = [f" calculation='{calculation}', prefix='{prefix}', pseudo_dir='./pseudo', outdir='./scratch',",
               " tprnfor=.true., tstress=.true., verbosity='high',",
               f" max_seconds={max_seconds}, nstep=80, etot_conv_thr=1.0d-5, forc_conv_thr=8.0d-4,"]
    system = [f" ibrav=0, nat={len(structure)}, ntyp={len(elements)},",
              f" ecutwfc={ecutwfc:.8f}, ecutrho={ecutrho:.8f}, input_dft='PBE',",
              " nosym=.true., noinv=.true.,",
              f" nspin={settings['nspin']}, occupations='{settings['occupations']}',"]
    if metallic:
        system.append(" smearing='cold', degauss=0.01,")
    if molecular_oxygen:
        system.append(" tot_magnetization=2, nbnd=8,")
    lines = ["&CONTROL", *control, "/", "&SYSTEM", *system, "/", "&ELECTRONS",
             " conv_thr=1.0d-8, electron_maxstep=100, scf_must_converge=.true., mixing_beta=0.4,", "/"]
    if calculation != "scf":
        lines.extend(["&IONS", " ion_dynamics='bfgs',", "/"])
    if calculation == "vc-relax":
        lines.extend(["&CELL", " cell_dynamics='bfgs', press=0.0, press_conv_thr=0.5, cell_dofree='all',", "/"])
    lines.append("ATOMIC_SPECIES")
    for element in elements:
        mass = float(structure.composition.elements[[el.symbol for el in structure.composition.elements].index(element)].atomic_mass)
        lines.append(f"{element} {mass:.8f} {required[element]['filename']}")
    lines.append("CELL_PARAMETERS angstrom")
    lines.extend(" ".join(f"{value:.12f}" for value in vector) for vector in structure.lattice.matrix)
    lines.append("ATOMIC_POSITIONS crystal")
    for site in structure:
        lines.append(site.specie.symbol + " " + " ".join(f"{value:.12f}" for value in site.frac_coords))
    if molecular_oxygen:
        lines.append("K_POINTS gamma")
    else:
        lines.extend(["K_POINTS automatic", " ".join(str(value) for value in grid) + " 0 0 0"])
    return "\n".join(lines) + "\n", settings


def write_template(directory: Path, structure: Structure, pseudos: dict, **kwargs):
    import json
    directory.mkdir(parents=True, exist_ok=True)
    text, settings = qe_input(structure, pseudos, **kwargs)
    (directory / "pw.in").write_text(text, encoding="ascii")
    (directory / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings
