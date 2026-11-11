# Workflow stage visuals

The Workflow tab includes an original visual explainer for each of its seven selectable stages. These are simplified SVG schematics of the recorded methods. Crystal cartoons, tree sketches and model blocks are explanatory drawings; they are not saved atomic geometries, exact neural-network layer diagrams or an animation of an observed relaxation trajectory.

The illustrations use the existing paper, copper and blue palette. Their cards stack on narrow screens, retain native text descriptions and require no remote image service, new dependency or scientific computation. Stage buttons, source drawers and the guided presentation keep their existing behavior.

CrystalFormer is shown as structured inputs and embeddings, repeated causal attention/feed-forward blocks, output distributions and symmetry reconstruction. CHGNet is shown as an atom graph with an auxiliary bond graph, coupled feature updates, site-energy pooling and energy derivatives used by the optimizer. Exact layer counts and checkpoint hyperparameters are deliberately omitted. The six-atom requirement is a screening gate after generation. Comparison bars use the shared `policyColour()` presentation helper, including its existing contrast corrections.

The Overview and Workflow contribution text credits the pretrained models and highlights this project's decision layer, controlled evaluation and evidence trail. It does not claim a new foundation model, a proven general uncertainty advantage or a newly established stable material.

| Stage | Evidence that constrains the illustration |
|---|---|
| Propose | Six oxide formulas absent from the pinned MP and WBM composition snapshots; this is not proof of global novelty. See `reports/phase2_report.md` and `artifacts/phase6/structures/composition_novelty.csv` in the research workspace. |
| Generate | Frozen pretrained CrystalFormer, with the same symmetry-aware architecture for P1 and nontrivial conditioning. Species/Wyckoff/coordinate sampling and symmetry reconstruction are conceptual, not an added uncertainty head. See `vendor/CrystalFormer/README.md`, its sampling code and `reports/phase6_report.md`. |
| Screen | Forty-eight new-formula draws produced zero exact-cell eligible candidates. Twelve larger-cell diagnostics remain excluded. The separate planned control and prototype branches must not be portrayed as survivors of this failed branch. See the Phase 6 generation tables. |
| Select | Five outer-bootstrap members, each with 128 ExtraTrees, use 408 initial-only descriptors. Calibrated disagreement and diversity inform the recorded historical policies. This is separate from the pretrained generator and the empty fresh new-formula shortlist. See `reports/phase3_report.md`, `research_acquisition.py` and the Phase 6 acquisition results. |
| Relax | CHGNet's learned energy supplies force/stress derivatives used in position/cell relaxation. Eleven selected model results converged, including one verified cached reuse. Model relaxation alone is not DFT validation or a stability claim. See the Phase 6 structure results and installed CHGNet model code. |
| Validate | Nineteen charged QE jobs include attempts, continuations and checks; three distinct geometries passed the saved finite checks. These are the known generated MgO control and compatible source MgO/CaO references. The perturbation and complete competing-reference hull remain incomplete. See `artifacts/phase6/evidence/fresh_DFT_evidence_table.csv` and `reports/phase6_report.md`. |
| Compare | Quality versus Full means are 41.2 versus 29.4 historical near-stable hits per 50 queries, across five overlapping splits. Primary exact-cell contrasts and known-phase recovery are separately scoped. No newly established DFT-confirmed stable novel material is implied. See the Phase 6 results and exported website datasets. |

Primary model references checked for the schematics:

- [CrystalFormer official implementation](https://github.com/deepmodeling/CrystalFormer).
- [ExtraTreesRegressor official documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html). The five outer-bootstrap members are this project's implementation choice.
- [CHGNet official implementation](https://github.com/CederGroupHub/chgnet) and [primary paper](https://doi.org/10.1038/s42256-023-00716-3).

The existing source-record controls remain the path to the actual saved research evidence. The frozen data release and its scientific images are not modified by these explanatory visuals.
