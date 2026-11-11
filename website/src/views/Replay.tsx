import { policyColour } from '../presentation/policyColours';
import { Component, lazy, Suspense, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { BatchBudget, Policy, ReplaySeed, Round } from '../data/contracts';
import { DATA_RELEASE } from '../data/release';
import { useResearchDataset } from '../data/ResearchData';
import { BUDGETS, POLICIES, SEEDS } from '../state/route';
import type { RouteState } from '../state/route';
import { batchFor, buildReplaySeries, comparisonCsv } from '../replay/model';
import type { ReplayMetric, ReplayChartPoint } from '../replay/model';
import { useCsvDownload } from '../replay/useCsvDownload';
import { useReplayPlayback } from '../replay/useReplayPlayback';
import { DataNotice, formatNumber, StatusBadge } from '../components/Shared';
import { QueryDrawer } from '../components/QueryDrawer';
import type { ViewProps } from './types';
import '../replay/replay.css';
import { useTourScene } from '../tour/TourContext';

const ReplayChart = lazy(() => import('../components/ReplayChart'));
const METRICS: readonly ReplayMetric[] = ['hits', 'precision', 'systems'];
const LABELS: Readonly<Record<ReplayMetric, string>> = { hits: 'Near-stable hits', precision: 'Precision', systems: 'Chemical systems' };
const display = (point: ReplayChartPoint | undefined, metric: ReplayMetric, aggregate: boolean) => point?.mean === null || !point
  ? 'Unavailable' : `${formatNumber(point.mean * (metric === 'precision' ? 100 : 1), metric === 'precision' ? 1 : aggregate ? 1 : 0)}${metric === 'precision' ? '%' : ''}`;

class ChartBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <div className="data-notice" role="alert"><h2>Chart unavailable.</h2><p>The recorded data table and CSV below remain usable.</p><button className="button button-secondary" onClick={() => window.location.reload()}>Reload to retry chart</button></div> : this.props.children; }
}

export function Replay({ data, state, update, onSources, onGlossary, playing, setPlaying, registerCancellation, reset }: ViewProps) {
  const [metric, setMetric] = useState<ReplayMetric>('hits');
  const [queryOpen, setQueryOpen] = useState(false);
  const [shareStatus, setShareStatus] = useState('');
  const tour = useTourScene();
  useEffect(() => {
    if (tour.scene?.id.startsWith('replay-')) setMetric(tour.scene.id === 'replay-full' || tour.scene.id === 'replay-aggregate' ? 'systems' : 'hits');
  }, [tour.scene?.id]);
  const aggregate = state.mode === 'aggregate';
  const history = useResearchDataset(aggregate ? null : `replay/seed-${state.seed}.json` as const);
  const batch = history.data ? batchFor(history.data, state.policy, state.batch) : null;
  const historyReady = !aggregate && history.status === 'ready' && history.data?.seed === state.seed && batch !== null;
  const playback = useReplayPlayback({ state, playing, setPlaying, update, registerCancellation, historyReady, reset });
  useEffect(() => { setQueryOpen(false); setShareStatus(''); }, [state.mode, state.seed, state.policy]);
  const families = useMemo(() => ({ hits: buildReplaySeries(data.curves, data.theme, state, 'hits'),
    precision: buildReplaySeries(data.curves, data.theme, state, 'precision'), systems: buildReplaySeries(data.curves, data.theme, state, 'systems'),
  }), [data.curves, data.theme, state.mode, state.seed, state.policies]);
  const series = families[metric].map((item) => ({ ...item, points: item.points.filter((point) => point.queries <= state.budget) }));
  const tableRows = state.policies.flatMap((policy) => BUDGETS.filter((budget) => budget <= state.budget).map((budget) => ({ policy, budget,
    hits: families.hits.find((item) => item.policy === policy)?.points.find((point) => point.queries === budget),
    precision: families.precision.find((item) => item.policy === policy)?.points.find((point) => point.queries === budget),
    systems: families.systems.find((item) => item.policy === policy)?.points.find((point) => point.queries === budget),
  })));
  const csv = useMemo(() => comparisonCsv(data.curves, data.theme, state, DATA_RELEASE.dataReleaseId), [data.curves, data.theme, state]);
  const comparisonDownload = useCsvDownload(csv);
  const manualUpdate = (patch: Partial<RouteState>) => { playback.pause(); update(patch); };
  const togglePolicy = (policy: Policy) => {
    const next = state.policies.includes(policy) ? state.policies.filter((item) => item !== policy) : [...state.policies, policy];
    if (next.length > 0) manualUpdate({ policies: next, policy: next.includes(state.policy) ? state.policy : next[0] });
  };
  const inspectedPoints = Object.fromEntries(METRICS.map((item) => [item,
    families[item].find((family) => family.policy === state.policy)?.points.find((point) => point.queries === state.budget)])) as Record<ReplayMetric, ReplayChartPoint | undefined>;
  const share = async () => { playback.pause(); setShareStatus('Copy the browser address to share this recorded selection.'); try { await navigator.clipboard.writeText(window.location.href); setShareStatus('Replay link copied.'); }
    catch { setShareStatus('Copy the browser address to share this recorded selection.'); } };

  return <div className="replay-page">
    <header className="view-header"><p className="eyebrow">The recorded acquisition experiment</p><h1 className="page-heading" tabIndex={-1}>Compare the search policies.</h1><p className="lede">Explore saved historical outcomes under equal query budgets. Quality retrieved more near-stable records than Full in all five splits. Step through the recorded decisions to see how those results accumulated.</p></header>
    <section className="control-bar replay-controls" aria-label="Recorded comparison selections">
      <label className="field">Split<select value={aggregate ? 'aggregate' : String(state.seed)} onChange={(event) => manualUpdate(event.target.value === 'aggregate' ? { mode: 'aggregate' } : { mode: 'seed', seed: Number(event.target.value) as ReplaySeed })}><option value="aggregate">Aggregate · five overlapping splits</option>{SEEDS.map((seed) => <option value={seed} key={seed}>Split {seed}</option>)}</select></label>
      <label className="field">Inspected policy<select value={state.policy} onChange={(event) => manualUpdate({ policy: event.target.value as Policy })}>{state.policies.map((policy) => <option key={policy} value={policy}>{data.theme.policyLabels[policy]}</option>)}</select></label>
      <label className="field budget-field" htmlFor="replay-budget"><span>Completed historical queries <output htmlFor="replay-budget">{state.budget} / 50</output></span><input id="replay-budget" className="budget-range" type="range" min="0" max="50" step="10" value={state.budget} aria-label="Completed historical queries" aria-valuetext={`${state.budget} completed queries, at recorded ten-query boundaries`} onChange={(event) => manualUpdate({ budget: Number(event.target.value) as BatchBudget })} /><span className="budget-ticks" aria-hidden="true">{BUDGETS.map((budget) => <span key={budget}>{budget}</span>)}</span></label>
    </section>
    <fieldset className="policy-toggles"><legend>Compare policies</legend>{POLICIES.map((policy) => <label key={policy}><input type="checkbox" checked={state.policies.includes(policy)} disabled={state.policies.includes(policy) && state.policies.length === 1} onChange={() => togglePolicy(policy)} /><span className="policy-dot" style={{ backgroundColor: policyColour(data.theme, policy) }} aria-hidden="true" />{data.theme.policyLabels[policy]}</label>)}</fieldset>
    <section className="replay-current" aria-label="Current inspected-policy metrics"><div className="replay-current-label"><span className="policy-dot" style={{ backgroundColor: policyColour(data.theme, state.policy) }} />{data.theme.policyLabels[state.policy]} · {aggregate ? 'five-split mean' : `split ${state.seed}`} · {state.budget} completed queries</div><div className="replay-metrics">{METRICS.map((item) => <div className="replay-metric" key={item}><span>{LABELS[item]}</span><strong>{display(inspectedPoints[item], item, aggregate)}</strong><small>{state.budget === 0 && item === 'precision' ? 'No queried records yet' : aggregate ? `Sample SD ${formatNumber((inspectedPoints[item]?.sampleStd ?? 0) * (item === 'precision' ? 100 : 1), 2)}${item === 'precision' ? ' percentage points' : ''}` : 'Saved cumulative outcome'}</small></div>)}</div></section>
    <section className="playback-panel" aria-labelledby="playback-heading"><div className="playback-heading"><div><span className="eyebrow">Recorded batch replay</span><h2 id="playback-heading">Inspect, then reveal.</h2></div><StatusBadge tone={playing ? 'blue' : 'neutral'}>{playing ? 'Playing saved batches' : 'Paused'}</StatusBadge></div>
      <p className="playback-phase" role="status" aria-live="polite">{!aggregate && history.status === 'error' ? 'Saved query history unavailable; retry below.' : playback.phaseLabel}</p>
      <div className="playback-actions"><button className="button button-primary" disabled={!playing && !playback.canPlay} onClick={playing ? playback.pause : playback.play}>{playing ? 'Pause' : 'Play'}</button><button className="button button-secondary" disabled={playing || !playback.canNext} onClick={playback.next}>{playback.nextLabel}</button><button className="text-button" disabled={aggregate || !historyReady} onClick={() => manualUpdate({ budget: 0, batch: 1, revealed: false })}>Start at zero</button><button className="text-button" onClick={playback.resetReplay}>Reset exploration</button></div>
      {aggregate ? <div><button className="button button-secondary" disabled>Inspect 10 selected queries</button><p className="small-text">Aggregate mode has no individual query history. Select one recorded split to play, inspect or export its ten-query batches.</p></div> : history.status !== 'ready' ? <DataNotice status={history.status} error={history.error} retry={history.retry} /> : <div className="batch-inspection"><label className="field">Inspected batch<select value={state.batch} onChange={(event) => manualUpdate({ batch: Number(event.target.value) as Round })}>{[1, 2, 3, 4, 5].filter((round) => round <= Math.min(5, state.budget / 10 + 1)).map((round) => <option value={round} key={round}>Batch {round} · {round * 10 <= state.budget ? 'revealed' : 'predictions only'}</option>)}</select></label><button className="button button-secondary" disabled={!historyReady} onClick={() => { playback.pause(); setQueryOpen(true); }}>Inspect 10 selected queries</button><span className="small-text">{state.revealed ? 'This batch’s historical outcomes are revealed.' : 'Predictions only; historical outcomes are hidden.'}</span></div>}
      <p className="small-text">Each step uses a saved ten-query decision and subsequent label reveal. It never implies a refit after each individual query. Playing pauses when you leave, switch selections, reset or hide the browser page.</p>
    </section>
    <section className="replay-plot-section" aria-labelledby="replay-curves-heading"><div className="section-heading-row"><div><p className="eyebrow">Same budget, different policies</p><h2 id="replay-curves-heading">The recorded search curves.</h2></div><button className="source-link" onClick={() => { playback.pause(); onSources(data.curves.sourceIds); }}>Curve sources ↗</button></div>
      <fieldset className="metric-switch"><legend>Chart metric</legend>{METRICS.map((item) => <label key={item} className={item === metric ? 'is-active' : ''}><input type="radio" name="replay-metric" value={item} checked={metric === item} onChange={() => setMetric(item)} />{LABELS[item]}</label>)}</fieldset>
      <ChartBoundary><Suspense fallback={<DataNotice status="loading" />}><ReplayChart series={series} metric={metric} budget={state.budget} onBudgetSelect={(budget) => manualUpdate({ budget })} /></Suspense></ChartBoundary>
      <p className="scope-note">Historical near-stable means signed hull distance ≤0.05 eV/atom. At zero queries, counts are a derived display origin and precision is unavailable. Aggregate bands are mean ± sample SD across five overlapping splits; they are not a predictor’s calibrated radius or independent-dataset confidence intervals.</p>
    </section>
    <section className="research-table-section" aria-labelledby="replay-table-heading"><div className="section-heading-row"><h2 id="replay-table-heading">Displayed recorded data</h2><div className="replay-export-actions">{comparisonDownload && <a className="button button-secondary" href={comparisonDownload.url} download={`flamel-comparison-${aggregate ? 'aggregate' : state.seed}-${state.budget}queries.csv`}>Download displayed comparison</a>}<button className="source-link" onClick={share}>Copy replay link ↗</button></div></div>
      <p className="small-text" role="status">{shareStatus}</p><p className="small-text">Visible policies at 0/10/20/30/40/50 boundaries up to {state.budget} completed queries. CSV retains full precision, units, source IDs and null meanings.</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Recorded acquisition values, scroll horizontally"><table><caption>{aggregate ? 'Mean and sample SD across five overlapping splits.' : `Saved outcomes for split ${state.seed}.`} Zero-query values are derived display states. Precision percentages are shown as fractions in the CSV.</caption><thead><tr><th scope="col">Policy</th><th scope="col">Completed queries</th><th scope="col">Near-stable hits{aggregate && ' · mean ± SD'}</th><th scope="col">Precision{aggregate && ' · mean ± SD'}</th><th scope="col">Chemical systems{aggregate && ' · mean ± SD'}</th></tr></thead><tbody>{tableRows.map((row) => <tr key={`${row.policy}-${row.budget}`} className={row.budget === state.budget ? 'current-budget-row' : ''}><th scope="row"><span className="policy-dot" style={{ backgroundColor: policyColour(data.theme, row.policy) }} aria-hidden="true" />{data.theme.policyLabels[row.policy]}</th><td className="numeric">{row.budget}</td>{METRICS.map((item) => <td key={item} className="numeric">{display(row[item], item, aggregate)}{aggregate && row[item]?.sampleStd !== null && row[item]?.sampleStd !== undefined && <> <span className="muted">± {formatNumber(row[item]!.sampleStd! * (item === 'precision' ? 100 : 1), 2)}{item === 'precision' ? ' pp' : ''}</span></>}</td>)}</tr>)}</tbody></table></div>
    </section>
    <div className="interpretation-row"><p>These are historical retrieval outcomes, not newly DFT-confirmed materials. Broader chemistry coverage and higher retrieval yield answer different questions.</p><button className="source-link" onClick={() => { playback.pause(); onGlossary(); }}>Explain the terms ↗</button></div>
    {queryOpen && !aggregate && history.data && batch && <QueryDrawer history={history.data} batch={batch} policy={state.policy} policyLabel={data.theme.policyLabels[state.policy]} seed={state.seed} revealed={state.revealed} completedBudget={state.budget} canNext={playback.canNext} nextLabel={playback.nextLabel} onNext={playback.next} onClose={() => setQueryOpen(false)} onSources={(ids) => { setQueryOpen(false); playback.pause(); onSources(ids); }} />}
  </div>;
}
