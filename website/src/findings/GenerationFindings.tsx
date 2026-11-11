import { useEffect, useState, type ReactNode } from 'react';
import { useTourScene } from '../tour/TourContext';
import type { CoreData } from '../data/ResearchData';
import { useResearchDataset } from '../data/ResearchData';
import type { Control, GenerationCohort, GenerationDataset, GenerationDraw, RelaxedStructureRecord } from '../data/contracts';
import { DATA_RELEASE } from '../data/release';
import type { RouteState } from '../state/route';
import { DataNotice, SavedFigure, formatNumber } from '../components/Shared';
import { useCsvDownload } from '../replay/useCsvDownload';
import { armLabel, compositionDraws, compositionNoveltyCsv, controlCohorts, controlLabel, countsText, eligibilityReasons, fraction, generationCohortCsv, generationDrawCsv, modelEnergyCsv, prototypeCsv, scopeLabel, selectedEnergyRows } from './generation';
import './generation.css';

interface Props {
  readonly data: CoreData; readonly state: RouteState;
  readonly update: (patch: Partial<RouteState>) => void;
  readonly onSources: (ids?: readonly string[]) => void; readonly onGlossary: () => void;
}
const percent = (value: number | null) => value === null ? 'Unavailable' : `${formatNumber(value * 100, 1)}%`;
const yesNo = (value: boolean) => value ? 'Yes' : 'No';

function CsvLink({ text, name, children }: { readonly text: string; readonly name: string; readonly children: ReactNode }) {
  const asset = useCsvDownload(text);
  return asset ? <a className="source-link" href={asset.url} download={`flamel-${name}.csv`}>{children}</a> : <span className="small-text" role="status">Preparing current table CSV…</span>;
}

function YieldPlot({ cohorts }: { readonly cohorts: readonly GenerationCohort[] }) {
  return <figure className="generation-yield-plot" aria-label="Recorded valid and unique yield fractions">
    <figcaption>Recorded fractions of emitted draws. Blue bars: exact-cell valid; copper bars: exact-cell valid and unique. Raw numerators and denominators remain visible.</figcaption>
    {cohorts.flatMap(row => [
      { key: `${row.arm}-valid`, label: `${armLabel(row.arm)} · valid`, count: row.exactValid, kind: 'valid' },
      { key: `${row.arm}-unique`, label: `${armLabel(row.arm)} · unique`, count: row.exactValidUnique, kind: 'unique' },
    ].map(bar => <div className={`generation-yield-row ${bar.kind}`} key={bar.key}><span>{bar.label}</span><span className="generation-yield-track" aria-hidden="true"><span style={{ width: `${(fraction(bar.count, row.draws) ?? 0) * 100}%` }} /></span><strong>{bar.count}/{row.draws} · {percent(fraction(bar.count, row.draws))}</strong></div>))}
  </figure>;
}

export function GenerationFindings(props: Props) {
  const loaded = useResearchDataset('generation.json');
  return <div className="generation-findings">
    {!loaded.data ? <><p>The primary first-eight comparisons, separate MgO supplement, all six proposals and four prototypes are recorded findings. No generated new-formula structure passed the exact-cell gate.</p><DataNotice status={loaded.status} error={loaded.error} retry={loaded.retry} /></> : <GenerationResults {...props} generation={loaded.data} />}
  </div>;
}

function GenerationResults({ data, state, update, onSources, onGlossary, generation }: Props & { readonly generation: GenerationDataset }) {
  const [primaryControl, setPrimaryControl] = useState<Control>('mgo_rocksalt');
  const [energyControl, setEnergyControl] = useState<Control>('mgo_rocksalt');
  const [formula, setFormula] = useState('CaMg2O3');
  const tour = useTourScene();
  useEffect(() => {
    if (tour.scene?.id === 'symmetry-mgo') setPrimaryControl('mgo_rocksalt');
    if (tour.scene?.id === 'symmetry-tio2') setPrimaryControl('tio2_rutile');
    if (tour.scene?.id === 'symmetry-energy') setEnergyControl('mgo_rocksalt');
  }, [tour.scene?.id]);
  const control: Control = state.scope === 'supplementary' ? 'mgo_rocksalt' : primaryControl;
  const cohorts = controlCohorts(generation, state.scope, control);
  const draws = compositionDraws(generation, formula);
  const pair = generation.symmetryPairs.find(row => row.control === energyControl);
  const pairRows = selectedEnergyRows(generation, energyControl);
  const references = generation.relaxedStructures.filter(row => row.candidateId === 'reference_anatase' || row.candidateId === 'reference_rutile');
  const release = DATA_RELEASE.dataReleaseId;
  const csvInfo = <p className="small-text">CSV files contain the current displayed table with full numeric precision, study/release IDs and public source IDs. Energy is eV per physical atom, distances are Å, and fractions use 0–1. Empty fields mean unavailable or not applicable; recorded zeros remain zero.</p>;
  const openCrystal = (candidateId: string) => {
    const candidate = data.structures.candidates.find(row => row.candidateId === candidateId);
    if (!candidate) return;
    const model = data.structures.stages.find(row => row.candidateId === candidateId && row.stage === 'model_relaxed');
    update({ view: 'crystals', candidateId, stageId: model?.stageId ?? candidate.defaultStageId });
  };
  const structureLink = (candidateId: string) => data.structures.candidates.some(row => row.candidateId === candidateId)
    ? <button className="source-link" onClick={() => openCrystal(candidateId)}>View saved structure</button>
    : <span className="small-text">No public saved geometry</span>;
  const energyTable = (records: readonly RelaxedStructureRecord[], caption: string) => <div className="table-scroll" tabIndex={0} role="region" aria-label={caption}><table><caption>{caption}</caption><thead><tr><th scope="col">Record / method</th><th scope="col">Formula / atoms</th><th scope="col">CHGNet energy (eV/atom)</th><th scope="col">Optimizer / final SG</th><th scope="col">Pinned geometry matches</th><th scope="col">Saved geometry</th></tr></thead><tbody>{records.map(row => <tr key={row.candidateId}><th scope="row">{row.role === 'symmetry' ? armLabel(row.arm) : row.role === 'prototype' ? 'Prototype substitution' : row.candidateId === 'reference_anatase' ? 'Anatase reference' : row.candidateId === 'reference_rutile' ? 'Rutile reference' : 'Rocksalt reference'}<span className="record-id">{row.candidateId}</span></th><td>{row.finalFormula}<br />{row.atoms} physical atoms</td><td className="numeric">{formatNumber(row.chgnetEnergyEVPerAtom, 8)}</td><td>{row.converged ? 'Converged' : 'Not converged'} · {formatNumber(row.optimizerSteps, 0)} steps<br />SG {formatNumber(row.finalSpacegroup, 0)} at {row.spacegroupSymprecAngstrom} Å<br /><small>Filter force: {formatNumber(row.filterFmaxEVPerAngstrom, 6)} eV/Å</small></td><td>{row.matchesPinnedMpSameCompositionGeometryIds.length ? row.matchesPinnedMpSameCompositionGeometryIds.join(', ') : 'No match in tested subset'}<span className="generation-matches">{row.sameCompositionMpGeometriesTested} same-composition geometries tested</span></td><td>{structureLink(row.candidateId)}</td></tr>)}</tbody></table></div>;
  const drawTable = (records: readonly GenerationDraw[], caption: string) => <div className="table-scroll" tabIndex={0} role="region" aria-label={caption}><table><caption>{caption}</caption><thead><tr><th scope="col">Draw / requested formula</th><th scope="col">Actual / requested atoms</th><th scope="col">Actual element counts</th><th scope="col">Exact-cell eligibility</th><th scope="col">Geometry / diagnostic</th><th scope="col">SG requested → measured</th><th scope="col">Saved geometry</th></tr></thead><tbody>{records.map(row => <tr key={row.candidateId}><th scope="row">{row.formula}<span className="record-id">{row.candidateId}</span></th><td>{row.atoms} / {row.requestedAtoms}</td><td className="numeric">{countsText(row.actualCounts)}</td><td>{eligibilityReasons(row).map(reason => <span className="eligibility-reason" key={reason}>{reason}</span>)}<small>{row.duplicateOf ? `Duplicate of ${row.duplicateOf}` : 'No recorded duplicate'}</small></td><td>{row.geometryValid ? 'Geometry-valid' : 'Geometry-invalid'}<br /><small>Minimum distance {formatNumber(row.minimumPeriodicDistanceAngstrom, 6)} Å</small><br />{row.largerCellDiagnosticExcluded ? 'Larger-cell diagnostic only; excluded' : row.differentCellCountDiagnosticExcluded ? 'Different-cell diagnostic only; excluded' : 'Not a ratio-valid within-cap diagnostic'}</td><td>{formatNumber(row.requestedSpacegroup, 0)} → {formatNumber(row.measuredSpacegroup, 0)}</td><td>{structureLink(row.candidateId)}</td></tr>)}</tbody></table></div>;
  return <>
    <section aria-labelledby="symmetry-results-heading">
      <p className="eyebrow">Same trained architecture · different sampling conditioning</p><h3 id="symmetry-results-heading">Exact-cell validity and unique yield</h3>
      <p>The nontrivial-space-group and P1 arms use the same fixed CrystalFormer architecture and differ in sampling conditioning. The primary comparison uses the first eight draws in each arm. More valid draws do not automatically mean more unique structures, and this experiment does not isolate a symmetry-free trained architecture.</p>
      <div className="generation-tabs" role="tablist" aria-label="Generation cohort scope" onKeyDown={event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); const next = event.key === 'Home' ? 'primary' : event.key === 'End' ? 'supplementary' : state.scope === 'primary' ? 'supplementary' : 'primary'; update({ scope: next }); event.currentTarget.querySelector<HTMLButtonElement>(`[data-scope="${next}"]`)?.focus(); } }}>
        <button role="tab" type="button" data-scope="primary" aria-selected={state.scope === 'primary'} aria-controls="generation-scope-panel" tabIndex={state.scope === 'primary' ? 0 : -1} id="generation-primary-tab" onClick={() => update({ scope: 'primary' })}>Primary · first eight</button>
        <button role="tab" type="button" data-scope="supplementary" aria-selected={state.scope === 'supplementary'} aria-controls="generation-scope-panel" tabIndex={state.scope === 'supplementary' ? 0 : -1} id="generation-supplementary-tab" onClick={() => update({ scope: 'supplementary' })}>Supplementary · MgO only</button>
      </div>
      <div role="tabpanel" id="generation-scope-panel" aria-labelledby={state.scope === 'primary' ? 'generation-primary-tab' : 'generation-supplementary-tab'}>
        <div className="generation-controls"><label className="field">Control composition<select aria-label="Symmetry control composition" value={control} disabled={state.scope === 'supplementary'} onChange={event => setPrimaryControl(event.target.value as Control)}><option value="mgo_rocksalt">MgO · Mg₄O₄ requested cell</option><option value="tio2_rutile">TiO₂ · Ti₂O₄ requested cell</option></select></label><span className="status-badge">{scopeLabel(state.scope)}</span></div>
        {state.scope === 'supplementary' && <p className="scope-note">These are four additional MgO draws per arm, shown on their own. They do not change either primary first-eight denominator. No TiO₂ supplementary cohort was recorded.</p>}
        <YieldPlot cohorts={cohorts} />
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Selected symmetry cohort counts"><table><caption>{controlLabel(control)} · {scopeLabel(state.scope)}. Unique yield uses all emitted draws as its denominator.</caption><thead><tr><th scope="col">Conditioning arm</th><th scope="col">Emitted draws</th><th scope="col">Exact-cell valid</th><th scope="col">Valid fraction</th><th scope="col">Valid and unique</th><th scope="col">Unique yield</th><th scope="col">Valid requested SG</th><th scope="col">Larger-cell diagnostics excluded</th></tr></thead><tbody>{cohorts.map(row => <tr key={row.arm}><th scope="row">{armLabel(row.arm)}</th><td>{row.draws}</td><td>{row.exactValid}/{row.draws}</td><td>{percent(fraction(row.exactValid, row.draws))}</td><td>{row.exactValidUnique}/{row.draws}</td><td>{percent(fraction(row.exactValidUnique, row.draws))}</td><td>{row.validRequestedSpacegroup}</td><td>{row.excludedLargerCellDiagnostics}</td></tr>)}</tbody></table></div>
        <div className="generation-actions"><CsvLink text={generationCohortCsv(generation, state.scope, control, release)} name={`symmetry-${state.scope}-${control}`}>Download displayed symmetry table CSV</CsvLink><button className="source-link" onClick={() => onSources(['generation_cohorts', 'generation_draws'])}>Trace symmetry counts</button></div>
      </div>
      <details><summary>View the saved primary-generation figure</summary><SavedFigure logicalName="figures/generation.png" alt="Saved primary-generation plot with first-eight validity and unique yield for MgO and TiO2 conditioning arms" caption="Original frozen primary figure. The interactive table above keeps supplementary draws separate." /></details>
    </section>

    <section aria-labelledby="symmetry-energy-heading"><p className="eyebrow">Selected model comparisons · one structure per arm</p><h3 id="symmetry-energy-heading">Within-composition CHGNet energies</h3>
      <p>These two saved selected pairs have different sampling pools. MgO uses the supplementary primary-plus-top-up selection pool; TiO₂ uses the primary first-eight pool. Each contains one unique selected structure per arm, not an energy distribution.</p>
      <div className="generation-controls"><label className="field">Selected model-energy pair<select aria-label="Selected model-energy pair" value={energyControl} onChange={event => setEnergyControl(event.target.value as Control)}><option value="mgo_rocksalt">MgO · supplemented selection pool</option><option value="tio2_rutile">TiO₂ · primary selection pool</option></select></label></div>
      {pair && <div className="generation-pair-metric"><strong>P1 − nontrivial = {formatNumber(pair.p1MinusNontrivialChgnetEVPerAtom, 8)} eV/atom</strong><p>{formatNumber(pair.p1MinusNontrivialChgnetEVPerAtom * 1000, 3)} meV/atom · {pair.quotaPerArm} selected structure per arm · {energyControl === 'mgo_rocksalt' ? 'supplemented MgO selection pool' : 'primary TiO₂ first-eight selection pool'}. The relaxed pair {pair.relaxedPairStructureMatch ? 'matched' : 'did not match'} each other under the saved structure comparison.</p></div>}
      {energyTable(pairRows, `${controlLabel(energyControl)} selected pair · CHGNet only · one per arm`)}
      <div className="generation-actions"><CsvLink text={modelEnergyCsv(generation, pairRows, release, `${energyControl}; ${pair?.scope ?? 'Unavailable'}; selected one structure per arm`)} name={`selected-energy-pair-${energyControl}`}>Download displayed energy-pair table CSV</CsvLink><button className="source-link" onClick={() => onSources(['symmetry_pairs', 'relaxed_structures'])}>Trace selected energy pair</button></div>
      <p className="scope-note">CHGNet predictions are model energies per physical atom. Absolute energies across compositions do not define formation energies, hull stability or a DFT ranking. The higher P1 energy in these selected pairs does not establish a general energy advantage or architecture causality.</p>
      <h4>Anatase and rutile: a separate within-TiO₂ model ranking</h4><p>The saved anatase-minus-rutile CHGNet difference is {formatNumber(generation.summary.anataseMinusRutileChgnetEVPerAtom, 8)} eV/atom ({formatNumber(generation.summary.anataseMinusRutileChgnetEVPerAtom * 1000, 3)} meV/atom). CHGNet ranks this anatase reference below this rutile reference. This is not a DFT ground-state or thermodynamic-stability claim.</p>
      {energyTable(references, 'Anatase and rutile saved TiO₂ references · CHGNet ranking only')}
      <div className="generation-actions"><CsvLink text={modelEnergyCsv(generation, references, release, 'Saved anatase and rutile references; within-TiO2 CHGNet comparison only')} name="tio2-model-references">Download displayed TiO₂ reference table CSV</CsvLink></div>
      <details><summary>View the saved within-composition energy figure</summary><SavedFigure logicalName="figures/model-energies.png" alt="Saved within-composition CHGNet energy comparisons for the selected MgO and TiO2 pairs and TiO2 references" caption="The saved figure reports model predictions with their selection scope; it does not establish DFT stability." /></details>
    </section>

    <section aria-labelledby="composition-results-heading"><p className="eyebrow">Six proposed compositions · eight attempts each</p><h3 id="composition-results-heading">The exact-cell shortlist remained empty: 0/48</h3>
      <p>All 48 new-formula transformer draws failed the frozen exact-cell eligibility gate. This is a cell-representation and validation-workload constraint. A correct reduced ratio in a larger cell remains excluded; rejection does not establish physical instability.</p>
      <div className="generation-controls"><label className="field">Composition proposal<select aria-label="Composition proposal" value={formula} onChange={event => setFormula(event.target.value)}>{generation.compositionNovelty.map(row => <option key={row.formula}>{row.formula}</option>)}</select></label><span className="status-badge">{draws.length} attempts · {draws.filter(row => row.valid).length} exact-cell eligible</span></div>
      <p>{draws.filter(row => !row.exactCountsMatch).length}/{draws.length} did not reproduce requested element counts; {draws.filter(row => !row.geometryValid).length}/{draws.length} also failed recorded geometry validity. Reasons can overlap. {draws.filter(row => row.largerCellDiagnosticExcluded).length} larger-cell diagnostic(s) for this formula remain excluded.</p>
      {drawTable(draws, `${formula} · all eight emitted attempts and exact eligibility flags`)}
      <div className="generation-actions"><CsvLink text={generationDrawCsv(generation, draws, release, `${formula}; eight new-formula attempts`)} name={`composition-attempts-${formula}`}>Download displayed composition-attempt table CSV</CsvLink><button className="source-link" onClick={() => onSources(['generation_draws', 'generation_cohorts'])}>Trace composition attempts</button></div>
      <details><summary>Inspect all 12 excluded larger-cell new-formula diagnostics</summary><p>These twelve records are a subset of the 48 attempts, not twelve extra draws. They have the requested reduced ratio and pass the saved within-cap geometry diagnostic, while their emitted cell differs from the exact requested cell. Control diagnostic rows are separate in the original 88-draw table.</p>{drawTable(generation.excluded, 'All twelve new-formula larger-cell diagnostics · excluded from exact-cell yield')}<div className="generation-actions"><CsvLink text={generationDrawCsv(generation, generation.excluded, release, 'All twelve new-formula larger-cell diagnostics')} name="excluded-new-formula-diagnostics">Download displayed 12-diagnostic table CSV</CsvLink><button className="source-link" onClick={() => onSources(['excluded_diagnostics', 'generation_draws'])}>Trace all exclusions</button></div></details>
    </section>

    <section aria-labelledby="prototype-results-heading"><p className="eyebrow">Separate method baseline</p><h3 id="prototype-results-heading">Four prepared prototype substitutions</h3><p>These prepared prototypes use reference-derived substitution. They are a separate method, rather than successful CrystalFormer outputs or replacements for the empty 0/48 shortlist. All four converged under the saved CHGNet criterion; none was submitted for fresh candidate DFT and none established a stable material.</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="All four prepared prototypes"><table><caption>Four prototype baselines · source parent, saved model outcome and fresh-DFT status</caption><thead><tr><th scope="col">Target / parent</th><th scope="col">Atoms</th><th scope="col">Initial geometry</th><th scope="col">CHGNet converged</th><th scope="col">Final SG</th><th scope="col">CHGNet energy (eV/atom)</th><th scope="col">Fresh candidate DFT</th><th scope="col">Saved geometry</th></tr></thead><tbody>{generation.prototypes.map(row => <tr key={row.candidateId}><th scope="row">{row.targetFormula}<span className="generation-matches">Parent: {row.parentMaterialId}</span></th><td>{row.atoms}</td><td>{row.initialGeometryValid ? 'Valid' : 'Invalid'}</td><td>{yesNo(row.chgnetConverged)}</td><td>{row.finalSpacegroup}<br /><small>symprec 0.01 Å</small></td><td className="numeric">{formatNumber(row.chgnetEnergyEVPerAtom, 8)}</td><td>{row.freshDftSubmitted ? 'Submitted' : 'Not submitted'}</td><td>{structureLink(row.candidateId)}</td></tr>)}</tbody></table></div>
      <div className="generation-actions"><CsvLink text={prototypeCsv(generation, release)} name="prototype-baselines">Download displayed prototype table CSV</CsvLink><button className="source-link" onClick={() => onSources(['prototype_baselines', 'relaxed_structures'])}>Trace prototype baselines</button></div>
    </section>

    <section aria-labelledby="catalog-scope-heading"><p className="eyebrow">Historical snapshots · limited geometry coverage</p><h3 id="catalog-scope-heading">Catalog absence has a specific scope</h3><p>All six proposed compositions are absent from these two pinned historical catalogs. This does not establish current or global composition novelty, absence from CrystalFormer pretraining, or DFT-confirmed stability.</p>
      <dl className="record-facts"><div><dt>MP snapshot</dt><dd>{generation.catalogScope.mpSnapshot}<br />{formatNumber(generation.catalogScope.populations.mp.records, 0)} records · {formatNumber(generation.catalogScope.populations.mp.uniqueCompositions, 0)} unique compositions</dd></div><div><dt>WBM snapshot</dt><dd>{generation.catalogScope.wbmSnapshot}<br />{formatNumber(generation.catalogScope.populations.wbm.records, 0)} records · {formatNumber(generation.catalogScope.populations.wbm.uniqueCompositions, 0)} unique compositions</dd></div></dl>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="All six historical composition matches"><table><caption>Snapshot-specific composition search · no global novelty or pretraining-OOD inference</caption><thead><tr><th scope="col">Formula</th><th scope="col">MP composition records</th><th scope="col">WBM composition records</th><th scope="col">Absent in both snapshots</th><th scope="col">Global novelty established</th><th scope="col">Pretraining OOD established</th><th scope="col">DFT stability confirmed</th></tr></thead><tbody>{generation.compositionNovelty.map(row => <tr key={row.formula}><th scope="row">{row.formula}</th><td>{row.mpMatchingCompositionRecords}</td><td>{row.wbmMatchingCompositionRecords}</td><td>{yesNo(row.absentFromBothPinnedSnapshots)}</td><td>{yesNo(row.globalCompositionNoveltyEstablished)}</td><td>{yesNo(row.generatorPretrainingOodEstablished)}</td><td>{yesNo(row.dftConfirmedStability)}</td></tr>)}</tbody></table></div>
      <div className="generation-actions"><CsvLink text={compositionNoveltyCsv(generation, release)} name="historical-composition-absence">Download displayed catalog-match table CSV</CsvLink><button className="source-link" onClick={() => onSources(['composition_novelty', 'structures_summary'])}>Trace catalog scope</button><button className="source-link" onClick={onGlossary}>Open novelty and OOD glossary</button></div>
      <p className="scope-note">Saved geometry matching covered 15/23 MgO and 34/44 TiO₂ MP entries, using original-source cells with at most 30 sites. Larger-source-cell geometries were not tested. A missing match in this partial subset does not establish global structural novelty. The conditioned MgO result matches mp-1265; the conditioned TiO₂ result matches mp-1041565 and mp-2657. The two P1 outputs were unmatched only within the tested subsets.</p>
      <details><summary>Inspect all 11 selected CHGNet result records</summary><p>Four symmetry selections, four prototype substitutions and three same-composition references remain distinct. The table follows recorded method order, not an energy ranking across formulas. Every energy is a CHGNet prediction per actual physical atom.</p>{energyTable(generation.relaxedStructures, 'All eleven selected model results · distinct methods and compositions')}<div className="generation-actions"><CsvLink text={modelEnergyCsv(generation, generation.relaxedStructures, release, 'All eleven selected model records in source method order; compare energies only within composition')} name="all-selected-model-results">Download displayed 11-result table CSV</CsvLink><button className="source-link" onClick={() => onSources(['relaxed_structures'])}>Trace all model records</button></div></details>
      {csvInfo}
    </section>
  </>;
}
