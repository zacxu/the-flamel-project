import { Component, lazy, Suspense, useState } from 'react';
import type { ReactNode } from 'react';
import type { SavedStage } from '../data/contracts';
import { SavedFigure } from './Shared';
import '../crystal/lab.css';

const CrystalViewer = lazy(() => import('./CrystalViewer'));

class RendererBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

/** Key by stage: a failing renderer cannot retain a previous geometry. */
export function CrystalDisplay({ record, elementColours, compact = false }: {
  record: SavedStage; elementColours: Readonly<Record<string, string>>; compact?: boolean;
}) {
  return <DisplayForStage key={record.stageId} record={record} elementColours={elementColours} compact={compact} />;
}

function DisplayForStage({ record, elementColours, compact }: {
  record: SavedStage; elementColours: Readonly<Record<string, string>>; compact: boolean;
}) {
  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  // The compact introduction starts with its genuine saved figure. Load the
  // shared 3D chunk on intent; the full Lab still starts interactively.
  const [showSaved, setShowSaved] = useState(compact);
  const [openedInteractive, setOpenedInteractive] = useState(!compact);
  const figure = <SavedFigure logicalName={record.fallbackFigureLogicalName}
    alt={`Saved ${record.geometry.actualAtoms}-atom ${record.geometry.formula} cell at stage ${record.stage}, with original saved site identity.`}
    caption="Stage-specific scientific figure. Periodic positions are wrapped for display; no additional physical atoms." />;
  const fallback = <div className="crystal-fallback" role="status"><p><strong>Interactive 3D unavailable.</strong> {failure ?? 'The renderer could not load.'} The saved figure, metadata, coordinates and export remain available.</p>{figure}<button className="button button-secondary" onClick={() => { setFailure(null); setAttempt(value => value + 1); }}>Retry interactive 3D</button></div>;
  return <div className={`crystal-display ${compact ? 'crystal-display-compact' : ''}`}>
    {showSaved ? <div>{figure}<button className="text-button" onClick={() => { setOpenedInteractive(true); setShowSaved(false); }}>{openedInteractive ? 'Return to interactive 3D' : 'Explore interactive 3D'}</button></div> : failure ? fallback : <RendererBoundary key={attempt} fallback={fallback}>
      <Suspense fallback={<div className="crystal-loading" role="status"><p>Loading interactive 3D. The saved geometry is already available below.</p>{figure}</div>}>
        <CrystalViewer record={record} elementColours={elementColours} compact={compact} onFailure={setFailure} />
      </Suspense>
    </RendererBoundary>}
    {!showSaved && <button className="text-button crystal-figure-toggle" onClick={() => setShowSaved(true)}>Use saved scientific figure</button>}
  </div>;
}
