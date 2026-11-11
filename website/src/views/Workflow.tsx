import { useEffect, useState } from 'react';
import { useTourScene } from '../tour/TourContext';
import type { CoreData } from '../data/ResearchData';
import type { RouteState } from '../state/route';
import { WorkflowIllustration } from '../components/WorkflowIllustration';
import '../components/WorkflowIllustration.css';

type View = 'overview' | 'workflow' | 'replay' | 'crystals' | 'findings' | 'evidence';
interface Props {
  data: CoreData;
  navigate: (view: View, patch?: Partial<RouteState>) => void;
  onSources: (ids?: readonly string[]) => void;
  onGlossary: () => void;
}
type Step = CoreData['methods']['workflow'][number]['id'];
interface StepDetail { input: string; output: string; status: string; example: string; view: View; action: string; sourceIds: readonly string[] }

export function Workflow({ data, navigate, onSources, onGlossary }: Props) {
  const [selected, setSelected] = useState<Step>('propose');
  const tour = useTourScene();
  useEffect(() => {
    if (tour.scene?.id === 'workflow-propose') setSelected('propose');
    if (tour.scene?.id === 'workflow-generate') setSelected('generate');
    if (tour.scene?.id === 'workflow-screen') setSelected('screen');
  }, [tour.scene?.id]);
  const { summary, methods } = data;
  const details: Record<Step, StepDetail> = {
    propose: {
      input: 'Simple oxide compositions and two pinned historical composition snapshots.',
      output: 'Six new-to-reference formula proposals, alongside separate known controls and four prepared prototype baselines.',
      status: 'Proposal scope frozen',
      example: 'CaMg₂O₃ is one proposal. Absence from these two snapshots does not establish global novelty or exclusion from generator training.',
      view: 'findings', action: 'Inspect composition evidence', sourceIds: ['structures_summary'],
    },
    generate: {
      input: 'Formula and symmetry conditioning passed to pretrained CrystalFormer, with the requested cell size enforced during screening.',
      output: `${summary.counts.actualCrystalFormerDraws} recorded draws across primary controls, supplementary controls and new-formula cohorts.`,
      status: 'Saved generation results',
      example: 'The primary first-eight MgO arms yielded 7/8 versus 0/8 exact-cell valid draws. Both arms use the same symmetry-aware architecture.',
      view: 'findings', action: 'Inspect generation findings', sourceIds: ['structures_summary'],
    },
    screen: {
      input: 'Saved generated lattices, species counts and coordinates.',
      output: `${summary.counts.newFormulaExactValid}/${summary.counts.newFormulaDraws} eligible new-formula draws; ${summary.counts.excludedNewFormulaLargerCellDiagnostics} larger-cell diagnostics remain excluded.`,
      status: 'New-formula path stops here',
      example: 'The twelve-atom CaMg₂O₃ draw has the requested reduced ratio but fails the frozen six-atom cell gate. Viewing its geometry never makes it eligible.',
      view: 'crystals', action: 'Inspect saved structures', sourceIds: ['structures_summary'],
    },
    select: {
      input: 'Historical predicted mean, calibrated disagreement radius and diversity; separately, eligible fresh candidates.',
      output: 'Five recorded acquisition policies with equal historical label budgets. The new-formula fresh shortlist is empty.',
      status: 'Two distinct selection settings',
      example: 'Full combines quality, uncertainty and diversity. It found fewer historical near-stable labels than Quality in every paired split.',
      view: 'replay', action: 'Open the recorded comparison', sourceIds: data.curves.sourceIds,
    },
    relax: {
      input: 'Selected known controls, catalog references and the four prototype baselines.',
      output: `${summary.counts.modelSelectedStructures} converged CHGNet results: ten new launches and one verified cached reuse.`,
      status: 'Model relaxation complete',
      example: 'The six-atom CaMg₂O₃ prototype converged under CHGNet. It is a prepared baseline, separate from the excluded transformer draw, and has no fresh candidate DFT result.',
      view: 'crystals', action: 'Inspect the saved stages', sourceIds: ['structures_summary'],
    },
    validate: {
      input: 'The separately predetermined known-MgO control and compatible oxide source references.',
      output: `${summary.counts.qeAttempts} charged QE jobs, including checks and failures; ${summary.counts.acceptedRelaxedQeGeometries} geometries accepted with finite sensitivity checks.`,
      status: 'Known-control evidence; incomplete broader validation',
      example: 'Generated eight-atom MgO, source-reference MgO and source-reference CaO are distinct accepted geometries. A process exit or JOB DONE alone does not establish validation.',
      view: 'evidence', action: 'Inspect validation records', sourceIds: ['evidence_summary'],
    },
    compare: {
      input: 'Comparable saved results within each scientific track, with their matching units and settings.',
      output: 'A negative acquisition result, a scoped symmetry-conditioning contrast and known-phase recovery.',
      status: 'No new stable material established',
      example: 'Only 2/161 primary and 1/57 fallback reference entries were computed. The 900-second perturbation remains incomplete, so a full competing-phase hull was not established.',
      view: 'evidence', action: 'Trace claims to evidence', sourceIds: summary.sourceIds,
    },
  };
  const current = methods.workflow.find(step => step.id === selected)!;
  const detail = details[selected];

  return <div className="workflow-page">
    <header className="view-header"><p className="eyebrow">From hypothesis to evidence</p><h1 className="page-heading" tabIndex={-1}>Follow the experiment.</h1><p className="lede">Seven stages connect symmetry-conditioned generation, uncertainty-aware selection and genuine first-principles checks. Every step below describes saved work.</p></header>
    <section className="workflow-contribution" aria-labelledby="workflow-contribution-heading">
      <div><p className="workflow-illustration-kicker">Our contribution</p><h2 id="workflow-contribution-heading">Turning crystal generation into a testable discovery workflow.</h2></div>
      <div><p>We built and evaluated a prototype for oxide discovery within fixed query and compute budgets. Pretrained CrystalFormer and CHGNet provide the models; our work connects them to selection logic, controlled experiments and traceable validation.</p>
        <ul><li><strong>Designed the decision layer.</strong> A calibrated ensemble supplies quality and uncertainty estimates; acquisition policies also account for diversity.</li><li><strong>Ran controlled comparisons.</strong> Equal query budgets, whole chemical-system holdouts and matched symmetry-conditioning tests.</li><li><strong>Made the evidence inspectable.</strong> Exact-cell gates, saved relaxations, failed attempts and audited first-principles checks remain available.</li></ul>
      </div>
    </section>
    <nav className="workflow-nodes" aria-label="Research workflow stages">
      {methods.workflow.map((step, index) => <button key={step.id} className={`workflow-node${selected === step.id ? ' is-active' : ''}`} aria-pressed={selected === step.id} aria-controls="workflow-detail" onClick={() => setSelected(step.id)}><span className="workflow-number">0{index + 1}</span><span>{step.label}</span>{index < methods.workflow.length - 1 && <span className="workflow-arrow" aria-hidden="true">→</span>}</button>)}
    </nav>
    <section id="workflow-detail" className="workflow-detail" aria-live="polite" aria-atomic="true" aria-labelledby="workflow-step-heading">
      <div className="workflow-detail-heading"><div><p className="eyebrow">Selected stage</p><h2 id="workflow-step-heading" className="section-heading">{current.label}</h2></div><span className={`status-badge${selected === 'screen' || selected === 'compare' ? ' status-warning' : ''}`}>{detail.status}</span></div>
      <p>{current.description}</p>
      <WorkflowIllustration stage={selected} data={data} />
      <dl className="input-output"><div><dt>Input</dt><dd>{detail.input}</dd></div><div><dt>Recorded output</dt><dd>{detail.output}</dd></div></dl>
      <p className="workflow-example"><strong>Real example.</strong> {detail.example}</p>
      <div className="detail-actions"><button className="button button-secondary" onClick={() => navigate(detail.view)}>{detail.action} <span aria-hidden="true">↗</span></button><button className="source-link" onClick={() => onSources(detail.sourceIds)}>View source records</button></div>
    </section>

    <section className="workflow-tracks" aria-labelledby="tracks-heading"><div className="section-heading-row"><div><p className="eyebrow">How the branches relate</p><h2 id="tracks-heading" className="section-heading">Two scientific tracks.</h2></div><button className="source-link" onClick={onGlossary}>Explain the targets</button></div>
      <article className="track track-historical"><p className="eyebrow">01 · Historical acquisition</p><h3>Predict → select → reveal saved labels</h3><p>Five overlapping chemical-system splits, five policies and 50 historical queries per policy/split. Predictions precede each recorded batch of ten label reveals; this is separate from fresh crystal generation.</p><div className="track-path"><span>Existing WBM structures</span><span aria-hidden="true">→</span><span>Recorded policy decisions</span><span aria-hidden="true">→</span><span>Historical signed hull targets</span></div><p className="scope-note">Near-stable: target ≤0.05 eV/atom. On/below reference hull: target ≤0. These outcomes are historical retrieval labels.</p><button className="source-link" onClick={() => navigate('replay')}>Replay the saved acquisition <span aria-hidden="true">→</span></button></article>
      <article className="track track-fresh"><p className="eyebrow">02 · Fresh structures and validation</p><h3>Generate → screen → inspect separate branches</h3>
        <div className="track-branches">
          <div className="track-branch"><h4>Six new-to-reference formulas</h4><p>48 transformer draws → exact-cell gate</p><p className="track-stop"><strong>0 eligible.</strong> This path ends before fresh candidate DFT. Twelve larger-cell diagnostics stay excluded.</p></div>
          <div className="track-branch"><h4>Predetermined known-MgO control</h4><p>Saved generated MgO → CHGNet → QE and compatible source references</p><p><strong>Known-phase recovery.</strong> The control follows its own planned branch; it is not a successful new-formula discovery.</p></div>
          <div className="track-branch"><h4>Four prepared prototype baselines</h4><p>Prototype substitution → CHGNet relaxation</p><p><strong>Four converged model baselines.</strong> Their convergence adds no successes to the transformer’s 0/48 yield.</p></div>
        </div>
        <button className="source-link" onClick={() => navigate('crystals')}>Inspect real saved structures <span aria-hidden="true">→</span></button>
      </article>
    </section>
    <aside className="scope-note workflow-target-note"><strong>Keep the targets distinct.</strong> Historical signed hull-distance labels and fresh QE total energies are different quantities. The website does not combine them into interchangeable feedback, retrain a predictor, generate crystals or submit calculations.</aside>
  </div>;
}
