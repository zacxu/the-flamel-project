# Workflow visual scientific review

Reviewed on 23 October 2026 (Singapore time). Scope: the seven stage illustrations, captions, accessible SVG descriptions and surrounding workflow text in `src/components/WorkflowIllustration.tsx` and `src/views/Workflow.tsx`. This is a presentation review of frozen evidence; it adds no numerical experiment or scientific finding.

**Result: no outstanding material scientific issue in the reviewed source.** All three requested clarifications are present: formula and space group condition CrystalFormer while exact cell size is checked after sampling; draws “reach” the eligibility gate; the two-sided uncertainty graphic is labelled “calibrated interval.”

| Stage | Reviewed scientific scope | Local grounding |
|---|---|---|
| Propose | Oxide compositions, two pinned catalog checks, six new-to-reference proposals, separate known controls and four prototypes. Catalog absence does not establish global novelty or exclusion from generator pretraining. | `../../reports/phase2_report.md`, catalog/composition section; `../../artifacts/phase6/structures/composition_novelty.csv` |
| Generate | Frozen pretrained CrystalFormer v0.6, autoregressive sampling, formula and space-group conditioning, conceptual periodic output. P1 and nontrivial conditioning use the same symmetry-aware architecture. The requested six-atom cell is a downstream gate, not an exact-size model input. | `../../vendor/CrystalFormer/README.md`, model card; `../../vendor/CrystalFormer/crystalformer/src/sample.py`; `../../scripts/phase3_generate.py` |
| Screen | Frozen composition, exact evaluated-cell and geometry checks. The twelve-atom CaMg2O3 example fails the six-atom cell requirement. Zero of 48 new-formula draws qualify; 12 larger-cell diagnostic matches remain excluded. | `../../reports/phase6_report.md`, symmetry/composition section; `../../artifacts/phase6/structures/generation_draws.csv` |
| Select | Five outer-bootstrap ExtraTrees members, each with 128 trees and 408 initial-only descriptors. Interval radius is q times max(member disagreement, 0.01 eV/atom). The five-policy historical replay reveals existing labels and stays separate from fresh QE. | `../../reports/phase3_report.md`, initial model section; `../../research_models.py`; `../../research_acquisition.py`; `../../reports/phase6_report.md`, acquisition section |
| Relax | Conceptual neighbor graph and pretrained CHGNet energy; energy derivatives supply forces and stress. FIRE updates atomic coordinates and cell. Eleven selected results converge, including one verified cached reuse. The drawings are not observed geometries or trajectories. | `../../reports/phase5_report.md`; `../../artifacts/phase5/chgnet/summary.json`; installed `chgnet/model/model.py`, energy-derivative computation |
| Validate | Predetermined known-MgO control and compatible source-reference branch; QE/PBE acceptance includes terminal electronic state, forces/full stress and finite cutoff/k-point sensitivity. Three accepted geometries do not establish a complete hull or a new stable material. | `../../reports/phase6_report.md`, fresh DFT section; `../../artifacts/phase6/evidence/fresh_DFT_evidence_table.csv`; `../../artifacts/phase6/evidence/reference_inventory_completeness.csv` |
| Compare | Actual descriptive historical means: Quality 41.2 versus Full 29.4 near-stable hits per 50 queries; 32.8 versus 42.2 chemical systems. Five splits overlap. Known-MgO recovery, incomplete broader reference/perturbation validation and zero newly established stable materials remain explicit. | `../../reports/phase6_report.md`, acquisition and frozen-conclusion sections |

The diagrams deliberately label conceptual geometry, token boxes, graph messages and wave curves as simplified representations. They do not depict literal layer layouts, measured candidate predictions, actual wavefunctions, a new trained transformer, or an uninterrupted successful new-formula discovery pipeline. Historical WBM hull-distance labels, CHGNet estimates and fresh QE energies remain separate quantities.

Primary references checked for the model schematics:

- [CrystalFormer official repository](https://github.com/deepmodeling/CrystalFormer): autoregressive symmetry-aware representation and symmetry reconstruction. The pinned local implementation defines the executed experiment.
- [CHGNet official repository](https://github.com/CederGroupHub/chgnet) and [primary paper](https://doi.org/10.1038/s42256-023-00716-3): pretrained crystal graph potential and atomistic relaxation.
- [ExtraTreesRegressor official documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html): estimator reference; the local protocol and source define the five outer-bootstrap members and frozen hyperparameters.

This review assesses scientific presentation only. Browser layout, keyboard behavior, asset loading and deployment are verified separately by the implementation owner.
