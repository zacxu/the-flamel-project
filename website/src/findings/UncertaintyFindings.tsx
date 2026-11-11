import type { KeyboardEvent } from 'react';
import { DataNotice, formatNumber, SavedFigure } from '../components/Shared';
import { useResearchDataset, type CoreData } from '../data/ResearchData';
import type { EvaluationPolicy, ReplaySeed, RiskCoverage, UncertaintyDataset } from '../data/contracts';
import { DATA_RELEASE } from '../data/release';
import { useCsvDownload } from '../replay/useCsvDownload';
import { SEEDS, type RouteState } from '../state/route';
import { ADVANCED_ENDPOINTS, CORE_ENDPOINTS, ENDPOINT_LABELS, roleTotals, selectUncertaintyContext,
  uncertaintyDecilesCsv, uncertaintyMetricsCsv, uncertaintyRiskCsv, uncertaintyRolesCsv } from './uncertainty';
import './uncertainty.css';

export interface UncertaintyFindingsProps {
  data: CoreData;
  state: RouteState;
  update: (patch: Partial<RouteState>) => void;
  onSources: (ids?: readonly string[]) => void;
  onGlossary: () => void;
}
const pct = (value: number, digits = 1) => `${formatNumber(value * 100, digits)}%`;
const energy = (value: number | null, digits = 4) => formatNumber(value, digits);
function Download({ text, filename, children }: { text: string; filename: string; children: string }) {
  const download = useCsvDownload(text);
  return download ? <a className="source-link" href={download.url} download={filename}>{children} ↓</a>
    : <span className="small-text" role="status">Preparing CSV…</span>;
}

/** SVG is a compact display of the ten archived points. Every point has a native
 * keyboard-equivalent slider step and a complete numeric row below. */
function RiskPlot({ rows, selected, onSelect }: { rows: readonly RiskCoverage[]; selected: number; onSelect: (fraction: number) => void }) {
  const ceiling = Math.max(...rows.map((row) => Math.max(row.maeEVPerAtom, row.allRowsMaeEVPerAtom))) * 1.16;
  const x = (fraction: number) => 54 + fraction * 510;
  const y = (value: number) => 210 - value / ceiling * 165;
  const activate = (event: KeyboardEvent<SVGGElement>, fraction: number) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(fraction); }
  };
  return <svg className="uncertainty-risk-plot" viewBox="0 0 610 255" role="group" aria-label="Recorded selective-risk points; each point selects a retained fraction">
    <line x1="54" y1="210" x2="575" y2="210" stroke="currentColor" opacity=".35" />
    <line x1="54" y1="36" x2="54" y2="210" stroke="currentColor" opacity=".35" />
    <text x="54" y="20">MAE (eV/atom)</text>
    <text x="45" y="213" textAnchor="end">0</text>
    <text x="45" y="55" textAnchor="end">{formatNumber(ceiling, 3)}</text>
    <line className="risk-baseline" x1="54" x2="575" y1={y(rows[0].allRowsMaeEVPerAtom)} y2={y(rows[0].allRowsMaeEVPerAtom)} />
    <text x="574" y={y(rows[0].allRowsMaeEVPerAtom) - 8} textAnchor="end">All-row MAE</text>
    <polyline className="risk-line" points={rows.map((row) => `${x(row.requestedRetainedFraction)},${y(row.maeEVPerAtom)}`).join(' ')} />
    {rows.map((row) => <g className="uncertainty-risk-point" key={row.requestedRetainedFraction} role="button" tabIndex={0}
      aria-pressed={selected === row.requestedRetainedFraction}
      aria-label={`Retain requested ${pct(row.requestedRetainedFraction, 0)}: ${row.retainedRows} rows, MAE ${energy(row.maeEVPerAtom)} eV per atom`}
      onClick={() => onSelect(row.requestedRetainedFraction)} onKeyDown={(event) => activate(event, row.requestedRetainedFraction)}>
      <title>{`${pct(row.requestedRetainedFraction, 0)} requested; ${pct(row.actualRetainedFraction, 4)} actual; ${row.retainedRows} rows; MAE ${row.maeEVPerAtom} eV/atom`}</title>
      <circle cx={x(row.requestedRetainedFraction)} cy={y(row.maeEVPerAtom)} r="5" />
    </g>)}
    <text x={x(.1)} y="231" textAnchor="middle">10%</text><text x={x(.5)} y="231" textAnchor="middle">50%</text>
    <text x={x(1)} y="231" textAnchor="middle">100%</text><text x="310" y="251" textAnchor="middle">Requested retained fraction · 10 recorded steps</text>
  </svg>;
}

function LoadedUncertainty({ dataset, data, state, update, onSources, onGlossary }: UncertaintyFindingsProps & { dataset: UncertaintyDataset }) {
  const context = selectUncertaintyContext(dataset, state.seed, state.endpoint, state.retainedFraction);
  const { metrics, retained } = context;
  const isAdvanced = ADVANCED_ENDPOINTS.includes(state.endpoint as typeof ADVANCED_ENDPOINTS[number]);
  const conservative = roleTotals(dataset.roles, 'conservative'), optimistic = roleTotals(dataset.roles, 'optimistic');
  const maxDecileMae = Math.max(...context.deciles.map((row) => row.maeEVPerAtom));
  const filename = `${state.seed}-${state.endpoint}`;
  if (!metrics || !retained || context.risk.length !== 10 || context.deciles.length !== 10) return <DataNotice status="unavailable" />;
  return <div className="uncertainty-findings">
    <p>The saved evaluation separates whole chemical systems within each split. It tests prediction of historical signed hull distance, in eV/atom. Five splits reuse an overlapping population; this explorer keeps each split separate.</p>
    <div className="uncertainty-controls">
      <label className="field">Uncertainty split<select aria-label="Uncertainty split" value={state.seed} onChange={(event) => update({ seed: Number(event.target.value) as ReplaySeed })}>
        {SEEDS.map((seed, index) => <option key={seed} value={seed}>Split {index + 1} · {seed}</option>)}
      </select></label>
      <fieldset><legend>Saved endpoint</legend><div className="uncertainty-endpoints">{CORE_ENDPOINTS.map((endpoint) =>
        <label key={endpoint}><input type="radio" name="uncertainty-endpoint" value={endpoint} checked={state.endpoint === endpoint}
          onChange={() => update({ endpoint })} />{ENDPOINT_LABELS[endpoint]}</label>)}</div></fieldset>
      <details className="uncertainty-advanced" key={isAdvanced ? 'advanced' : 'core'} open={isAdvanced || undefined}>
        <summary>Advanced · other saved policy endpoints</summary>
        <label className="field">Advanced uncertainty endpoint<select aria-label="Advanced uncertainty endpoint" value={isAdvanced ? state.endpoint : ''}
          onChange={(event) => { if (event.target.value) update({ endpoint: event.target.value as EvaluationPolicy }); }}>
          <option value="" disabled>Choose another saved policy</option>{ADVANCED_ENDPOINTS.map((endpoint) => <option key={endpoint} value={endpoint}>{ENDPOINT_LABELS[endpoint]} · 50 queries</option>)}
        </select></label>
      </details>
    </div>
    <p className="uncertainty-context" role="status">Split {SEEDS.indexOf(state.seed) + 1} · {state.seed} · {ENDPOINT_LABELS[state.endpoint]} · {context.queries} completed historical queries · {formatNumber(metrics.rows, 0)} evaluation rows</p>
    <p className="small-text">Initial is the single shared model before acquisition, once per split. Every other endpoint is the saved model after 50 queries. These controls do not change replay progress or fit a model between individual queries.</p>

    <section className="uncertainty-panel" aria-labelledby="reliability-heading"><h3 id="reliability-heading">Does the nominal interval cover the target?</h3>
      <div className="uncertainty-coverage" role="img" aria-label={`Nominal interval coverage ${pct(dataset.summary.nominalIntervalCoverage)}; observed coverage ${pct(metrics.interval90EmpiricalCoverage, 2)} on ${metrics.rows} evaluation rows`}>
        <p><strong className="numeric">{pct(metrics.interval90EmpiricalCoverage, 2)}</strong> observed coverage · <strong>90%</strong> nominal coverage</p>
        <div className="uncertainty-coverage-track"><div className="uncertainty-coverage-fill" style={{ width: pct(metrics.interval90EmpiricalCoverage, 6) }} /><span className="uncertainty-coverage-nominal" style={{ left: '90%' }} /></div>
        <div className="uncertainty-coverage-labels"><span>0%</span><span>Copper marker: nominal 90%</span><span>100%</span></div>
      </div>
      <dl className="uncertainty-stat-grid">
        <div className="uncertainty-stat"><dt>Mean absolute error</dt><dd>{energy(metrics.maeEVPerAtom)}<small>eV/atom · all evaluation rows</small></dd></div>
        <div className="uncertainty-stat"><dt>Root mean squared error</dt><dd>{energy(metrics.rmseEVPerAtom)}<small>eV/atom · all evaluation rows</small></dd></div>
        <div className="uncertainty-stat"><dt>Mean full interval width</dt><dd>{energy(metrics.meanIntervalWidthEVPerAtom)}<small>eV/atom · twice the calibrated radius</small></dd></div>
        <div className="uncertainty-stat"><dt>Disagreement/error association</dt><dd>{formatNumber(metrics.disagreementAbsoluteErrorSpearman, 4)}<small>Spearman ρ · unitless</small></dd></div>
        <div className="uncertainty-stat"><dt>Calibration scale q</dt><dd>{formatNumber(metrics.calibrationScale, 4)}<small>Unitless · saved endpoint calibration</small></dd></div>
        <div className="uncertainty-stat"><dt>Empirical minus nominal</dt><dd>{formatNumber((metrics.interval90EmpiricalCoverage - .9) * 100, 2)}<small>Percentage points · descriptive difference</small></dd></div>
      </dl>
      <p className="uncertainty-method">radius = q × max(ensemble disagreement, 0.01 eV/atom)<br />interval = predicted mean ± radius</p>
      <p>Disagreement measures variation among ensemble predictions. The saved calibration scale expands that disagreement into a prediction interval; disagreement itself is not a coverage probability. Mean interval width and prediction error provide the scale needed to interpret coverage.</p>
      <p className="scope-note">Calibration and evaluation chemistry are disjoint within a split. Chemical-system shift and repeated adaptive reuse prevent a guaranteed 90% coverage claim for arbitrary out-of-distribution chemistry. This diagnostic does not calibrate CHGNet/QE energies or fresh generated crystals.</p>
      <div className="uncertainty-downloads"><Download text={uncertaintyMetricsCsv(dataset, context, DATA_RELEASE.dataReleaseId)} filename={`flamel-uncertainty-${filename}.csv`}>Download displayed reliability CSV</Download>
        <button className="source-link" onClick={() => onSources(['evaluation_metrics', 'uncertainty_summary'])}>Trace reliability sources ↗</button><button className="source-link" onClick={onGlossary}>Explain uncertainty terms</button></div>
    </section>

    <section className="uncertainty-panel" aria-labelledby="risk-heading"><h3 id="risk-heading">What changes when we retain the least-disagreeing rows?</h3>
      <p>Sort the same untouched evaluation rows by ensemble disagreement, ascending, with material ID breaking ties. Each saved step retains ceil(n × requested fraction) rows. No threshold was optimized and no model was retrained.</p>
      <label className="field uncertainty-risk-control">Requested retained fraction: <strong>{pct(state.retainedFraction, 0)}</strong><input id="uncertainty-retained-fraction" type="range" min="10" max="100" step="10" value={state.retainedFraction * 100}
        aria-label="Requested retained fraction" aria-valuetext={`${pct(state.retainedFraction, 0)} requested; ${retained.retainedRows} rows, ${pct(retained.actualRetainedFraction, 4)} actual`}
        onChange={(event) => update({ retainedFraction: Number(event.target.value) / 100 })} /></label>
      <div role="status"><strong>{formatNumber(retained.retainedRows, 0)} / {formatNumber(metrics.rows, 0)} rows</strong> retained · actual fraction <strong>{pct(retained.actualRetainedFraction, 4)}</strong> · subset MAE <strong>{energy(retained.maeEVPerAtom)} eV/atom</strong> · all-row MAE <strong>{energy(retained.allRowsMaeEVPerAtom)} eV/atom</strong> · ratio <strong>{formatNumber(retained.maeRelativeToAllRows, 4)}</strong></div>
      <RiskPlot rows={context.risk} selected={state.retainedFraction} onSelect={(retainedFraction) => update({ retainedFraction })} />
      <div className="uncertainty-table-wrap" tabIndex={0} role="region" aria-label="Selective-risk numeric table, scroll horizontally if needed"><table className="uncertainty-table"><caption>Ten saved retention steps · selected step highlighted · errors in eV/atom</caption><thead><tr><th scope="col">Requested</th><th scope="col">Rows</th><th scope="col">Actual fraction</th><th scope="col">Subset MAE</th><th scope="col">All-row MAE</th><th scope="col">MAE ratio</th><th scope="col">Interval coverage</th></tr></thead>
        <tbody>{context.risk.map((row) => <tr key={row.requestedRetainedFraction} data-selected={row.requestedRetainedFraction === state.retainedFraction}><th scope="row">{pct(row.requestedRetainedFraction, 0)}{row.requestedRetainedFraction === state.retainedFraction ? ' · selected' : ''}</th><td>{formatNumber(row.retainedRows, 0)}</td><td>{pct(row.actualRetainedFraction, 4)}</td><td>{energy(row.maeEVPerAtom)}</td><td>{energy(row.allRowsMaeEVPerAtom)}</td><td>{formatNumber(row.maeRelativeToAllRows, 4)}</td><td>{pct(row.interval90EmpiricalCoverage, 2)}</td></tr>)}</tbody></table></div>
      <p className="scope-note">This is selective risk on a diagnostic subset. A lower error among retained rows does not improve predictions for the complete population, establish a new acquisition policy, or remove error from the discarded rows. Cross-split populations overlap; no aggregate retention claim is implied.</p>
      <div className="uncertainty-downloads"><Download text={uncertaintyRiskCsv(dataset, context, DATA_RELEASE.dataReleaseId)} filename={`flamel-retention-${filename}.csv`}>Download displayed retention CSV</Download><button className="source-link" onClick={() => onSources(['risk_coverage'])}>Trace retention source ↗</button></div>
    </section>

    <details className="uncertainty-details uncertainty-panel"><summary>Explore ten saved uncertainty deciles</summary>
      <p>The selected split/endpoint has ten approximately equal-count bins ordered by disagreement and material ID. Splitting 3,418 rows leaves bins of 342 or 341 rows. Bin 1 has the least disagreement, bin 10 the most. Bar height represents MAE; the table retains width, coverage and disagreement context. These are descriptive bins, not probability bins or a new calibration experiment.</p>
      <div className="uncertainty-deciles" role="img" aria-label={`Mean absolute error by disagreement decile for ${ENDPOINT_LABELS[state.endpoint]}, split ${SEEDS.indexOf(state.seed) + 1}; complete values follow in the table`}>
        {context.deciles.map((row) => <div className="uncertainty-decile" key={row.decile}><span className="uncertainty-decile-bar" style={{ height: `${row.maeEVPerAtom / maxDecileMae * 100}%` }} title={`Decile ${row.decile}: MAE ${row.maeEVPerAtom} eV/atom`} /><span className="uncertainty-decile-label">{row.decile}</span></div>)}
      </div>
      <div className="uncertainty-table-wrap" tabIndex={0} role="region" aria-label="Uncertainty-decile numeric table, scroll horizontally if needed"><table className="uncertainty-table"><caption>Ten saved bins · all energies and disagreement in eV/atom</caption><thead><tr><th scope="col">Decile</th><th scope="col">Rows</th><th scope="col">Mean disagreement</th><th scope="col">Minimum</th><th scope="col">Maximum</th><th scope="col">MAE</th><th scope="col">Coverage</th><th scope="col">Mean full width</th></tr></thead><tbody>{context.deciles.map((row) => <tr key={row.decile}><th scope="row">{row.decile}</th><td>{row.rows}</td><td>{energy(row.meanDisagreementEVPerAtom)}</td><td>{energy(row.minDisagreementEVPerAtom)}</td><td>{energy(row.maxDisagreementEVPerAtom)}</td><td>{energy(row.maeEVPerAtom)}</td><td>{pct(row.interval90EmpiricalCoverage, 2)}</td><td>{energy(row.meanIntervalWidthEVPerAtom)}</td></tr>)}</tbody></table></div>
      <div className="uncertainty-downloads"><Download text={uncertaintyDecilesCsv(dataset, context, DATA_RELEASE.dataReleaseId)} filename={`flamel-deciles-${filename}.csv`}>Download displayed decile CSV</Download><button className="source-link" onClick={() => onSources(['uncertainty_deciles'])}>Trace decile source ↗</button></div>
    </details>

    <details className="uncertainty-details uncertainty-panel"><summary>Inspect Full policy: conservative and optimistic roles</summary>
      <p>Each batch allocated seven conservative and three optimistic selections sequentially. The following counts pool the five recorded split histories, including overlapping material populations; they are event counts, not unique discoveries.</p>
      <div className="uncertainty-role-summary">{[conservative, optimistic].map((row) => <article key={row.role}><h4>{row.role === 'conservative' ? 'Conservative' : 'Optimistic'}</h4><strong>{row.hits} / {row.queries}</strong><p>{row.precision === null ? 'Unavailable' : pct(row.precision, 2)} near-stable precision · event-weighted mean radius {energy(row.meanCalibratedRadiusEVPerAtom)} eV/atom</p></article>)}</div>
      <div className="uncertainty-table-wrap" tabIndex={0} role="region" aria-label="Full-policy role diagnostics table, scroll horizontally if needed"><table className="uncertainty-table"><caption>All ten saved split/role rows · Full policy only · means in eV/atom except unitless diversity</caption><thead><tr><th scope="col">Split / role</th><th scope="col">Queries</th><th scope="col">Near-stable hits</th><th scope="col">Precision</th><th scope="col">Reference-hull hits</th><th scope="col">Mean prediction</th><th scope="col">Mean radius</th><th scope="col">Mean diversity</th></tr></thead><tbody>{dataset.roles.map((row) => <tr key={`${row.seed}-${row.role}`} data-selected={row.seed === state.seed}><th scope="row">{row.seed} · {row.role}</th><td>{row.queries}</td><td>{row.nearStableHits}</td><td>{pct(row.precision, 2)}</td><td>{row.referenceHullHits}</td><td>{energy(row.meanPredictedMeanEVPerAtom)}</td><td>{energy(row.meanCalibratedRadiusEVPerAtom)}</td><td>{formatNumber(row.meanDiversityDistance, 4)}</td></tr>)}</tbody></table></div>
      <p className="scope-note">Roles were not randomized. Different selection criteria, allocation sizes and the evolving selected pool confound this comparison. The 140/175 versus 7/75 split describes this frozen policy and does not estimate a causal advantage of either role.</p>
      <div className="uncertainty-downloads"><Download text={uncertaintyRolesCsv(dataset, DATA_RELEASE.dataReleaseId)} filename="flamel-full-policy-roles.csv">Download all ten displayed role rows</Download><button className="source-link" onClick={() => onSources(['role_diagnostics'])}>Trace role source ↗</button></div>
    </details>
    <details className="uncertainty-details uncertainty-panel"><summary>Open the original saved reliability figure</summary><SavedFigure logicalName="figures/uncertainty.png" className="uncertainty-saved-figure" alt="Four-panel frozen figure: Full minus Quality hit endpoints are negative in all five splits; empirical interval coverage varies by split; selective-risk curves compare Initial, Quality and Full; decile error is plotted against disagreement. Interactive tables above provide the selected context's numeric values." caption="Saved research figure; it does not change with the website controls. Its split means are descriptive because the five populations overlap. Use the numeric tables for the selected split and endpoint." /></details>
    <p className="small-text">Downloads retain full numerical precision. Coverage and retained fractions are fractions in CSV; UI percentages are presentation only. Every CSV identifies units, source IDs, study and data release. {data.methods.target.name} is the historical target.</p>
  </div>;
}

export function UncertaintyFindings(props: UncertaintyFindingsProps) {
  const dataset = useResearchDataset('uncertainty.json');
  return dataset.status === 'ready' && dataset.data
    ? <LoadedUncertainty {...props} dataset={dataset.data} />
    : <DataNotice status={dataset.status} error={dataset.error} retry={dataset.retry} />;
}
