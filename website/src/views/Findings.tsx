import { GenerationFindings } from '../findings/GenerationFindings';
import { UncertaintyFindings } from '../findings/UncertaintyFindings';
import type { ViewProps } from './types';
import '../findings/findings.css';

/** Interactive saved diagnostics remain distinct from claims and validation. */
export function Findings(props: ViewProps) {
  const { data, update, onSources, onGlossary } = props;
  const goToSection = (id: string) => {
    const heading = document.getElementById(id);
    heading?.focus({ preventScroll: true });
    heading?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
  };
  return <div className="findings-page">
    <header className="view-header"><p className="eyebrow">What the frozen evidence supports</p><h1 className="page-heading" tabIndex={-1}>Results, with their limits.</h1><p className="lede">Explore the saved symmetry, composition and uncertainty experiments. The prototype’s findings include a negative acquisition result and an empty new-formula shortlist.</p><button className="source-link" onClick={onGlossary}>Open the research glossary ↗</button></header>
    <nav className="findings-jump" aria-label="Finding sections"><button onClick={() => goToSection('generation-findings-heading')}>Symmetry & compositions</button><button onClick={() => goToSection('uncertainty-findings-heading')}>Uncertainty & selective risk</button><button onClick={() => goToSection('conclusions-findings-heading')}>Claims & limits</button></nav>
    <section id="generation-findings" className="findings-explorer" aria-labelledby="generation-findings-heading"><p className="eyebrow">01 · The generation experiment</p><h2 id="generation-findings-heading" tabIndex={-1}>Symmetry and composition</h2><GenerationFindings {...props} /></section>
    <section id="uncertainty-findings" className="findings-explorer" aria-labelledby="uncertainty-findings-heading"><p className="eyebrow">02 · Saved predictor diagnostics</p><h2 id="uncertainty-findings-heading" tabIndex={-1}>Uncertainty under examination</h2><UncertaintyFindings {...props} /></section>
    <section className="findings-explorer" aria-labelledby="conclusions-findings-heading"><p className="eyebrow">03 · Claims with a defined scope</p><h2 id="conclusions-findings-heading" tabIndex={-1}>What follows from the evidence?</h2><div className="finding-conclusions">{data.claims.claims.map(claim => <article className="finding" key={claim.id}><h3>{claim.title}</h3><p>{claim.text}</p><button className="source-link" onClick={() => onSources(claim.sourceIds)}>Trace this finding ↗</button></article>)}</div><div className="findings-crosslinks"><button className="button button-secondary" onClick={() => update({ view: 'replay' })}>Compare historical acquisition</button><button className="button button-primary" onClick={() => update({ view: 'evidence' })}>Inspect the validation ledger</button></div></section>
    <aside className="scope-note">Recorded work only. These controls do not refit predictors, regenerate crystals or dispatch calculations. No comparison establishes a symmetry-free architecture benefit, calibrated uncertainty for arbitrary generated chemistry or a newly discovered stable material.</aside>
  </div>;
}
