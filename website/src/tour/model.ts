import type { RouteState } from '../state/route.ts';

export type TourSceneId = 'idea' | 'workflow-propose' | 'workflow-generate' | 'workflow-screen'
  | 'replay-zero' | 'replay-ten' | 'replay-twenty' | 'replay-thirty' | 'replay-forty' | 'replay-fifty' | 'replay-full' | 'replay-aggregate'
  | 'crystal-mgo' | 'crystal-prototype' | 'crystal-excluded' | 'symmetry-mgo' | 'symmetry-tio2' | 'symmetry-energy'
  | 'uncertainty-low' | 'uncertainty-high' | 'uncertainty-retain' | 'uncertainty-all' | 'evidence-jobs' | 'evidence-incomplete' | 'evidence-sources';
export interface TourScene {
  readonly id: TourSceneId; readonly at: number; readonly view: RouteState['view'];
  readonly caption: string; readonly anchor?: string; readonly patch?: Partial<RouteState>;
  readonly exampleId?: string; readonly stage?: 'accepted_dft' | 'model_relaxed' | 'generated_excluded';
}
export interface TourStep { readonly title: string; readonly seconds: number; readonly scenes: readonly TourScene[] }
const replay = (id: TourSceneId, at: number, budget: RouteState['budget']): TourScene => ({
  id, at, view: 'replay', anchor: 'replay-curves-heading',
  caption: `${budget} of 50 historical queries, at recorded batch boundaries. Quality and Full use the same label budget.`,
  patch: { mode: 'seed', seed: 20261022, policies: ['quality', 'full'], policy: 'quality', budget,
    batch: Math.max(1, budget / 10) as RouteState['batch'] },
});
/** A presentation script over immutable records. No policy, generation or scientific calculation executes here. */
export const TOUR_STEPS: readonly TourStep[] = [
  { title: 'Idea and workflow', seconds: 25, scenes: [
    { id: 'idea', at: 0, view: 'overview', anchor: 'overview-title', caption: 'An integrated crystal-discovery prototype. The historical acquisition study and fresh-structure study remain separate.' },
    { id: 'workflow-propose', at: 8, view: 'workflow', anchor: 'workflow-detail', caption: 'Six formula proposals were absent from two pinned composition snapshots; this is a historical snapshot claim.' },
    { id: 'workflow-generate', at: 14, view: 'workflow', anchor: 'workflow-detail', caption: 'A pretrained symmetry-aware transformer generated the recorded draws. Both conditioning arms use the same architecture.' },
    { id: 'workflow-screen', at: 20, view: 'workflow', anchor: 'tracks-heading', caption: 'No new-formula transformer draw passed the exact-cell gate. The known-control and prototype branches keep their own scope.' },
  ] },
  { title: 'Five-batch acquisition replay', seconds: 45, scenes: [
    replay('replay-zero', 0, 0), replay('replay-ten', 5, 10), replay('replay-twenty', 11, 20),
    replay('replay-thirty', 17, 30), replay('replay-forty', 23, 40), replay('replay-fifty', 29, 50),
    { ...replay('replay-full', 35, 50), patch: { ...replay('replay-full', 35, 50).patch, policy: 'full' }, caption: 'Inspect Full at the same 50-query endpoint. Broader chemistry coverage came with fewer historical near-stable hits.' },
    { id: 'replay-aggregate', at: 39, view: 'replay', anchor: 'replay-table-heading', patch: { mode: 'aggregate', policies: ['quality', 'full'], policy: 'full', budget: 50, batch: 5 }, caption: 'Five overlapping splits: Quality retrieved more near-stable records in every paired split. Mean and sample SD describe saved retrieval outcomes.' },
  ] },
  { title: 'Real structures and eligibility', seconds: 35, scenes: [
    { id: 'crystal-mgo', at: 0, view: 'crystals', anchor: 'crystal-workspace', exampleId: 'known-mgo-sequence', stage: 'accepted_dft', caption: 'Rotate the actual eight-atom, finite-checked known-MgO control. This is known-phase recovery.' },
    { id: 'crystal-prototype', at: 12, view: 'crystals', anchor: 'crystal-workspace', exampleId: 'camg2o3-prototype', stage: 'model_relaxed', caption: 'Six-atom CaMg₂O₃ is a prepared prototype baseline, relaxed by CHGNet. Model convergence is separate from DFT validation.' },
    { id: 'crystal-excluded', at: 24, view: 'crystals', anchor: 'crystal-workspace', exampleId: 'camg2o3-excluded-twelve-atom', stage: 'generated_excluded', caption: 'The twelve-atom transformer draw has a matching reduced ratio but fails the frozen six-atom exact-cell gate. Its saved geometry remains excluded.' },
  ] },
  { title: 'Symmetry conditioning and energy', seconds: 30, scenes: [
    { id: 'symmetry-mgo', at: 0, view: 'findings', anchor: 'symmetry-results-heading', patch: { scope: 'primary' }, caption: 'Primary MgO: 7/8 versus 0/8 exact-cell valid; unique yield 1/8 versus 0/8. Same architecture, different conditioning.' },
    { id: 'symmetry-tio2', at: 10, view: 'findings', anchor: 'symmetry-results-heading', patch: { scope: 'primary' }, caption: 'Primary TiO₂: 6/8 versus 1/8 valid, but 1/8 unique in both arms. Validity and unique yield answer different questions.' },
    { id: 'symmetry-energy', at: 20, view: 'findings', anchor: 'symmetry-energy-heading', patch: { scope: 'primary' }, caption: 'One selected CHGNet structure per arm. The MgO energy pair comes from the supplementary primary-plus-top-up pool; it does not change the primary yield denominators.' },
  ] },
  { title: 'Uncertainty and selective risk', seconds: 25, scenes: [
    { id: 'uncertainty-low', at: 0, view: 'findings', anchor: 'uncertainty-findings-heading', patch: { seed: 20261023, endpoint: 'full', retainedFraction: 1 }, caption: 'Full, split 20261023: empirical interval coverage is below the nominal 90% target. The displayed table gives the actual saved result.' },
    { id: 'uncertainty-high', at: 8, view: 'findings', anchor: 'uncertainty-findings-heading', patch: { seed: 20261024, endpoint: 'full', retainedFraction: 1 }, caption: 'Full, split 20261024: coverage is above 90%. Calibration varies by held-out split.' },
    { id: 'uncertainty-retain', at: 16, view: 'findings', anchor: 'risk-heading', patch: { seed: 20261024, endpoint: 'full', retainedFraction: 0.1 }, caption: 'Retain the saved lowest-uncertainty 10% subset: 342 of 3,418 rows after rounding. Subset MAE is a diagnostic, not a newly evaluated acquisition policy.' },
    { id: 'uncertainty-all', at: 21, view: 'findings', anchor: 'risk-heading', patch: { seed: 20261024, endpoint: 'full', retainedFraction: 1 }, caption: 'Restore all 3,418 rows. Compare selected-subset error with all-row error without claiming improved predictions for the complete population.' },
  ] },
  { title: 'Validation, limits and sources', seconds: 20, scenes: [
    { id: 'evidence-jobs', at: 0, view: 'evidence', anchor: 'dft-ledger-heading', caption: 'All nineteen real QE jobs remain visible. Process completion, terminal SCF, stationarity and full finite checks are separate fields.' },
    { id: 'evidence-incomplete', at: 8, view: 'evidence', anchor: 'dft-ledger-heading', caption: 'The 900-second perturbation is incomplete: no accepted terminal energy, force or stress. Three accepted geometries correspond to two original source-reference IDs.' },
    { id: 'evidence-sources', at: 14, view: 'evidence', anchor: 'methods-report-heading', caption: 'Only 2/161 primary and 1/57 fallback memberships are computed. No complete competing-phase hull or new stable material was established. Open the public source records to reproduce the account.' },
  ] },
];
export const TOUR_TOTAL_SECONDS = TOUR_STEPS.reduce((sum, step) => sum + step.seconds, 0);
export interface TourSnapshot {
  readonly status: 'idle' | 'running' | 'paused' | 'complete'; readonly step: number;
  readonly elapsed: number; readonly scene: TourScene | null;
}
export interface TourScheduler { now(): number; schedule(callback: () => void): unknown; cancel(handle: unknown): void }
export function createTourController(scheduler: TourScheduler, present: (scene: TourScene) => void) {
  let snapshot: TourSnapshot = { status: 'idle', step: 0, elapsed: 0, scene: null };
  let timer: unknown; let epoch = 0; let anchor = 0;
  const listeners = new Set<() => void>();
  const emit = () => { for (const listener of listeners) listener(); };
  const clear = () => { epoch++; if (timer !== undefined) scheduler.cancel(timer); timer = undefined; };
  const sceneAt = (step: number, elapsed: number) => [...TOUR_STEPS[step].scenes].reverse().find(scene => scene.at <= elapsed)!;
  const setPosition = (step: number, elapsed: number, status: TourSnapshot['status']) => {
    const scene = sceneAt(step, elapsed);
    const changed = scene.id !== snapshot.scene?.id;
    snapshot = { status, step, elapsed, scene };
    if (changed) present(scene);
    emit();
  };
  function queue() {
    const scheduledEpoch = epoch;
    timer = scheduler.schedule(() => {
      if (epoch !== scheduledEpoch || snapshot.status !== 'running') return;
      timer = undefined;
      let elapsed = Math.max(snapshot.elapsed, (scheduler.now() - anchor) / 1000);
      let step = snapshot.step;
      while (elapsed >= TOUR_STEPS[step].seconds) {
        elapsed -= TOUR_STEPS[step].seconds;
        if (step === TOUR_STEPS.length - 1) {
          clear(); setPosition(step, TOUR_STEPS[step].seconds, 'complete'); return;
        }
        step++; anchor += TOUR_STEPS[step - 1].seconds * 1000;
      }
      setPosition(step, elapsed, 'running'); queue();
    });
  }
  function go(step: number) {
    const running = snapshot.status === 'running'; clear();
    anchor = scheduler.now(); setPosition(Math.max(0, Math.min(TOUR_STEPS.length - 1, step)), 0, running ? 'running' : 'paused');
    if (running) queue();
  }
  return {
    getSnapshot: () => snapshot,
    subscribe(callback: () => void) { listeners.add(callback); return () => { listeners.delete(callback); }; },
    start() { clear(); snapshot = { status: 'running', step: 0, elapsed: 0, scene: null }; anchor = scheduler.now(); setPosition(0, 0, 'running'); queue(); },
    pause() {
      if (snapshot.status !== 'running') return;
      clear(); snapshot = { ...snapshot, status: 'paused' }; emit();
    },
    resume() { if (snapshot.status !== 'paused') return; clear(); anchor = scheduler.now() - snapshot.elapsed * 1000; snapshot = { ...snapshot, status: 'running' }; emit(); queue(); },
    next() { if (snapshot.status === 'idle' || snapshot.status === 'complete') return; if (snapshot.step === TOUR_STEPS.length - 1) { clear(); snapshot = { ...snapshot, status: 'complete', elapsed: TOUR_STEPS[snapshot.step].seconds }; emit(); } else go(snapshot.step + 1); },
    previous() { if (snapshot.status !== 'idle') go(snapshot.step === 0 ? 0 : snapshot.step - 1); },
    exit() { clear(); snapshot = { status: 'idle', step: 0, elapsed: 0, scene: null }; emit(); },
    dispose() { clear(); listeners.clear(); },
  };
}
