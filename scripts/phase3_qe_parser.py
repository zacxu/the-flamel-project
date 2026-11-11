"""Parse QE XML/stdout with explicit units and independent stationarity checks."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from pymatgen.core import Structure

BOHR_ANGSTROM = 0.529177210903
HARTREE_EV = 27.211386245988
HARTREE_BOHR3_TO_KBAR = 294210.264843
FORCE_LIMIT_EV_A = 0.0205688269904
STRESS_LIMIT_KBAR = 0.5


def xml_bool(element):
    return element is not None and (element.text or "").strip().lower() == "true"


def parse_job(directory: Path, settings: dict, *, return_code=None, timed_out=False, write_geometry=True):
    stdout_path = directory / "pw.out"
    text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    errors = []
    xml_path = directory / "scratch" / (settings["prefix"] + ".save") / "data-file-schema.xml"
    result = {"xml_path": str(xml_path), "xml_present": xml_path.exists(),
              "return_code": return_code, "timed_out": timed_out, "job_done": "JOB DONE." in text,
              "calculation": settings["calculation"], "geometry_relaxation_required": settings["calculation"] != "scf",
              "scf_converged": False, "ionic_converged": False, "force_norm_pass": False,
              "full_stress_pass": False, "pressure_pass": False,
              "production_numerical_convergence_established": False,
              "acceptance_scope": "This job's SCF/geometry stationarity only; cutoff/k refinement and final-setting rechecks remain separately required"}
    stdout_energies = re.findall(r"!\s+total energy\s+=\s+([-+0-9.EeDd]+)\s+Ry", text)
    if stdout_energies:
        result["stdout_last_total_energy_Ry"] = float(stdout_energies[-1].replace("D", "E"))
    iteration_counts = re.findall(r"convergence has been achieved in\s+(\d+)\s+iterations", text)
    result["completed_scf_calls"] = len(iteration_counts)
    result["scf_iterations_per_call"] = [int(item) for item in iteration_counts]
    for key, pattern in {"reported_MPI_processes": r"Number of MPI processes:\s+(\d+)",
                         "reported_threads_per_MPI_process": r"Threads/MPI process:\s+(\d+)",
                         "reported_k_points": r"number of k points=\s+(\d+)"}.items():
        values = re.findall(pattern, text)
        result[key] = int(values[-1]) if values else None
    if xml_path.exists():
        try:
            root = ET.parse(xml_path).getroot()
            output = root.find("output")
            if output is None:
                raise ValueError("QE output section missing")
            atomic = output.find("atomic_structure")
            if atomic is None:
                raise ValueError("QE final atomic_structure missing")
            cell = np.array([[float(value) for value in atomic.findtext("cell/" + name).split()]
                             for name in ("a1", "a2", "a3")]) * BOHR_ANGSTROM
            atoms = atomic.findall("atomic_positions/atom")
            positions = np.array([[float(value) for value in atom.text.split()] for atom in atoms]) * BOHR_ANGSTROM
            species = [atom.attrib["name"] for atom in atoms]
            geometry = Structure(cell, species, positions, coords_are_cartesian=True)
            if len(geometry) != settings["nat"] or not np.isfinite(geometry.cart_coords).all():
                raise ValueError("Invalid final geometry")
            final_json = directory / "final_geometry.json"
            if write_geometry:
                final_json.write_text(json.dumps(geometry.as_dict(), indent=2), encoding="utf-8")
                geometry.to(filename=str(directory / "final_geometry.cif"))
            energy_Ha = float(output.findtext("total_energy/etot"))
            forces = np.array([float(value) for value in output.findtext("forces").split()]).reshape((-1, 3)) * HARTREE_EV / BOHR_ANGSTROM
            stress = np.array([float(value) for value in output.findtext("stress").split()]).reshape((3, 3)) * HARTREE_BOHR3_TO_KBAR
            if forces.shape != (len(geometry), 3) or not np.isfinite(forces).all() or not np.isfinite(stress).all():
                raise ValueError("Invalid forces or stress")
            pressure = float(np.trace(stress) / 3)
            max_force = float(np.linalg.norm(forces, axis=1).max())
            max_stress = float(np.abs(stress).max())
            scf = output.find("convergence_info/scf_conv")
            opt = output.find("convergence_info/opt_conv")
            scf_error_Ry = float(scf.findtext("scf_error")) * 2 if scf is not None and scf.findtext("scf_error") else None
            result.update({"n_atoms": len(geometry), "formula": geometry.composition.reduced_formula,
                           "total_energy_Hartree": energy_Ha, "total_energy_Ry": energy_Ha * 2,
                           "total_energy_eV": energy_Ha * HARTREE_EV,
                           "energy_eV_per_atom": energy_Ha * HARTREE_EV / len(geometry),
                           "final_geometry_json": str(final_json), "final_volume_angstrom3": geometry.volume,
                           "forces_eV_per_angstrom": forces.tolist(), "max_force_vector_norm_eV_per_angstrom": max_force,
                           "stress_tensor_kbar_QE_convention": stress.tolist(), "pressure_kbar": pressure,
                           "max_absolute_residual_stress_component_kbar": max_stress,
                           "scf_converged": xml_bool(scf.find("convergence_achieved")) if scf is not None else False,
                           "scf_error_Ry": scf_error_Ry,
                           "electronic_residual_pass": scf_error_Ry is not None and scf_error_Ry <= settings.get("conv_thr_Ry", 1e-8),
                           "ionic_converged": xml_bool(opt.find("convergence_achieved")) if opt is not None else False,
                           "force_norm_pass": max_force <= FORCE_LIMIT_EV_A,
                           "full_stress_pass": max_stress <= STRESS_LIMIT_KBAR,
                           "pressure_pass": abs(pressure) <= STRESS_LIMIT_KBAR,
                           "raw_opt_convergence_xml": ET.tostring(opt, encoding="unicode") if opt is not None else None,
                           "unit_convention": "QE XML Hartree, Bohr, Hartree/Bohr force, Hartree/Bohr^3 stress; converted explicitly"})
            if "stdout_last_total_energy_Ry" in result:
                result["XML_stdout_energy_match"] = abs(result["total_energy_Ry"] - result["stdout_last_total_energy_Ry"]) < 1e-6
                if not result["XML_stdout_energy_match"]:
                    errors.append("Final XML energy differs from final stdout energy")
        except Exception as exc:
            errors.append(repr(exc))
    else:
        errors.append("Final QE XML unavailable")
    result["parser_errors"] = errors
    result["job_scf_accepted"] = return_code == 0 and not timed_out and result["job_done"] and result["scf_converged"] and result.get("electronic_residual_pass", False) and not errors
    result["job_stationary_at_this_setting"] = (result["job_scf_accepted"] and result["force_norm_pass"]
        and result["full_stress_pass"] and result["pressure_pass"]
        and (not result["geometry_relaxation_required"] or result["ionic_converged"]))
    if settings.get("molecular_oxygen"):
        result["job_stationary_at_this_setting"] = (result["job_scf_accepted"] and result["force_norm_pass"]
            and (not result["geometry_relaxation_required"] or result["ionic_converged"]))
    return result
