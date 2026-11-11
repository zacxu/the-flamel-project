import { policyColour } from '../presentation/policyColours';
import type { CoreData } from '../data/ResearchData';
import type { RouteState } from '../state/route';
import { DataNotice } from '../components/Shared';
import { useResearchDataset } from '../data/ResearchData';
import { CrystalDisplay } from '../components/CrystalDisplay';
import { CrystalCoordinates } from '../components/CrystalCoordinates';

type View = 'overview' | 'workflow' | 'replay' | 'crystals' | 'findings' | 'evidence';
interface Props {
  data: CoreData;
  navigate: (view: View, patch?: Partial<RouteState>) => void;
  onSources: (ids?: readonly string[]) => void;
  onGlossary: () => void;
}

const number = (value: number, digits = 1) => new Intl.NumberFormat('en', {
  minimumFractionDigits: digits, maximumFractionDigits: digits,
}).format(value);

/** The first screen describes the completed prototype and its measured limits. */
export function Overview({ data, navigate, onSources, onGlossary }: Props) {
  const { summary, methods, structures } = data;
  const quality = summary.policyStatistics.quality;
  const full = summary.policyStatistics.full;
  const knownMgo = structures.coreExamples.find(example => example.id === 'known-mgo-sequence');
  const acceptedMgo = structures.stages.find(stage => (
    stage.candidateId === knownMgo?.candidateId && stage.stage === 'accepted_dft'
  ));
  const heroStage = useResearchDataset(acceptedMgo?.logicalFile ?? null);
  const openCrystals = () => navigate('crystals', acceptedMgo ? {
    candidateId: acceptedMgo.candidateId, stageId: acceptedMgo.stageId,
  } : {});

  return <div className="overview-page">
    <section className="hero-grid" aria-labelledby="overview-title">
      <div className="hero-copy">
        <p className="eyebrow">The Flamel Project · research prototype</p>
        <h1 id="overview-title" className="page-heading" tabIndex={-1}>{methods.headline}</h1>
        <p className="lede">{methods.description}</p>
        <div className="hero-actions">
          <button className="button button-primary" onClick={() => navigate('replay', { mode: 'aggregate', policies: ['quality', 'full'], policy: 'full', budget: 50, batch: 5, revealed: false })}>Explore the experiment <span aria-hidden="true">↗</span></button>
          <button className="button button-secondary" onClick={openCrystals}>Inspect the crystals</button>
        </div>
        <p className="recorded-note"><span className="status-dot" aria-hidden="true" /> Recorded research. Your selections explore saved experiments.</p>
      </div>
      <div className="hero-visual">
        <div className="hero-visual-heading"><span className="eyebrow">A real saved structure</span><span className="status-badge status-accepted">DFT validated: known control</span></div>
        {heroStage.data ? <><CrystalDisplay record={heroStage.data} elementColours={data.theme.elementColours} compact /><p className="small-text hero-cell-caption">MgO · 8 physical atoms · accepted QE geometry</p><CrystalCoordinates record={heroStage.data} /></> : <DataNotice status={heroStage.status} error={heroStage.error} retry={heroStage.retry} />}
        <div className="hero-visual-footer"><p>Known rock-salt recovery. This is a validation control.</p><button className="source-link" onClick={() => onSources(acceptedMgo ? [acceptedMgo.sourceId] : methods.sourceIds)}>Structure source</button></div>
      </div>
    </section>

    <section className="research-intro" aria-labelledby="question-title">
      <div><p className="eyebrow">The research question</p><h2 id="question-title" className="section-heading">Can uncertainty guide the search for useful crystals?</h2></div>
      <div><p>{summary.hypothesis}</p><p><strong>Our contribution is the decision and evaluation pipeline.</strong> Around pretrained CrystalFormer and CHGNet, we built calibrated uncertainty and diversity-based selection, controlled comparisons on held-out chemical systems, strict candidate screening and a traceable record of model and first-principles checks. This makes the discovery hypothesis measurable within a limited compute budget.</p><button className="source-link" onClick={() => navigate('workflow')}>Explore what we built <span aria-hidden="true">→</span></button></div>
    </section>

    <section className="result-section" aria-labelledby="result-title">
      <div className="section-heading-row"><div><p className="eyebrow">What the experiment found</p><h2 id="result-title" className="section-heading">A useful negative result.</h2></div><button className="source-link" onClick={() => onSources(data.curves.sourceIds)}>Trace these results</button></div>
      <p className="result-explanation">Quality ranking retrieved more historical near-stable materials than the Full uncertainty-aware policy in all five paired splits. Full reached a wider range of chemical systems.</p>
      <div className="comparison-panel">
        <div className="comparison-axis"><span>Historical near-stable hits per 50 queries</span><span>Mean ± sample SD · 5 overlapping splits</span></div>
        <div className="comparison-row"><span className="policy-label"><i style={{ backgroundColor: policyColour(data.theme, 'quality') }} aria-hidden="true" />Quality</span><div className="comparison-track" aria-hidden="true"><span style={{ width: `${quality.nearStableHits.mean * 2}%`, backgroundColor: policyColour(data.theme, 'quality') }} /></div><strong>{number(quality.nearStableHits.mean)} <small>± {number(quality.nearStableHits.sampleStd, 2)}</small></strong></div>
        <div className="comparison-row"><span className="policy-label"><i style={{ backgroundColor: policyColour(data.theme, 'full') }} aria-hidden="true" />Full</span><div className="comparison-track" aria-hidden="true"><span style={{ width: `${full.nearStableHits.mean * 2}%`, backgroundColor: policyColour(data.theme, 'full') }} /></div><strong>{number(full.nearStableHits.mean)} <small>± {number(full.nearStableHits.sampleStd, 2)}</small></strong></div>
        <p className="comparison-note">Chemical systems reached: <strong>{number(quality.chemicalSystemCoverage.mean)} Quality</strong> / <strong>{number(full.chemicalSystemCoverage.mean)} Full</strong>. Diversity and yield answer different questions.</p>
      </div>
      <p className="scope-note">Near-stable means the saved signed historical hull target is ≤0.05 eV/atom. These are retrieval results from existing labels. The five splits share an overlapping population.</p>
      <button className="source-link" onClick={onGlossary}>Understand the terms</button>
    </section>

    <section className="metric-strip" aria-label="Fresh experiment and validation scope">
      <div className="metric"><strong>{summary.counts.newFormulaExactValid}/{summary.counts.newFormulaDraws}</strong><span>new-formula draws passed the exact-cell gate</span></div>
      <div className="metric"><strong>{summary.counts.modelSelectedStructures}</strong><span>selected CHGNet calculations converged</span></div>
      <div className="metric"><strong>{summary.counts.acceptedRelaxedQeGeometries}</strong><span>QE relaxed geometries passed the saved finite checks</span></div>
    </section>
    <aside className="outcome-note"><strong>No newly established DFT-confirmed stable novel material.</strong><p>The new-formula candidate path was empty. Known MgO was recovered in a separately planned validation branch; perturbation and competing-reference checks remain incomplete.</p><button className="source-link" onClick={() => navigate('evidence')}>Read the evidence and its limits <span aria-hidden="true">→</span></button></aside>
  </div>;
}
