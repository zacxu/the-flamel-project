import type { ReplayDataset, ReplayBatch, Policy, ReplaySeed } from '../data/contracts';
import { DATA_RELEASE } from '../data/release';
import { displayQueries, queryCsv } from '../replay/model';
import { useCsvDownload } from '../replay/useCsvDownload';
import { formatNumber, Modal, StatusBadge } from './Shared';

interface Props {
  history: ReplayDataset; batch: ReplayBatch; policy: Policy; policyLabel: string;
  seed: ReplaySeed; revealed: boolean; completedBudget: number;
  canNext: boolean; nextLabel: string; onNext: () => void;
  onClose: () => void; onSources: (ids: readonly string[]) => void;
}

export function QueryDrawer({ history, batch, policy, policyLabel, seed, revealed, completedBudget,
  canNext, nextLabel, onNext, onClose, onSources }: Props) {
  const rows = displayQueries(batch, revealed);
  const download = useCsvDownload(queryCsv(history, policy, batch.round, revealed, DATA_RELEASE.dataReleaseId));
  return <Modal title={`Batch ${batch.round} · selected queries`} onClose={onClose} className="query-modal">
    <div className="query-context"><span>Split {seed} · {policyLabel} · {completedBudget} completed queries</span>
      <StatusBadge tone={revealed ? 'blue' : 'copper'}>{revealed ? 'Recorded outcomes revealed' : 'Pre-reveal predictions'}</StatusBadge></div>
    <p className="scope-note">Exactly ten recorded selections, not the complete candidate pool. {revealed
      ? 'These historical labels were revealed together after this saved batch decision.'
      : 'The predictions below were recorded before this batch’s labels were revealed. Targets and hit flags remain hidden here and in the query CSV.'}</p>
    <div className="query-actions">
      {canNext && <button className="button button-primary" onClick={onNext}>{nextLabel}</button>}
      {download && <a className="button button-secondary" href={download.url} download={`flamel-queries-${seed}-${policy}-batch-${batch.round}-${revealed ? 'revealed' : 'predictions'}.csv`}>Download these 10 queries</a>}
      <button className="source-link" onClick={() => onSources(history.sourceIds)}>Query and metadata sources ↗</button>
    </div>
    <div className="table-scroll query-table" tabIndex={0} role="region" aria-label="Ten selected queries, scroll horizontally">
      <table><caption>Batch {batch.round}: {revealed ? 'saved predictions and revealed historical outcomes' : 'saved pre-selection predictions; outcomes hidden'}. Energies and radii are in eV/atom.</caption>
        <thead><tr><th scope="col">Query / material</th><th scope="col">Formula / system</th><th scope="col">Role</th><th scope="col">Predicted mean<br />eV/atom</th><th scope="col">Calibrated radius<br />eV/atom</th><th scope="col">Diversity</th><th scope="col">Selection score</th><th scope="col">Historical target<br />eV/atom</th><th scope="col">Near-stable hit<br />≤0.05 eV/atom</th><th scope="col">Reference-hull hit<br />≤0 eV/atom</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.materialId}>
          <th scope="row"><span className="query-number">#{row.queryNumber}</span><span className="material-id">{row.materialId}</span></th>
          <td><strong>{row.formula}</strong><span className="query-subline">{row.chemicalSystem} · {row.atoms} atoms</span></td>
          <td>{row.role.replaceAll('_', ' ')}</td><td className="numeric">{formatNumber(row.predictedMeanEVPerAtom, 6)}</td>
          <td className="numeric">{formatNumber(row.calibratedRadiusEVPerAtom, 6)}</td><td className="numeric">{formatNumber(row.diversityAtSelection, 6)}</td>
          <td className="numeric">{row.score === null ? 'Unavailable' : formatNumber(row.score, 6)}</td>
          <td className="numeric">{row.revealedLabelEVPerAtom === null ? 'Hidden until reveal' : formatNumber(row.revealedLabelEVPerAtom, 6)}</td>
          <td>{row.nearStableHit === null ? 'Hidden until reveal' : row.nearStableHit ? 'Yes' : 'No'}</td>
          <td>{row.referenceHullHit === null ? 'Hidden until reveal' : row.referenceHullHit ? 'Yes' : 'No'}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p className="small-text">Diversity and selection score retain the recorded policy’s scale. A missing random-policy score is unavailable, never zero. The calibration radius is q × max(ensemble disagreement, 0.01 eV/atom).</p>
    <p className="small-text">Hiding is a teaching display state, not access control: the historical outcomes are present in the public static data. No control changes the frozen model, coefficients or labels.</p>
  </Modal>;
}
