"""Export the frozen study's selected geometry without doing scientific inference.

Only saved structures and already-recorded metadata are read.  In particular this
module does not invoke a symmetry finder, matcher, model, optimizer or QE runner.
"""

from __future__ import annotations

import json
import hashlib
import io
import math
import os
import textwrap
from pathlib import Path

import numpy as np
from pymatgen.core import Structure


WORKSPACE = Path(__file__).resolve().parents[2]
FREEZE = "artifacts/phase6/manifest.json"
MODEL_PLAN = "artifacts/phase5/chgnet/plan.json"
MODEL_SUMMARY = "artifacts/phase5/chgnet/summary.json"
MODEL_ROWS = "artifacts/phase6/structures/relaxed_structures.csv"
DRAW_ROWS = "artifacts/phase6/structures/generation_draws.csv"
STRUCTURE_SUMMARY = "artifacts/phase6/structures/summary.json"
P3_QE = "artifacts/phase3/qe/summary.json"
P4_QE = "artifacts/phase4/qe/summary.json"
P5_QE = "artifacts/phase5/qe/summary.json"


def _path(value):
    return str(value).replace("\\", "/")


def _bool(value):
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError(f"Expected recorded boolean, got {value!r}")


def _symmetry(number=None, source=None, *, requested=None, settings_known=False):
    return {
        "spacegroupNumber": int(number) if number is not None else None,
        "requestedSpacegroupNumber": int(requested) if requested is not None else None,
        "symprecAngstrom": 0.01 if settings_known else None,
        "angleToleranceDegrees": 5.0 if settings_known else None,
        "evidenceSourceId": source,
        "newSymmetryInferencePerformed": False,
    }


def _eligibility(*, eligible=None, excluded=False, reasons=None, queue=False):
    return {
        "exactCellEligible": eligible,
        "workloadEligible": eligible,
        "queueSelected": queue,
        "newPhase5DFTDispatchAuthorized": False,
        "excluded": excluded,
        "reasons": reasons or [],
        "interpretation": "Geometry/workload and historical frozen queue gates at this stage; no stability implication or new dispatch authorization",
    }


def _novelty(row=None):
    return {
        "globalStructureNoveltyEstablished": False,
        "globalCompositionNoveltyEstablished": False,
        "generatorPretrainingOODEstablished": False,
        "matchesPinnedGeometryIds": json.loads(row["matches_pinned_MP_same_composition_geometry_ids"]) if row else [],
        "sameCompositionGeometriesTested": int(row["same_composition_MP_geometries_tested"]) if row else None,
        "scope": "Recorded pinned-subset matching only; an unmatched subset does not prove global novelty",
    }


def _no_dft():
    return {
        "status": "not_performed_at_this_stage",
        "jobId": None,
        "terminalSCFAccepted": None,
        "stationarityAccepted": None,
        "finiteSensitivityAccepted": None,
        "newStableMaterialEstablished": False,
        "fullHullEstablished": False,
    }


def _geometry(ctx, raw, stage_id):
    """Preserve the saved lattice/site basis; validate reversible conversions."""
    crystal = Structure.from_dict(raw)
    matrix = np.asarray(crystal.lattice.matrix, dtype=float)
    frac = np.asarray(crystal.frac_coords, dtype=float)
    cart = frac @ matrix
    restored = cart @ np.linalg.inv(matrix)
    distances = np.asarray(crystal.distance_matrix, dtype=float)
    positive = distances[np.triu_indices(len(crystal), 1)]
    nearest = float(np.min(positive)) if len(positive) else None
    determinant = float(np.linalg.det(matrix))
    sites = []
    for i, site in enumerate(crystal):
        species = [{"element": str(element.symbol), "occupancy": float(occ)}
                   for element, occ in site.species.items()]
        sites.append({"siteIndex": i, "species": species})
    rebuilt = Structure(matrix, [site.species for site in crystal], frac,
                        coords_are_cartesian=False, to_unit_cell=False)
    ctx.check(bool(np.isfinite(matrix).all() and np.isfinite(frac).all()),
              f"Finite saved geometry {stage_id}")
    ctx.check(bool(determinant > 0), f"Right-handed nonzero lattice {stage_id}",
              determinantAngstrom3=determinant)
    ctx.check(bool(np.allclose(restored, frac, rtol=0, atol=1e-12)),
              f"Fractional Cartesian roundtrip {stage_id}")
    ctx.check(bool(np.allclose(cart, crystal.cart_coords, rtol=0, atol=1e-10)),
              f"Lattice-row coordinate convention {stage_id}")
    ctx.check(bool(np.allclose(rebuilt.distance_matrix, distances, rtol=0, atol=1e-10)),
              f"Periodic distance roundtrip {stage_id}")
    ctx.check(bool(math.isclose(determinant, crystal.volume, rel_tol=0, abs_tol=1e-9)),
              f"Determinant volume {stage_id}")
    ctx.check(all(len(s["species"]) == 1 and s["species"][0]["occupancy"] == 1.0 for s in sites),
              f"Physical atom count equals saved ordered sites {stage_id}")
    source_cart = np.asarray([s["xyz"] for s in raw["sites"]], dtype=float)
    ctx.check(bool(np.allclose(cart, source_cart, rtol=0, atol=1e-8)),
              f"Saved Cartesian source coordinates {stage_id}")
    return {
        "actualAtoms": len(crystal),
        "formula": crystal.composition.formula,
        "reducedFormula": crystal.composition.reduced_formula,
        "latticeRowsAngstrom": matrix.tolist(),
        "fractionalCoordinates": frac.tolist(),
        "sites": sites,
        "pbc": [bool(x) for x in crystal.lattice.pbc],
        "volumeAngstrom3": determinant,
        "minimumPeriodicDistanceAngstrom": nearest,
        "displayWrappingApplied": False,
        "periodicImagesAdded": False,
    }


def _fallback_figure(ctx, record):
    """Draw an identified saved cell; display wrapping is explicit and local."""
    os.environ["MPLCONFIGDIR"] = str(WORKSPACE / "website" / ".cache" / "matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from PIL import Image

    renderer_version = "saved-stage-fallback-v2"
    logical_name = f"figures/structures/{record['stageId']}.png"
    identity = {"rendererVersion": renderer_version, "stageId": record["stageId"],
                "sourceSha256": record["sourceSha256"], "geometry": record["geometry"],
                "matplotlibVersion": matplotlib.__version__}
    identity_bytes = json.dumps(identity, allow_nan=False, sort_keys=True,
                                separators=(",", ":")).encode()
    key = hashlib.sha256(identity_bytes).hexdigest()
    cache = WORKSPACE / "website" / ".cache" / "structure-fallbacks"
    cache.mkdir(parents=True, exist_ok=True)
    image_path, hash_path = cache / f"{key}.png", cache / f"{key}.sha256"
    if image_path.is_file() and hash_path.is_file():
        content = image_path.read_bytes()
        ctx.check(hashlib.sha256(content).hexdigest() == hash_path.read_text().strip(),
                  f"Cached saved-stage fallback bytes verified {record['stageId']}")
    else:
        geometry = record["geometry"]
        matrix = np.asarray(geometry["latticeRowsAngstrom"])
        frac = np.asarray(geometry["fractionalCoordinates"])
        positions = (frac % 1.0) @ matrix
        corners_frac = np.asarray([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)])
        corners = corners_frac @ matrix
        palette = {"Mg": "#7B66B0", "Ca": "#D79731", "O": "#CE4945",
                   "Ti": "#68889B", "Sn": "#648D78", "Sr": "#AD7992", "Ba": "#A0804C"}
        symbols = [site["species"][0]["element"] for site in geometry["sites"]]
        fig = plt.figure(figsize=(5.2, 4.4), facecolor="#F6F2E9")
        ax = fig.add_subplot(111, projection="3d", facecolor="#F6F2E9")
        for i, corner in enumerate(corners_frac):
            for j in range(i + 1, len(corners_frac)):
                if np.count_nonzero(corner != corners_frac[j]) == 1:
                    line = corners[[i, j]]
                    ax.plot(*line.T, color="#849199", linewidth=0.9, alpha=0.9)
        for symbol in sorted(set(symbols)):
            selected = positions[[x == symbol for x in symbols]]
            ax.scatter(*selected.T, color=palette.get(symbol, "#777777"),
                       s=80 if symbol == "O" else 145, edgecolors="white",
                       linewidths=0.65, depthshade=True)
        bounds = np.vstack([corners, positions])
        low, high = bounds.min(axis=0), bounds.max(axis=0)
        center, half = (high + low) / 2, max(float((high - low).max()), 1.0) * 0.56
        for setter, value in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), center):
            setter(value - half, value + half)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=22, azim=-58)
        ax.set_axis_off()
        stage_label = {"generated": "Generated", "generated_excluded": "Generated / excluded",
                       "model_relaxed": "CHGNet relaxed", "accepted_dft": "Accepted finite QE checks",
                       "prototype_initial": "Prepared prototype", "catalog_initial": "Catalog input"}[record["stage"]]
        fig.suptitle(f"{geometry['reducedFormula']} · {stage_label}", x=0.5, y=0.98,
                     fontsize=12, weight="bold", color="#202A31")
        fig.text(0.5, 0.91, "\n".join(textwrap.wrap(record["candidateId"], width=61)),
                 fontsize=7.5, ha="center", va="center", color="#43505A")
        handles = [Line2D([0], [0], marker="o", linestyle="", color=palette.get(s, "#777777"),
                          markersize=7, label=s) for s in sorted(set(symbols))]
        fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.09),
                   ncol=len(handles), frameon=False, fontsize=9)
        fig.text(0.5, 0.065, f"{geometry['actualAtoms']} physical atoms · lattice in Å · coordinates wrapped for display",
                 ha="center", fontsize=7.3, color="#43505A")
        fig.text(0.5, 0.031, "Saved geometry only · illustrative atom sizes · no added periodic images",
                 ha="center", fontsize=7.2, color="#43505A")
        fig.subplots_adjust(left=0.02, right=0.98, bottom=0.16, top=0.83)
        temporary_image = cache / f"{key}.{os.getpid()}.tmp.png"
        fig.savefig(temporary_image, dpi=110, facecolor=fig.get_facecolor(),
                    metadata={"Software": "The Flamel Project W1 " + renderer_version})
        plt.close(fig)
        content = temporary_image.read_bytes()
        temporary_hash = cache / f"{key}.{os.getpid()}.tmp.sha256"
        temporary_hash.write_text(hashlib.sha256(content).hexdigest() + "\n", encoding="ascii")
        os.replace(temporary_image, image_path)
        os.replace(temporary_hash, hash_path)
    with Image.open(io.BytesIO(content)) as rendered:
        rendered.verify()
    ctx.check(content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) < 100_000,
              f"Stage-specific fallback is a small actual-geometry PNG {record['stageId']}",
              bytes=len(content))
    ctx.add_asset(logical_name, content)
    return logical_name


def export_structures(ctx):
    manifest = ctx.read_json(FREEZE)
    pinned = {_path(item["path"]): item["sha256"] for item in manifest["files"]}

    def authorize(path, digest=None, purpose="Saved candidate-stage provenance"):
        path = _path(path)
        expected = digest or pinned.get(path)
        ctx.check(expected is not None, f"Geometry source has frozen hash {path}")
        if expected is None:
            raise ValueError(f"No pinned hash for {path}")
        if path in pinned:
            ctx.check(expected == pinned[path], f"Lineage hash agrees with Phase6 freeze {path}")
        ctx.authorize(path, expected, purpose)
        return path

    def read(path, digest=None, purpose="Saved candidate-stage provenance"):
        return ctx.read_json(authorize(path, digest, purpose))

    def ev(path, field=None):
        return {"sourceId": ctx.source_id(_path(path)), "field": field}

    plan = ctx.read_json(MODEL_PLAN)
    summary = read(MODEL_SUMMARY, purpose="CHGNet result/parent/geometry identity join")
    rows = {r["candidate_id"]: r for r in ctx.read_csv(MODEL_ROWS)}
    draws = {r["candidate_id"]: r for r in ctx.read_csv(DRAW_ROWS)}
    results = {r["candidate_id"]: r for r in summary["results"]}
    ctx.check(len(plan["jobs"]) == len(rows) == len(results) == 11,
              "Eleven selected model records resolve exactly")
    candidates, stages = [], []
    source_to_stage = {}
    geometry_cache = {}

    def stage(candidate_id, stage_kind, method, path, digest, *, parent=None,
              parent_source=None, evidence=(), symmetry=None, eligibility=None,
              validation=None, novelty=None, energy=None):
        path = authorize(path, digest, "Public saved structure geometry")
        stage_id = f"{candidate_id}--{stage_kind}"
        geom = _geometry(ctx, ctx.read_json(path), stage_id)
        record = {
            "candidateId": candidate_id, "stageId": stage_id,
            "parentStageId": parent,
            "recordedParentSourceId": ctx.source_id(parent_source) if parent_source else None,
            "sourceId": ctx.source_id(path), "sourceSha256": digest,
            "evidence": list(evidence), "method": method, "stage": stage_kind,
            "eligibility": eligibility or _eligibility(),
            "dftValidation": validation or _no_dft(),
            "novelty": novelty or _novelty(), "geometry": geom,
            "symmetry": symmetry or _symmetry(), "energy": energy,
        }
        source_to_stage[path] = stage_id
        geometry_cache[stage_id] = geom
        record["fallbackFigureLogicalName"] = _fallback_figure(ctx, record)
        record["fallbackFigureDisplay"] = {"coordinatesWrappedIntoUnitCell": True,
                                           "periodicImagesAdded": False,
                                           "physicalAtoms": geom["actualAtoms"]}
        stages.append(record)
        ctx.add_json(f"structures/{stage_id}.json", record)
        return stage_id

    for job in plan["jobs"]:
        candidate_id = job["candidate_id"]
        item, row = results[candidate_id], rows[candidate_id]
        original = authorize(job["original_source"], job["original_source_sha256"],
                             "Original generation/prototype/reference input identity")
        source = authorize(job["source_structure"], job["source_structure_sha256"])
        result_path = authorize(item["result_path"], item["result_sha256"],
                                "Saved converged CHGNet result")
        result = ctx.read_json(result_path)
        ctx.check(result == item["result"], f"Model summary matches raw result {candidate_id}")
        ctx.check(result["source_structure_sha256"] == job["source_structure_sha256"],
                  f"Model input hash identity {candidate_id}")
        ctx.check(_bool(row["converged"]) and result["converged"] is True,
                  f"Recorded model convergence {candidate_id}")
        category = job["category"]
        if category == "symmetry":
            draw = draws[candidate_id]
            ctx.check(draw["source_sha256"] == job["source_structure_sha256"],
                      f"Generated source matches selected input {candidate_id}")
            initial_kind, initial_method = "generated", "crystalformer"
            symmetry = _symmetry(draw["measured_spacegroup"], ctx.source_id(DRAW_ROWS),
                                 requested=draw["requested_spacegroup"], settings_known=True)
            initial_eligibility = _eligibility(eligible=_bool(draw["valid"]))
        else:
            initial_kind = "prototype_initial" if category == "prototype" else "catalog_initial"
            initial_method = "prototype_substitution" if category == "prototype" else "catalog_reference"
            # A catalog SG label is not a new measurement of this saved cell.
            symmetry = _symmetry()
            initial_eligibility = _eligibility(eligible=True)
            original_crystal = Structure.from_file(str(WORKSPACE / original))
            staged_crystal = Structure.from_dict(ctx.read_json(source))
            ctx.check(bool(np.allclose(original_crystal.lattice.matrix,
                                       staged_crystal.lattice.matrix, rtol=0, atol=1e-10)),
                      f"CIF to saved model-input lattice identity {candidate_id}")
            ctx.check([str(s.species) for s in original_crystal] ==
                      [str(s.species) for s in staged_crystal] and
                      bool(np.allclose(original_crystal.frac_coords,
                                       staged_crystal.frac_coords, rtol=0, atol=1e-10)),
                      f"CIF to saved model-input sites identity {candidate_id}")
        initial = stage(candidate_id, initial_kind, initial_method,
                        source, job["source_structure_sha256"],
                        parent_source=original if source != original else None,
                        evidence=[ev(MODEL_PLAN, f"jobs[{job['selection_index']}]")],
                        symmetry=symmetry, eligibility=initial_eligibility)
        final_path = _path(result["final_structure"])
        final_hash = result["final_structure_sha256"]
        ctx.check(final_hash == row["source_sha256"] and final_path == _path(row["source_final_structure"]),
                  f"Final geometry joins frozen structure table {candidate_id}")
        settings = {
            "modelVersion": result["model_version"],
            "checkpointSha256": result["checkpoint_sha256"],
            "packageVersion": plan["settings"]["package"],
            "optimizer": plan["settings"]["optimizer"],
            "maxSteps": plan["settings"]["steps_max"],
            "forceThresholdEVPerAngstrom": plan["settings"]["fmax_eV_A"],
            "cellRelaxed": plan["settings"]["relax_cell"],
            "filter": plan["settings"]["ase_filter"],
            "imposedSymmetry": plan["settings"]["imposed_symmetry"],
        }
        value = float(result["energy_eV_per_atom"])
        ctx.check(math.isfinite(value) and value == float(row["CHGNet_energy_eV_per_atom"]),
                  f"Finite recorded per-atom model energy {candidate_id}")
        ctx.check(math.isclose(value * int(result["atoms"]), result["energy_total_eV"],
                               rel_tol=0, abs_tol=1e-10),
                  f"Model total-energy normalization by physical atoms {candidate_id}")
        final = stage(candidate_id, "model_relaxed", "chgnet",
                      final_path, final_hash, parent=initial,
                      parent_source=source,
                      evidence=[ev(result_path), ev(MODEL_ROWS, candidate_id), ev(MODEL_PLAN, "settings")],
                      symmetry=_symmetry(result["final_spacegroup"], ctx.source_id(MODEL_ROWS), settings_known=True),
                      eligibility=_eligibility(eligible=result["DFT_eligible"],
                                                reasons=result["DFT_ineligibility_reasons"],
                                                queue=item["previously_dispatched_known_MgO_control"]),
                      novelty=_novelty(row),
                      energy={"value": value, "unit": "eV/atom", "engine": "CHGNet",
                              "settingsScope": "chgnet-0.3.0-" + result["checkpoint_sha256"],
                              "settings": settings,
                              "interpretation": "Model electronic-energy estimate; not fresh DFT or stability"})
        ctx.check(geometry_cache[initial]["actualAtoms"] == geometry_cache[final]["actualAtoms"] == int(row["actual_atoms"]),
                  f"Physical source/model atom count {candidate_id}")
        candidates.append({
            "candidateId": candidate_id, "role": category,
            "method": initial_method, "control": job.get("control"), "arm": job.get("arm"),
            "comparisonScope": job.get("comparison_scope"),
            "formula": geometry_cache[initial]["reducedFormula"],
            "actualAtoms": geometry_cache[initial]["actualAtoms"],
            "stageIds": [initial, final], "defaultStageId": final,
            "parentMaterialId": job.get("parent_material_id"),
            "referenceMaterialId": job.get("reference_material_id"),
            "referencePhase": job.get("reference_phase"),
            "cachedModelReuse": job["cached"],
            "evidence": [ev(MODEL_PLAN, f"jobs[{job['selection_index']}]")],
            "eligible": True, "newStableMaterialEstablished": False,
        })

    # The excluded transformer draw is a separate candidate from its composition's
    # six-atom prototype.  Exclusion survives geometry export.
    matching_excluded = [r for r in draws.values()
                         if r["source_structure"] == "artifacts/phase3/generation/early_CaMg2O3/structure_005.json"]
    ctx.check(len(matching_excluded) == 1, "Unique saved twelve-atom CaMg2O3 excluded example")
    excluded = matching_excluded[0]
    excluded_id = excluded["candidate_id"]
    ctx.check(_bool(excluded["larger_cell_diagnostic_excluded"]) and not _bool(excluded["valid"]),
              "Larger-cell example remains excluded")
    excluded_stage = stage(excluded_id, "generated_excluded", "crystalformer",
                           excluded["source_structure"], excluded["source_sha256"],
                           evidence=[ev(DRAW_ROWS, excluded_id)],
                           symmetry=_symmetry(excluded["measured_spacegroup"], ctx.source_id(DRAW_ROWS),
                                              requested=excluded["requested_spacegroup"], settings_known=True),
                           eligibility=_eligibility(eligible=False, excluded=True,
                               reasons=["Actual 12-atom cell differs from the frozen exact 6-atom request; diagnostic only"]))
    ctx.check(geometry_cache[excluded_stage]["actualAtoms"] == 12 and int(excluded["requested_n_atoms"]) == 6,
              "Excluded source retains twelve physical atoms versus six requested")
    candidates.append({
        "candidateId": excluded_id, "role": "excluded_diagnostic", "method": "crystalformer",
        "formula": geometry_cache[excluded_stage]["reducedFormula"], "actualAtoms": 12,
        "stageIds": [excluded_stage], "defaultStageId": excluded_stage,
        "eligible": False, "newStableMaterialEstablished": False,
        "evidence": [ev(DRAW_ROWS, excluded_id)],
    })

    p3, p4 = ctx.read_json(P3_QE), ctx.read_json(P4_QE)
    structure_summary = ctx.read_json(STRUCTURE_SUMMARY)
    reference_memberships = ctx.read_csv("artifacts/phase6/evidence/reference_inventory_completeness.csv")
    qes = [
        ("phase1_mgo_attempt_000", p3["accepted_candidate_job_id"], P3_QE,
         p3["candidate_validation"]["full_numerical_convergence"], "candidate_control", None,
         structure_summary["DFT_validation"]["known_control"]["candidate_spacegroup"]),
        ("qe_source_reference_mgo_mp1265", p3["accepted_reference_job_id"], P3_QE,
         p3["reference_validation"]["full_numerical_convergence"], "source_reference", "mp-1265",
         structure_summary["DFT_validation"]["known_control"]["reference_spacegroup"]),
        ("qe_source_reference_cao_mp2605", p4["accepted_CaO_job_id"], P4_QE,
         p4["CaO_final_geometry_numerical_checks_pass"], "source_reference", "mp-2605", None),
    ]
    for candidate_id, job_id, summary_path, accepted, role, material_id, group in qes:
        ctx.check(accepted is True, f"Recorded final-geometry finite QE acceptance {job_id}")
        job_summary = p3 if summary_path == P3_QE else p4
        job_rows = [x for x in job_summary["jobs"] if x["job_id"] == job_id]
        ctx.check(len(job_rows) == 1, f"Unique accepted QE job record {job_id}")
        job_result_path = _path(job_rows[0]["path"])
        job_result = read(job_result_path, purpose="Accepted QE result and exact geometry parent relation")
        result, provenance = job_result["result"], job_result["provenance"]
        source = authorize(provenance["source_geometry"], provenance["source_geometry_sha256"],
                           "QE execution's recorded input geometry")
        final_path = _path(f"artifacts/phase{job_result['phase']}/qe/{job_id}/final_geometry.json")
        final_hash = pinned[final_path]
        settings = provenance["settings"]
        parent = source_to_stage.get(source)
        if role == "candidate_control":
            expected = "phase1_mgo_attempt_000--model_relaxed"
            ctx.check(parent == expected, "Accepted generated MgO QE provenance proves model-stage parent")
        else:
            ctx.check(parent is None, f"Source-reference QE cell has no fabricated model parent {job_id}")
            ctx.check(any(r["material_id"] == material_id and r["accepted_job_id"] == job_id and
                          _bool(r["accepted_fresh_compatible_QE"]) for r in reference_memberships),
                      f"Accepted source-reference material ID is recorded inventory membership {job_id}")
        ctx.check(result["job_scf_accepted"] is True and result["job_stationary_at_this_setting"] is True,
                  f"Accepted QE terminal SCF and stationarity {job_id}")
        stage_id = stage(candidate_id, "accepted_dft", "quantum_espresso",
                         final_path, final_hash, parent=parent, parent_source=source,
                         evidence=[ev(summary_path), ev(job_result_path), ev(STRUCTURE_SUMMARY, "DFT_validation")],
                         symmetry=_symmetry(group, ctx.source_id(STRUCTURE_SUMMARY) if group else None,
                                            settings_known=group is not None),
                         eligibility=_eligibility(eligible=True, queue=True),
                         validation={"status": "accepted_numerical_control" if role == "candidate_control" else "accepted_numerical_reference",
                                     "jobId": job_id, "terminalSCFAccepted": True,
                                     "stationarityAccepted": True, "finiteSensitivityAccepted": accepted,
                                     "newStableMaterialEstablished": False, "fullHullEstablished": False},
                         energy={"value": float(result["energy_eV_per_atom"]), "unit": "eV/atom",
                                 "engine": "Quantum ESPRESSO PBE",
                                 "settingsScope": "qe-pbe-90-720-spacing0.35-nspin1-" + geometry_cache[parent]["reducedFormula"] if parent else "qe-pbe-90-720-spacing0.35-nspin1-" + result["formula"],
                                 "settings": {"functional": settings["input_dft"],
                                              "wavefunctionCutoffRy": settings["ecutwfc_Ry"],
                                              "densityCutoffRy": settings["ecutrho_Ry"],
                                              "kMesh": settings["k_mesh"],
                                              "kSpacingTargetInverseAngstrom": settings["k_spacing_start_inv_angstrom"],
                                              "nspin": settings["nspin"], "occupations": settings["occupations"],
                                              "pseudoSha256ByElement": provenance["pseudo_hashes"],
                                              "executableSha256": provenance["executable_sha256"]},
                                 "interpretation": "Static PBE electronic energy; accepted finite numerical tests, no hull or phonon proof"})
        ctx.check(geometry_cache[stage_id]["actualAtoms"] == result["n_atoms"],
                  f"Accepted QE geometry physical atom count {job_id}")
        ctx.check(math.isfinite(float(result["energy_eV_per_atom"])) and
                  math.isclose(result["energy_eV_per_atom"] * result["n_atoms"],
                               result["total_energy_eV"], rel_tol=0, abs_tol=1e-9),
                  f"Accepted QE energy normalization by physical atoms {job_id}")
        if role == "candidate_control":
            candidate = next(c for c in candidates if c["candidateId"] == candidate_id)
            candidate["stageIds"].append(stage_id)
            candidate["defaultStageId"] = stage_id
        else:
            candidates.append({"candidateId": candidate_id, "role": role,
                               "method": "catalog_reference", "referenceMaterialId": material_id,
                               "formula": geometry_cache[stage_id]["reducedFormula"],
                               "actualAtoms": geometry_cache[stage_id]["actualAtoms"],
                               "stageIds": [stage_id], "defaultStageId": stage_id,
                               "eligible": True, "newStableMaterialEstablished": False,
                               "evidence": [ev(summary_path), ev(job_result_path)]})

    perturb = read(P5_QE, purpose="Evidence-only incomplete known-MgO perturbation")
    ctx.check(perturb["accepted_perturbation_job_id"] is None and
              perturb["perturbation_validation_incomplete"] is True,
              "Incomplete perturbation creates no accepted geometry stage")
    incomplete_evidence = [{
        "evidenceId": "known-mgo-perturbation-incomplete", "candidateId": "phase1_mgo_attempt_000",
        "kind": "incomplete_dft_perturbation", "sourceId": ctx.source_id(P5_QE),
        "jobIds": [j["job_id"] for j in perturb["jobs"]],
        "acceptedTerminalStageId": None, "energy": None,
        "status": "time_limit_before_terminal_convergence",
        "explanation": "Recorded 900-second QE limit; no accepted terminal geometry, forces, stress or energy comparison",
        "newStableMaterialEstablished": False,
    }]
    by_id = {s["stageId"]: s for s in stages}
    ctx.check(len(candidates) == 14 and len({c["candidateId"] for c in candidates}) == 14,
              "Fourteen distinct candidate/reference entities")
    ctx.check(len(stages) == len(by_id) == 26, "Twenty-six uniquely identified saved geometry stages")
    ctx.check(sum(s["stage"] == "model_relaxed" for s in stages) == 11,
              "All eleven selected model finals are public")
    ctx.check(sum(s["stage"] == "accepted_dft" for s in stages) == 3,
              "Exactly three accepted relaxed QE geometry stages")
    ctx.check(all(s["parentStageId"] is None or
                  (s["parentStageId"] in by_id and by_id[s["parentStageId"]]["candidateId"] == s["candidateId"])
                  for s in stages), "Every public stage parent is present and belongs to the same candidate")
    nonorthogonal = [s["stageId"] for s in stages
                    if not np.allclose(np.asarray(s["geometry"]["latticeRowsAngstrom"]) @
                                       np.asarray(s["geometry"]["latticeRowsAngstrom"]).T,
                                       np.diag(np.diag(np.asarray(s["geometry"]["latticeRowsAngstrom"]) @
                                                       np.asarray(s["geometry"]["latticeRowsAngstrom"]).T)),
                                       rtol=0, atol=1e-6)]
    ctx.check(len(nonorthogonal) > 0, "Geometry validation includes actual non-orthogonal saved cells",
              stageIds=nonorthogonal)
    core_examples = [
        {"id": "known-mgo-sequence", "candidateId": "phase1_mgo_attempt_000",
         "stageIds": next(c["stageIds"] for c in candidates if c["candidateId"] == "phase1_mgo_attempt_000")},
        {"id": "mgo-p1-partner", "candidateId": "phase4_supplementary_mgo_rocksalt_p1_attempt_010"},
        {"id": "tio2-nontrivial", "candidateId": "phase4_tio2_rutile_nontrivial_attempt_000"},
        {"id": "tio2-p1", "candidateId": "phase4_tio2_rutile_p1_attempt_000"},
        {"id": "camg2o3-prototype", "candidateId": "prototype_CaMg2O3"},
        {"id": "camg2o3-excluded-twelve-atom", "candidateId": excluded_id},
    ]
    ctx.add_json("structures/index.json", {
        "candidates": candidates,
        "stages": [{"candidateId": s["candidateId"], "stageId": s["stageId"],
                    "stage": s["stage"], "parentStageId": s["parentStageId"],
                    "logicalFile": f"structures/{s['stageId']}.json",
                    "sourceId": s["sourceId"], "sourceSha256": s["sourceSha256"],
                    "fallbackFigureLogicalName": s["fallbackFigureLogicalName"],
                    "actualAtoms": s["geometry"]["actualAtoms"]} for s in stages],
        "coreExamples": core_examples, "evidenceOnly": incomplete_evidence,
        "counts": {"entities": 14, "stages": 26, "modelFinals": 11,
                   "acceptedQERelaxedGeometries": 3, "excludedExamples": 1},
        "geometryConvention": {"latticeVectors": "rows", "latticeUnit": "angstrom",
                               "coordinates": "fractional", "cartesianFormula": "fractional @ lattice",
                               "siteIndices": "zero-based saved source order", "displayWrappingApplied": False,
                               "periodicImagesAdded": False, "physicalAtomsExcludeDisplayImages": True},
        "validation": {"nonOrthogonalStageIds": nonorthogonal,
                       "newSymmetryInference": False, "newMatching": False,
                       "newModelInference": False, "newRelaxations": False},
        "scope": "Saved-stage navigation only; separate execution cells are separate entities and failed QE creates no accepted stage",
    })
