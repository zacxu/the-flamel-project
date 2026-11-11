"""Curated interpretation and attribution for the frozen website datasets."""
from __future__ import annotations

from export_common import ExportContext


def export_content(ctx: ExportContext) -> None:
    uncertainty = ctx.read_json("artifacts/phase6/uncertainty/summary.json")
    structures = ctx.read_json("artifacts/phase6/structures/summary.json")
    evidence = ctx.read_json("artifacts/phase6/evidence/summary.json")
    source = {
        "uncertainty": ctx.source_id("artifacts/phase6/uncertainty/summary.json"),
        "structures": ctx.source_id("artifacts/phase6/structures/summary.json"),
        "evidence": ctx.source_id("artifacts/phase6/evidence/summary.json"),
        "report": ctx.source_id("reports/phase6_report.md"),
    }
    claims = [
        ("prototype", "An integrated research prototype", "The workflow combines a pretrained symmetry-aware generator, a separate calibrated ensemble selector, model relaxation and genuine first-principles validation. It is not a newly trained transformer architecture.", "report"),
        ("acquisition", "The full policy found fewer historical hits", "Quality retrieved 41.2 near-stable records per 50 queries on average, versus 29.4 for Full. Every one of the five paired differences favoured Quality. These are dependent splits of one historical dataset.", "uncertainty"),
        ("coverage", "Broader chemistry coverage had a retrieval cost", "Full covered 42.2 chemical systems on average versus Quality's 32.8, while retrieving fewer historical near-stable records. Coverage is not discovery yield.", "uncertainty"),
        ("calibration", "Uncertainty ranked error but coverage varied", "Full endpoint nominal-90% interval coverage averaged 88.88%, ranging from 84.84% to 92.10% by split. This does not guarantee calibration for arbitrary OOD chemistry or generated crystals.", "uncertainty"),
        ("roles", "The role breakdown is descriptive", "Full conservative slots found 140/175 historical hits, optimistic slots 7/75. The roles selected different candidates and were not randomized; the breakdown does not isolate causality.", "uncertainty"),
        ("symmetry", "Conditioning improved primary exact-cell validity", "MgO yielded 7/8 versus 0/8 valid cells and TiO2 6/8 versus 1/8 for nontrivial groups versus P1. Both arms use the same symmetry-aware architecture; this is not an architecture-training ablation.", "structures"),
        ("energy-pairs", "Two selected model-energy comparisons", "Each control has one selected unique structure per arm. MgO uses the supplemented pool, TiO2 the primary pool. The CHGNet energy differences do not establish a distribution, a DFT symmetry advantage or a causal architecture benefit.", "structures"),
        ("compositions", "Historical composition absence is scoped", "Six proposals are absent from the two pinned historical composition indexes. Global composition novelty and absence from generator pretraining remain unproven.", "structures"),
        ("eligibility", "The exact-cell gate was the bottleneck", "None of 48 new-formula transformer draws met the frozen exact-cell gate. Twelve larger-cell ratio/geometry matches remain excluded; rejection is not proof of physical instability.", "structures"),
        ("model-results", "Eleven selected model calculations converged", "Four symmetry selections, four prepared prototypes and three references converged under CHGNet. Ten launches were new and one calculation was reused identically; prototypes did not replace the empty transformer shortlist.", "structures"),
        ("catalog-matching", "Unmatched is not globally novel", "Saved MP geometry coverage is 15/23 MgO and 34/44 TiO2 entries. Both P1 outputs are unmatched to this saved subset only.", "structures"),
        ("known-control", "Fresh DFT recovered known MgO", "The accepted generated MgO matches the known source reference. Its -0.005533 meV/atom energy difference is numerically unresolved; recovery is not discovery.", "evidence"),
        ("incomplete", "Perturbation and competition remain incomplete", "The 900-second perturbation stopped without accepted terminal SCF convergence. Source-reference coverage is 2/161 Ca-Mg-O and 1/57 Mg-O; no full competing-phase hull is established.", "evidence"),
        ("discovery", "No new stable material was established", "Model convergence, catalog absence, process exit zero and a known-phase DFT recovery cannot establish a newly discovered stable material, phonon stability or synthesis feasibility.", "evidence"),
    ]
    ctx.add_json("claims.json", {"claims": [{"id": ident, "title": title, "text": text,
                  "sourceIds": [source[key]], "claimStatus": "supported_with_stated_scope"}
                  for ident, title, text, key in claims],
                  "newStableMaterialEstablished": False,
                  "notes": ["Source hashes establish file identity, not scientific acceptance.",
                            "Predictive uncertainty, model energy, fresh DFT energy, novelty and stability are distinct concepts."]})
    terms = [
        ("historical-near-stable", "Historical near-stable", "The released signed WBM distance to a fixed historical MP hull is <=0.05 eV/atom. This is a retrospective label, not a new DFT result.", "eV/atom"),
        ("historical-reference-hull", "On/below the historical reference hull", "A released signed historical hull distance <=0. Negative signed values are preserved rather than clipped to zero.", "eV/atom"),
        ("calibration-radius", "Calibration radius", "The recorded interval half-width is q times max(ensemble disagreement, 0.01 eV/atom), using the frozen calibration procedure. Empirical coverage is evaluated separately.", "eV/atom"),
        ("disagreement", "Ensemble disagreement", "Sample standard deviation of the five member predictions. It can rank error without guaranteeing calibrated intervals under arbitrary distribution shift.", "eV/atom"),
        ("exact-cell", "Exact-cell validity", "Eligibility includes the requested expanded atom counts in the actual executed cell. The gate is a protocol/workload condition, not a physical stability label.", None),
        ("unique", "Unique structure", "A valid structure remaining after the protocol's tolerant structural deduplication. Multiple valid draws can collapse to one unique representative.", None),
        ("model-relaxed", "CHGNet relaxed", "A saved structure meets the stated model/optimizer convergence criterion. Its model energy is not a fresh QE energy or a thermodynamic hull distance.", "eV/atom"),
        ("dft-validation", "Fresh DFT validation", "Electronic/geometry acceptance and compatible finite sensitivity checks are separate from process completion. Accepted static calculations alone do not establish competition-hull or phonon stability.", None),
        ("reference-coverage", "Reference coverage", "Accepted source-reference IDs divided by the retained inventory memberships for the stated chemical system. A generated control does not add another source reference ID.", None),
        ("prototype", "Prototype substitution", "A predeclared known-template substitution baseline, distinct from transformer-generated outputs. A converged baseline is not automatically stable or globally novel.", None),
        ("ood", "Out-of-distribution scope", "The predictor withholds complete chemical systems within each split. This does not prove that generator pretraining excludes those compositions or establish universal OOD performance.", None),
        ("known-recovery", "Known-phase recovery", "A generated/relaxed control matches a named known phase. Reproducing it validates a workflow without establishing discovery of a new material.", None),
    ]
    ctx.add_json("glossary.json", {"terms": [{"id": ident, "label": label, "definition": definition, "unit": unit}
                                              for ident, label, definition, unit in terms]})
    ctx.add_json("theme.json", {
        "palette": {"paper": "#F6F2E9", "graphite": "#202A31", "copper": "#A85F37", "selection": "#164B6B"},
        "policyColours": {"random": "#777777", "quality": "#0072B2", "quality_diversity": "#009E73", "uncertainty": "#E69F00", "full": "#CC79A7", "initial_shared": "#555555"},
        "policyLabels": {"random": "Random", "quality": "Quality", "quality_diversity": "Quality + Diversity", "uncertainty": "Uncertainty", "full": "Full", "initial_shared": "Initial shared"},
        "elementColours": {"Mg": "#7B66B0", "Ca": "#D79731", "O": "#CE4945", "Ti": "#68889B", "Sn": "#648D78", "Sr": "#AD7992", "Ba": "#A0804C"},
        "statusLabels": {"generated": "Generated", "prototype_initial": "Prototype initial geometry", "catalog_initial": "Catalog initial geometry", "generated_excluded": "Generated: excluded by protocol", "model_relaxed": "CHGNet relaxed", "accepted_dft": "DFT validated: known phase/reference", "excluded": "Excluded by protocol", "incomplete": "Validation incomplete", "not_evaluated": "Not evaluated"},
        "typography": {"heading": "Georgia, serif", "body": "system-ui, sans-serif", "numeric": "ui-monospace, monospace"},
        "motion": {"autoRotationDefault": False, "respectReducedMotion": True},
    })
    notices = [
        {"name": "Wang-Botti-Marques / Matbench Discovery data", "role": "Historical labels and structure provenance", "licence": "CC-BY-4.0", "credit": "Hai-Chen Wang, Silvana Botti, Miguel A. L. Marques; Matbench Discovery curation by Janosh Riebesell and contributors", "url": "https://figshare.com/articles/dataset/Matbench_Discovery_v1_0_0/22715158", "licenceUrl": "https://creativecommons.org/licenses/by/4.0/", "modifications": "Selected records joined to local metadata, grouped and summarized for a frozen replay; no new historical labels generated."},
        {"name": "Materials Project 2022.10.28 snapshot", "role": "Pinned composition/reference catalog and source geometries", "licence": "CC-BY-4.0", "credit": "Materials Project Team; distributed snapshot in the Matbench Discovery data registry", "url": "https://github.com/janosh/matbench-discovery/blob/main/data/datasets.yml", "licenceUrl": "https://creativecommons.org/licenses/by/4.0/", "modifications": "Scoped composition membership/geometry subsets and separately computed compatible QE results; not a current/global catalog."},
        {"name": "CrystalFormer", "role": "Pretrained generator used in the frozen experiment", "licence": "Apache-2.0", "credit": "Zhendong Cao, Xiaoshan Luo, Jian Lv, Lei Wang and contributors", "url": "https://github.com/deepmodeling/CrystalFormer", "licenceUrl": "https://github.com/deepmodeling/CrystalFormer/blob/main/LICENSE", "modifications": "Existing pretrained model was used; the website distributes recorded outcomes, not model software or checkpoints."},
        {"name": "CHGNet", "role": "Model relaxation used in the frozen experiment", "licence": "Modified BSD (upstream CHGNet LICENSE)", "credit": "Bowen Deng, Peichen Zhong, KyuJung Jun, Janosh Riebesell, Kevin Han, Christopher J. Bartel, Gerbrand Ceder and contributors", "url": "https://github.com/CederGroupHub/chgnet", "licenceUrl": "https://raw.githubusercontent.com/CederGroupHub/chgnet/main/LICENSE", "modifications": "Displays saved model-relaxed geometries and metrics; no model software or checkpoints redistributed."},
        {"name": "Quantum ESPRESSO", "role": "Fresh PBE calculations used in the frozen experiment", "licence": "GPL-2.0 scientific software; executables not redistributed in the website", "credit": "Quantum ESPRESSO authors and contributors", "url": "https://www.quantum-espresso.org/", "licenceUrl": None, "modifications": "Displays local calculation outcomes and convergence evidence; no executables or pseudopotential files redistributed."},
    ]
    ctx.add_json("methods.json", {
        "title": "The Flamel Project", "headline": "Explore the search for new crystals.",
        "description": "An interactive research prototype connecting symmetry, predictive uncertainty and first-principles validation. Explore what worked, what failed, and what the evidence supports.",
        "executionMode": "recorded_research_only", "liveScientificCompute": False,
        "target": {"name": "e_above_hull_mp2020_corrected_ppd_mp", "unit": "eV/atom", "nearStableInclusive": .05, "referenceHullInclusive": 0, "freshQETargetCompatible": False},
        "workflow": [{"id": ident, "label": label, "description": description} for ident, label, description in [
            ("propose", "Propose", "Six formulas absent only from the two pinned historical catalogs; four separate prototype baselines."),
            ("generate", "Generate", "Recorded CrystalFormer outputs under matched symmetry conditions; no new sampling in this website."),
            ("screen", "Screen", "Exact-cell workload/geometry gates retain failures and excluded larger-cell diagnostics."),
            ("select", "Select", "Historical acquisition replay is separate from the fresh initial-selector workflow. The new-formula fresh shortlist is empty."),
            ("relax", "Relax", "Eleven selected model calculations converged, including one verified identical cached reuse."),
            ("validate", "Validate", "The predetermined known MgO fallback and compatible oxide references received genuine QE calculations."),
            ("compare", "Compare", "Known-phase recovery is accepted within measured finite sensitivity; perturbation and reference competition remain incomplete.")]],
        "sourceIds": list(source.values()), "attributions": notices,
        "externalPublicationLinks": [{"kind": kind, "label": label, "url": None, "status": "not_published"}
                                      for kind, label in [("repository", "Code repository"), ("writeup", "One-page account"), ("video", "Presentation video")]],
        "sourceRegistryReference": "https://github.com/janosh/matbench-discovery/blob/main/data/datasets.yml",
        "scope": ["Five overlapping dataset splits are descriptive, not independent-dataset significance evidence.",
                  "Hidden reveal labels are a teaching display state, not access-controlled secret data.",
                  "No new stable material, complete hull, phonon stability or synthesis result is established."]})
    figures = {
        "figures/overview.png": "artifacts/phase6/figures/research_overview.png",
        "figures/uncertainty.png": "artifacts/phase6/uncertainty/uncertainty_reliability.png",
        "figures/structures.png": "artifacts/phase6/structures/representative_structures.png",
        "figures/generation.png": "artifacts/phase4/figures/primary_generation.png",
        "figures/model-energies.png": "artifacts/phase5/figures/within_composition_energies.png",
    }
    for logical, original in figures.items():
        ctx.add_asset(logical, ctx.read_asset(original))
    ctx.check(uncertainty["new_pool_queries"] == 0 and structures["new_generator_draws"] == 0
              and not evidence["new_stable_material_established"], "Content matches closed scientific scope")
