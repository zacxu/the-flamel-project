import { useId } from 'react';
import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import type { DotItemDotProps, TooltipContentProps } from 'recharts';
import type { BatchBudget, Policy } from '../data/contracts';
import type { ReplayMetric, ReplaySeries } from '../replay/model';
import '../replay/chart.css';

interface ReplayChartProps {
  readonly series: readonly ReplaySeries[];
  readonly metric: ReplayMetric;
  readonly budget: BatchBudget;
  readonly onBudgetSelect?: (budget: BatchBudget) => void;
}

const BOUNDARIES: readonly BatchBudget[] = [0, 10, 20, 30, 40, 50];
const DASHES: Readonly<Record<Policy, string | undefined>> = {
  quality: undefined, full: '8 3', quality_diversity: '3 3', random: '2 5', uncertainty: '10 3 2 3',
};
const LABELS: Readonly<Record<ReplayMetric, string>> = {
  hits: 'Cumulative near-stable hits', precision: 'Cumulative hit precision', systems: 'Chemical-system coverage',
};

function formatValue(value: number, metric: ReplayMetric): string {
  return metric === 'precision'
    ? `${new Intl.NumberFormat('en', { maximumFractionDigits: 1 }).format(value * 100)}%`
    : new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(value);
}

function RecordedTooltip({ active, label, series, metric }: Pick<TooltipContentProps, 'active' | 'label'> & {
  readonly series: readonly ReplaySeries[]; readonly metric: ReplayMetric;
}) {
  const queries = typeof label === 'number' ? label : Number(label);
  if (!active || !BOUNDARIES.includes(queries as BatchBudget)
    || !series.some((item) => item.points.some((point) => point.queries === queries))) return null;
  return <div className="replay-chart-tooltip">
    <p><strong>{queries} completed queries</strong></p>
    {queries === 0 && <p className="replay-tooltip-origin">Derived zero-query display origin; no labels acquired.</p>}
    <ul>{series.map((item) => {
      const point = item.points.find((value) => value.queries === queries);
      if (!point) return null;
      return <li key={item.policy}>
        <span className="replay-chart-key" style={{ borderColor: item.colour }} aria-hidden="true" />
        <span><strong>{item.label}</strong><span className="replay-tooltip-value">{point.mean === null
          ? queries === 0 && metric === 'precision' ? 'Unavailable at zero queries' : 'Unavailable'
          : <>{point.sampleStd === null ? 'Value' : 'Mean'}: {formatValue(point.mean, metric)}
            {point.sampleStd !== null && <><br />Sample SD: {formatValue(point.sampleStd, metric)}</>}</>}</span></span>
      </li>;
    })}</ul>
  </div>;
}

/** Renders only supplied recorded boundaries; no fitting or intermediate outcomes. */
export default function ReplayChart({ series, metric, budget, onBudgetSelect }: ReplayChartProps) {
  const captionId = useId();
  const helpId = useId();
  // This second boundary check prevents a caller from accidentally exposing future outcomes.
  const recordedSeries = series.map((item) => ({ ...item,
    points: item.points.filter((point) => BOUNDARIES.includes(point.queries as BatchBudget) && point.queries <= budget),
  }));
  const chartData = BOUNDARIES.filter((queries) => queries <= budget).map((queries) => {
    const row: Record<string, number | readonly number[] | null> = { queries };
    for (const item of recordedSeries) {
      const point = item.points.find((value) => value.queries === queries);
      row[`${item.policy}Value`] = point?.mean ?? null;
      row[`${item.policy}Band`] = point?.sampleStd !== null && point?.sampleStd !== undefined
        && point.low !== null && point.high !== null ? [point.low, point.high] : null;
    }
    return row;
  });
  const hasSpread = recordedSeries.some((item) => item.points.some((point) => point.sampleStd !== null));
  const values = recordedSeries.flatMap((item) => item.points.flatMap((point) =>
    [point.mean, point.low, point.high].filter((value): value is number => value !== null && Number.isFinite(value))));
  const lower = Math.min(0, ...values);
  const upper = Math.max(metric === 'precision' ? 1 : 5, ...values);
  const padding = Math.max((upper - lower) * 0.05, 0.01);
  // Spread bands retain their calculated extent, including values outside physical bounds.
  const domain: [number, number] = [lower < 0 ? lower - padding : 0, upper + padding];

  function recordedDot(colour: string, policy: Policy) {
    return ({ cx, cy, payload }: DotItemDotProps) => {
      const record: unknown = payload;
      const queries = record && typeof record === 'object' && 'queries' in record ? record.queries : null;
      if (typeof cx !== 'number' || typeof cy !== 'number' || typeof queries !== 'number'
        || !BOUNDARIES.includes(queries as BatchBudget) || queries > budget) return <g />;
      const select = () => onBudgetSelect?.(queries as BatchBudget);
      const label = recordedSeries.find((item) => item.policy === policy)?.label ?? policy;
      return <circle cx={cx} cy={cy} r={queries === budget ? 4.5 : 3}
        fill="var(--white, #fffefa)" stroke={colour} strokeWidth={2}
        className={onBudgetSelect ? 'replay-chart-dot replay-chart-dot-interactive' : 'replay-chart-dot'}
        role={onBudgetSelect ? 'button' : undefined} tabIndex={onBudgetSelect ? 0 : undefined}
        aria-label={onBudgetSelect ? `Set budget to ${queries} completed queries; ${label} curve point` : undefined}
        onClick={onBudgetSelect ? select : undefined}
        onKeyDown={onBudgetSelect ? (event) => {
          if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); }
        } : undefined} />;
    };
  }

  return <figure className="replay-chart" aria-labelledby={captionId} aria-describedby={helpId}>
    <figcaption id={captionId} className="replay-chart-caption">
      <strong>{LABELS[metric]}</strong><span>{metric === 'precision' ? 'Hits / completed queries' : metric === 'systems'
        ? 'Distinct systems queried' : 'Signed reference-hull distance ≤0.05 eV/atom'}</span>
    </figcaption>
    <ul className="replay-chart-legend" aria-label="Visible acquisition policies">{recordedSeries.map((item) =>
      <li key={item.policy}><svg width="28" height="10" viewBox="0 0 28 10" aria-hidden="true"><line x1="0" y1="5" x2="28" y2="5"
        stroke={item.colour} strokeWidth="2.5" strokeDasharray={DASHES[item.policy]} /></svg>{item.label}</li>)}</ul>
    <div className="replay-chart-canvas">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <ComposedChart data={chartData} accessibilityLayer margin={{ top: 14, right: 18, bottom: 28, left: 0 }}
          desc={`${LABELS[metric]} at recorded ten-query boundaries up to ${budget} completed queries. The table below provides the values.`}>
          <CartesianGrid stroke="var(--line, #d8d3c8)" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="queries" type="number" domain={[0, 50]} ticks={[...BOUNDARIES]} allowDecimals={false}
            stroke="var(--muted, #52606a)" tickLine={false} tick={{ fontSize: 12 }}
            label={{ value: 'Completed historical queries', position: 'bottom', offset: 10, fontSize: 12 }} />
          <YAxis domain={domain} width={metric === 'precision' ? 51 : 43} stroke="var(--muted, #52606a)"
            tickLine={false} axisLine={false} tick={{ fontSize: 12 }}
            tickFormatter={(value: number) => metric === 'precision' ? `${Math.round(value * 100)}%` : formatValue(value, metric)} />
          <Tooltip filterNull={false} isAnimationActive={false} cursor={{ stroke: '#949a97', strokeDasharray: '3 3' }}
            content={(props) => <RecordedTooltip {...props} series={recordedSeries} metric={metric} />}
            wrapperStyle={{ maxWidth: 'min(310px, 85vw)', zIndex: 3 }} />
          <ReferenceLine x={budget} stroke="#777a72" strokeDasharray="2 5" />
          {recordedSeries.map((item) => <Area key={`${item.policy}-spread`} dataKey={`${item.policy}Band`}
            type="linear" fill={item.colour} fillOpacity={0.1} stroke="none" isAnimationActive={false}
            connectNulls={false} dot={false} activeDot={false} legendType="none" tooltipType="none" />)}
          {recordedSeries.map((item) => <Line key={item.policy} dataKey={`${item.policy}Value`} name={item.label}
            type="linear" stroke={item.colour} strokeWidth={2.5} strokeDasharray={DASHES[item.policy]}
            isAnimationActive={false} connectNulls={false} dot={recordedDot(item.colour, item.policy)} activeDot={false} />)}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
    <p id={helpId} className="replay-chart-help">{hasSpread
      ? 'Lines show the mean; shaded bands show ±1 sample SD across five overlapping historical splits. This is acquisition variability, not predictor calibration or an independent confidence interval.'
      : 'Each point is a recorded outcome for the selected split. Lines connect recorded boundaries; no intermediate outcomes are measured.'}
      {' '}Only completed query boundaries are shown. Zero counts are a derived display origin; no labels have been acquired at zero queries.
      {' '}{metric === 'precision' && budget === 0 ? 'Precision is unavailable at zero queries. ' : ''}
      Use the data table below for exact values.</p>
  </figure>;
}
