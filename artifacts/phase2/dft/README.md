# Phase 2 DFT plan: Ca-Mg-O / CaMg2O3

The primary composition is **CaMg2O3 (six reduced atoms)**, selected by the shared
label-blind composition protocol and absent from both named frozen WBM and MP
composition catalogs. This is catalog-scoped absence, not global novelty.

The complete MP2022 reference inventory contains **161 entries** across Ca, Mg,
O, Ca-Mg, Ca-O, Mg-O and Ca-Mg-O. All source/primitive JSON geometries and CIFs
are retained under data/references/mp_2022_10_28. Tight geometry-only matching
found no aliases; no source energy or hull filtering was used. Twenty-one entries
have more than20 informational primitive atoms, including a150-atom CaMg149 phase. Known
ternaries include CaMg3O4 and CaMgO3; spin/occupancy-ambiguous references are flagged.
The alternate Mg-O inventory contains57 entries, including14 over20 atoms.
For execution, ALL original source cells are retained: 21 primary
and 14 fallback cells exceed20 atoms; the largest primary source
cell has150 atoms. Primitive copies are informational and unverified,
never used for QE. In particular mp-1183575 retains its original4-atom CaMg cell.
Source site properties are preserved in JSON; magnetic-order metadata still needs
explicit QE spin initialization/review before any flagged reference is executed.
Neither inventory is promised to be fully recalculated within the six-hour cap.
These reference geometries cover the named MP snapshot only: additional WBM
structures are not part of the fresh QE reference inventory. WBM is used for
composition absence and the separate replay. A complete MP-inventory result
would still not establish stability against every known or published phase.

The first small reference queue is CaO rocksalt mp-2605, MgO rocksalt mp-1265,
Mg hcp mp-153 and Ca fcc mp-45, selected by documented prototypes, not source
energies. All other phases remain visible in reference_queue.csv. The primary
candidate has an explicit test reaction **CaMg2O3 -> CaO +2MgO**:

    delta [eV/atom] = e_candidate - e_CaO/3 - 2e_MgO/3

A clearly positive value demonstrates instability against that reaction. A clearly
negative value only beats those two binary anchors. It is not stability against the
full161-entry reference inventory. Candidate-vs-candidate competition must also
be checked. Margins comparable to the measured numerical sensitivity remain
unresolved; start with a5-meV/atom guard and enlarge it when actual shifts require.

Templates use PBE, the same checksum-identified UPF per element, shared starting
50/400-Ry cutoffs, reciprocal spacing0.60/A with denser probes, electronic1e-8Ry,
force8e-4Ry/Bohr (~0.02057eV/A), pressure0.5kbar, and unconstrained solid-cell
relaxation with nosym/noinv. The inputs are starting templates, not converged
production settings. Cutoff/k/smearing/spin/vacuum checks must be executed later.
After choosing final cutoff/k settings, recheck force vectors and full stress at
those exact settings. Continue geometry/cell relaxation if stationarity fails,
then repeat checks before accepting energies; small energy shifts alone are insufficient.
For solids, final acceptance requires both absolute scalar pressure<=0.5kbar and
every residual stress-tensor component<=0.5kbar in absolute value; a small trace
cannot hide shear. Independently check maximum atomic force-vector norm<=0.02057eV/A.
O2 triplet templates have fixed12/15/18-A boxes and fixed total magnetization2muB;
solid-oxygen entries are retained independently. Missing spin review blocks a
complete reference claim. No MP/VASP, WBM or CHGNet energy is mixed into QE.

The existing QE ledger has1 known-phase job consuming
2.103913s, leaving21597.896087s. Budget planning allocates9000s for
references/anchors,5400s for one or two candidates,5400s for numerical checks,
and1797.896087s for failures/restarts. These are ceilings/planning envelopes,
not promised runtimes. The2.104-second symmetric two-atom SCF pilot cannot predict
larger nonsymmetric relaxations or molecular/spin workloads. Run one QE job with
four threads at a time and append every attempt to the existing QE ledger.

**No QE or CHGNet calculation ran in Phase2.** All221 QE input templates
were parsed with ASE, and geometry/hash checks passed. This validates input
syntax/geometry, not electronic convergence or stability. Stage checksum-verified
UPFs and scratch directories when creating actual Phase3 jobs.

Entry points:

    .envs/analysis/Scripts/python.exe -W ignore::FutureWarning scripts/phase2_dft.py inventory
    .envs/analysis/Scripts/python.exe -W ignore::FutureWarning scripts/phase2_dft.py prepare --system Ca-Mg-O
    .envs/analysis/Scripts/python.exe scripts/phase2_dft_finalize.py

The frozen plan is reference_plan.json; numerical_protocol.json and
budget_forecast.json contain acceptance and stopping rules. Primary and fallback
reference_plan files retain every entry and template. Phase3 must freeze early
candidate IDs and pool provenance before candidate DFT outcomes.

Source geometry archive: https://figshare.com/files/40344436, MP2022 export,
MD5 76fc748db6b175bb80de4c276d27c235. SSSP source:
https://archive.materialscloud.org/record/2023.65. QE input definitions:
https://www.quantum-espresso.org/Doc/INPUT_PW.html.
