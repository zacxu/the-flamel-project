import { useState } from 'react';
import type { CandidateEntity, SavedStage, StageMethod } from '../data/contracts';
import { useResearchDataset } from '../data/ResearchData';
import { DataNotice, formatNumber, SavedFigure, StatusBadge } from '../components/Shared';
import { CrystalDisplay } from '../components/CrystalDisplay';
import { CrystalCoordinates } from '../components/CrystalCoordinates';
import { comparableEnergy } from '../crystal/geometry';
import { useStructureDownload } from '../crystal/useStructureDownload';
import type { ViewProps } from './types';
import '../crystal/lab.css';

const methodLabels: Record<StageMethod, string> = {
  crystalformer: 'CrystalFormer', prototype_substitution: 'Prototype substitution',
  catalog_reference: 'Catalog reference', chgnet: 'CHGNet', quantum_espresso: 'Quantum ESPRESSO',
};
const exampleLabels: Record<string, string> = {
  'known-mgo-sequence': 'Known MgO sequence', 'mgo-p1-partner': 'MgO · P1 partner',
  'tio2-nontrivial': 'TiO₂ · nontrivial', 'tio2-p1': 'TiO₂ · P1',
  'camg2o3-prototype': 'CaMg₂O₃ · prototype', 'camg2o3-excluded-twelve-atom': 'CaMg₂O₃ · excluded 12 atoms',
};

function candidateLabel(candidate: CandidateEntity) {
  return `${candidate.formula} · ${methodLabels[candidate.method]}${candidate.arm ? ` · ${candidate.arm === 'p1' ? 'P1' : 'nontrivial'}` : ''}${candidate.referencePhase ? ` · ${candidate.referencePhase}` : ''}${candidate.role === 'source_reference' ? ' · source reference' : ''}${candidate.role === 'excluded_diagnostic' ? ' · excluded' : ''} · ${candidate.actualAtoms} atoms`;
}
function energyLabel(record: SavedStage) {
  return record.energy ? `${formatNumber(record.energy.value, 8)} eV/atom · ${record.energy.engine}` : 'Not evaluated at this saved stage';
}

export function CrystalLab({ data, state, update, onSources, onGlossary }: ViewProps) {
  const candidate = data.structures.candidates.find(item => item.candidateId === state.candidateId);
  const stages = data.structures.stages.filter(item => item.candidateId === candidate?.candidateId);
  const selected = stages.find(item => item.stageId === state.stageId);
  const saved = useResearchDataset(selected?.logicalFile ?? null);
  const generation = useResearchDataset('generation.json');
  const record = saved.data;
  const download = useStructureDownload(record);
  const [compareStageId, setCompareStageId] = useState('');
  const compareIndex = data.structures.stages.find(item => item.stageId === compareStageId);
  const comparison = useResearchDataset(compareIndex?.logicalFile ?? null);
  const peer = comparison.data;
  const energyComparison = record && peer ? comparableEnergy(record, peer) : null;
  const chooseCandidate = (id: string) => {
    const next = data.structures.candidates.find(item => item.candidateId === id);
    if (next) update({ candidateId: next.candidateId, stageId: next.defaultStageId });
  };
  const choosePair = (leftId: string, rightId: string) => {
    const left = data.structures.stages.find(item => item.candidateId === leftId && item.stage === 'model_relaxed');
    const right = data.structures.stages.find(item => item.candidateId === rightId && item.stage === 'model_relaxed');
    if (left && right) { setCompareStageId(right.stageId); update({ candidateId: left.candidateId, stageId: left.stageId }); }
  };

  return <div className="crystal-page">
    <header className="view-header"><p className="eyebrow">Crystal Lab · saved scientific structures</p><h1 className="page-heading" tabIndex={-1}>Inspect the actual cells.</h1><p className="lede">Rotate a real saved geometry, inspect its atoms and follow only the stages that exist. A generated cell, a model result and a finite-checked DFT control each keep their own evidence.</p></header>
    <nav className="crystal-examples" aria-label="Core crystal examples">{data.structures.coreExamples.map(example => <button className="example-button" aria-pressed={state.candidateId === example.candidateId} key={example.id} onClick={() => chooseCandidate(example.candidateId)}>{exampleLabels[example.id] ?? example.id}</button>)}</nav>
    <section className="control-bar crystal-selection" aria-label="Saved crystal selection">
      <label className="field">Candidate<select value={state.candidateId} onChange={event => chooseCandidate(event.target.value)}>{data.structures.candidates.map(item => <option key={item.candidateId} value={item.candidateId}>{candidateLabel(item)}</option>)}</select></label>
      <label className="field">Saved stage<select value={state.stageId} onChange={event => update({ stageId: event.target.value })}>{stages.map(stage => <option key={stage.stageId} value={stage.stageId}>{data.theme.statusLabels[stage.stage]} · {stage.actualAtoms} atoms</option>)}{!stages.some(stage => stage.stage === 'accepted_dft') && <option value="unavailable-dft" disabled>DFT · no accepted saved stage</option>}</select></label>
      <button className="source-link" onClick={onGlossary}>Model versus DFT</button>
    </section>
    <div className="stage-sequence" aria-label="Available recorded stages">{stages.map(stage => <button key={stage.stageId} className={stage.stageId === state.stageId ? 'stage-step is-current' : 'stage-step'} aria-current={stage.stageId === state.stageId ? 'step' : undefined} onClick={() => update({ stageId: stage.stageId })}><span>{data.theme.statusLabels[stage.stage]}</span><small>{stage.actualAtoms} physical atoms</small></button>)}</div>
    <p className="small-text stage-sequence-note">Recorded snapshots, without interpolated trajectories. Separate catalog/source references remain separate entities. {!stages.some(stage => stage.stage === 'accepted_dft') && 'DFT stage unavailable: this entity has no accepted saved DFT geometry.'}</p>
    {!record ? <DataNotice status={saved.status} error={saved.error} retry={saved.retry} /> : <>
      <div className="crystal-workspace" id="crystal-workspace">
        <section className="crystal-image-panel" aria-label="Selected saved structure workspace">
          <div className="panel-label"><span>{record.geometry.formula} · {record.geometry.actualAtoms} physical atoms</span><StatusBadge tone={record.eligibility.excluded ? 'copper' : record.stage === 'accepted_dft' ? 'blue' : 'neutral'}>{record.eligibility.excluded ? 'Excluded by protocol' : data.theme.statusLabels[record.stage]}</StatusBadge></div>
          <CrystalDisplay record={record} elementColours={data.theme.elementColours} />
        </section>
        <section className="crystal-facts" aria-labelledby="crystal-facts-heading"><p className="eyebrow">Scientific identity</p><h2 id="crystal-facts-heading" className="section-heading">This saved stage</h2><dl className="record-facts">
          <div><dt>Origin</dt><dd>{candidate ? methodLabels[candidate.method] : 'Unavailable'}</dd></div>
          <div><dt>Stage method</dt><dd>{methodLabels[record.method]}</dd></div>
          <div><dt>Physical atoms</dt><dd>{record.geometry.actualAtoms}</dd></div>
          <div><dt>Space group</dt><dd>{record.symmetry.spacegroupNumber === null ? 'Unavailable at this saved stage' : record.symmetry.spacegroupNumber}</dd></div>
          <div><dt>Requested group</dt><dd>{record.symmetry.requestedSpacegroupNumber ?? 'Not recorded for this stage'}</dd></div>
          <div><dt>SG tolerance</dt><dd>{record.symmetry.symprecAngstrom === null ? 'Not recorded for this stage' : `${formatNumber(record.symmetry.symprecAngstrom, 3)} Å; angle ${formatNumber(record.symmetry.angleToleranceDegrees, 1)}°`}</dd></div>
          <div><dt>Saved energy</dt><dd>{energyLabel(record)}</dd></div>
          <div><dt>Cell volume</dt><dd>{formatNumber(record.geometry.volumeAngstrom3, 6)} Å³</dd></div>
          <div><dt>Periodic minimum</dt><dd>{record.geometry.minimumPeriodicDistanceAngstrom === null ? 'Unavailable' : `${formatNumber(record.geometry.minimumPeriodicDistanceAngstrom, 6)} Å`}</dd></div>
          <div><dt>Eligibility</dt><dd>{record.eligibility.excluded ? 'Excluded from the frozen experiment gate' : record.eligibility.interpretation}</dd></div>
          <div><dt>Exact-cell gate</dt><dd>{record.eligibility.exactCellEligible === null ? 'Unavailable / not applicable' : record.eligibility.exactCellEligible ? 'Eligible' : 'Not eligible'}</dd></div>
          <div><dt>Workload gate</dt><dd>{record.eligibility.workloadEligible === null ? 'Unavailable / not applicable' : record.eligibility.workloadEligible ? 'Eligible' : 'Not eligible'}</dd></div>
          <div><dt>Frozen QE queue</dt><dd>{record.eligibility.queueSelected ? 'Selected in saved plan' : 'Not selected in saved plan'}; no new dispatch</dd></div>
          <div><dt>DFT validation</dt><dd>{record.dftValidation.status === 'not_performed_at_this_stage' ? 'Not performed at this stage' : record.dftValidation.status === 'accepted_numerical_control' ? 'Finite-checked known control' : 'Finite-checked source reference'}</dd></div>
        </dl><button className="source-link" onClick={() => onSources([...new Set([record.sourceId, ...record.evidence.map(item => item.sourceId), record.symmetry.evidenceSourceId, record.recordedParentSourceId].filter((id): id is string => id !== null))])}>Source and stage evidence ↗</button>
          {download && <a className="button button-secondary structure-download" href={download.url} download={`flamel-${record.stageId}.cif`}>Download selected saved CIF</a>}
        </section>
      </div>
      <p className="scope-note" role={record.eligibility.excluded ? 'status' : undefined}>{record.eligibility.excluded ? `${record.eligibility.reasons.join(' ')} Drawing this geometry does not make it eligible. ` : ''}{record.stage === 'accepted_dft' ? 'This accepted geometry is a known control or source reference. ' : ''}No new stable material is established. Atom sizes are a display aid, not ionic radii. CIF encodes all saved sites explicitly in P1; it retains the recorded space group as provenance and does not infer new symmetry.</p>
      <CrystalCoordinates record={record} />
      <details className="crystal-provenance"><summary>Saved identity, parent and energy settings</summary><dl className="record-facts"><div><dt>Candidate ID</dt><dd><code>{record.candidateId}</code></dd></div><div><dt>Stage ID</dt><dd><code>{record.stageId}</code></dd></div><div><dt>Recorded parent</dt><dd>{record.parentStageId ? <code>{record.parentStageId}</code> : 'No parent stage recorded in this entity'}</dd></div><div><dt>Source ID</dt><dd><code>{record.sourceId}</code></dd></div><div><dt>Source SHA-256</dt><dd><code>{record.sourceSha256}</code></dd></div></dl>{record.energy ? <><p>{record.energy.interpretation}</p><p className="small-text">Settings scope: {record.energy.settingsScope}</p><pre>{JSON.stringify(record.energy.settings, null, 2)}</pre></> : <p>No energy calculation is recorded at this stage.</p>}</details>
    </>}

    <section className="crystal-comparison" aria-labelledby="crystal-comparison-heading"><div className="section-heading-row"><div><p className="eyebrow">Explicit comparison</p><h2 id="crystal-comparison-heading">Two saved cells, one question.</h2></div></div>
      <p>Compare snapshots side by side. Energy differences are available only for the same composition, engine and recorded calculation settings. Each cell keeps its own stage and physical atom count.</p>
      <div className="pair-actions" aria-label="Saved symmetry energy pairs">{generation.data ? generation.data.symmetryPairs.map(pair => <button className="button button-secondary" key={pair.control} onClick={() => choosePair(pair.nontrivialCandidateId, pair.p1CandidateId)}>{pair.control === 'mgo_rocksalt' ? 'Compare MgO model pair' : 'Compare TiO₂ model pair'}</button>) : <DataNotice status={generation.status} error={generation.error} retry={generation.retry} />}</div>
      <p className="small-text">The MgO pair is selected from the supplementary primary-plus-top-up pool; TiO₂ uses the primary first-eight pool. Each contains one selected structure per arm, using the same pretrained architecture with different conditioning. These model comparisons do not establish an energy distribution, causal architecture benefit or DFT stability.</p>
      <label className="field comparison-picker">Comparison saved stage<select value={compareStageId} onChange={event => setCompareStageId(event.target.value)}><option value="">Choose a separate saved stage</option>{data.structures.stages.map(stage => { const entity = data.structures.candidates.find(item => item.candidateId === stage.candidateId); return <option key={stage.stageId} value={stage.stageId}>{entity ? candidateLabel(entity) : stage.candidateId} · {data.theme.statusLabels[stage.stage]}</option>; })}</select></label>
      {compareStageId && !peer && <DataNotice status={comparison.status} error={comparison.error} retry={comparison.retry} />}
      {record && peer && <><div className="saved-comparison-grid">{[record, peer].map((item, index) => <article key={`${index}-${item.stageId}`}><span className="eyebrow">{index === 0 ? 'Selected stage · A' : 'Comparison stage · B'}</span><h3>{item.geometry.formula} · {item.geometry.actualAtoms} atoms</h3><p>{data.theme.statusLabels[item.stage]} · {methodLabels[item.method]}</p><SavedFigure logicalName={item.fallbackFigureLogicalName} alt={`Comparison ${index === 0 ? 'A' : 'B'}: ${item.geometry.actualAtoms}-atom ${item.geometry.formula}, saved stage ${item.stage}.`} caption="Separate saved snapshot; no morph or relaxation animation." /><p className="numeric comparison-energy">{energyLabel(item)}</p><p>{item.eligibility.excluded ? 'Excluded by protocol.' : item.eligibility.interpretation}</p><small className="saved-stage-id">{item.stageId}</small></article>)}</div>
        <div className="energy-comparison-result" role="status">{energyComparison?.compatible ? <><strong>B − A: {formatNumber(energyComparison.deltaEVPerAtom! * 1000, 6)} meV/atom</strong><p>{energyComparison.reason} Model/total-energy differences are not formation energies or proof of thermodynamic stability.</p></> : <><strong>Energy difference unavailable.</strong><p>{energyComparison?.reason}</p></>}</div>
      </>}
    </section>

    <section className="crystal-catalog" aria-labelledby="crystal-catalog-heading"><div className="section-heading-row"><div><p className="eyebrow">The complete saved registry</p><h2 id="crystal-catalog-heading">Every result stays visible.</h2></div></div><p>{data.structures.counts.modelFinals} model-result records, one excluded diagnostic and two distinct accepted source-reference entities. All {data.structures.counts.stages} saved stages can be inspected. A converged prototype does not increase the transformer’s 0/48 new-formula success count.</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Saved structure catalog, scroll horizontally"><table><caption>{data.structures.counts.entities} entities, including all eleven model-result records. Eligibility is separate from DFT validation.</caption><thead><tr><th scope="col">Formula / identity</th><th scope="col">Origin / role</th><th scope="col">Atoms</th><th scope="col">Model result</th><th scope="col">Eligibility</th><th scope="col">Saved stages</th><th scope="col">Inspect</th></tr></thead><tbody>{data.structures.candidates.map(item => { const entityStages = data.structures.stages.filter(stage => stage.candidateId === item.candidateId); return <tr key={item.candidateId} className={state.candidateId === item.candidateId ? 'selected-catalog-row' : ''}><th scope="row">{item.formula}<small>{item.arm ? item.arm === 'p1' ? 'P1' : 'Nontrivial symmetry' : item.referencePhase ?? item.role.replaceAll('_', ' ')}</small></th><td>{methodLabels[item.method]}<small>{item.role.replaceAll('_', ' ')}</small></td><td className="numeric">{item.actualAtoms}</td><td>{entityStages.some(stage => stage.stage === 'model_relaxed') ? 'Saved CHGNet final' : 'Not available'}</td><td>{item.role === 'excluded_diagnostic' ? 'Excluded by frozen gate' : 'See recorded stage scope'}</td><td>{entityStages.map(stage => data.theme.statusLabels[stage.stage]).join(' → ')}</td><td><button className="text-button" aria-label={`Inspect ${candidateLabel(item)}`} onClick={() => chooseCandidate(item.candidateId)}>Inspect ↗</button></td></tr>; })}</tbody></table></div>
    </section>
  </div>;
}
