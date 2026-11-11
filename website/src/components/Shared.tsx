import { Component, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { CoreData } from '../data/ResearchData';
import { usePresentationAsset } from '../data/usePresentationAsset';

export const formatNumber = (value: number | null | undefined, digits = 1) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(value) : 'Unavailable';

export function StatusBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'copper' | 'blue' }) {
  return <span className={`status-badge status-${tone}`}>{children}</span>;
}

export function DataNotice({ status, error, retry }: { status: string; error?: string | null; retry?: () => void }) {
  const failed = status === 'error';
  return <div className={`data-notice ${failed ? 'notice-error' : ''}`} role={failed ? 'alert' : 'status'}>
    <span className="eyebrow">{failed ? 'Evidence unavailable' : status === 'loading' ? 'Loading saved research' : 'No recorded data'}</span>
    <p>{failed ? error || 'This evidence could not be loaded.' : status === 'loading'
      ? 'The study text stays available while its verified data loads.' : 'No saved record exists for this selection.'}</p>
    {failed && retry && <button className="button button-secondary" onClick={retry}>Try loading again</button>}
  </div>;
}

export function SavedFigure({ logicalName, alt, caption, className = '' }: {
  logicalName: string | null; alt: string; caption?: ReactNode; className?: string;
}) {
  const asset = usePresentationAsset(logicalName);
  return <figure className={`saved-figure ${className}`}>
    {asset.status === 'ready' && asset.url
      ? <img src={asset.url} alt={alt} width="760" height="600" />
      : <DataNotice status={asset.status} error={asset.error} retry={asset.retry} />}
    {caption && <figcaption>{caption}</figcaption>}
  </figure>;
}

export class ViewBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div className="data-notice notice-error" role="alert">
      <h2>This view could not be displayed.</h2><p>The saved evidence has not changed. You can retry this view or use the navigation above.</p>
      <button className="button button-secondary" onClick={() => this.setState({ failed: false })}>Retry view</button>
    </div> : this.props.children;
  }
}

export function Modal({ title, children, onClose, wide = false, className = '' }: {
  title: string; children: ReactNode; onClose: () => void; wide?: boolean; className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement;
    const dialog = ref.current;
    dialog?.showModal();
    return () => {
      const shouldRestore = document.activeElement === document.body || !!dialog?.contains(document.activeElement);
      dialog?.close();
      if (shouldRestore && previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, []);
  return <dialog ref={ref} className={`drawer ${wide ? 'drawer-wide' : ''} ${className}`} aria-labelledby="drawer-title"
    onCancel={(event) => { event.preventDefault(); closeRef.current(); }}
    onClick={(event) => { if (event.target === event.currentTarget) closeRef.current(); }}>
    <div className="drawer-content">
      <header className="drawer-header"><div><span className="eyebrow">Study notes</span><h2 id="drawer-title">{title}</h2></div>
        <button className="icon-button" autoFocus aria-label={`Close ${title.toLowerCase()}`} onClick={onClose}>×</button></header>
      {children}
    </div>
  </dialog>;
}

export function SourceDrawer({ data, ids, onClose }: { data: CoreData; ids: readonly string[] | null; onClose: () => void }) {
  const [search, setSearch] = useState('');
  const selected = ids === null ? data.provenance.sources : data.provenance.sources.filter((source) => ids.includes(source.sourceId));
  const filtered = selected.filter((source) => `${source.label} ${source.description} ${source.sourceId}`.toLowerCase().includes(search.toLowerCase()));
  return <Modal title="Sources & methods" onClose={onClose} wide>
    <p className="scope-note">A source hash identifies a saved file. It does not establish scientific acceptance or a newly stable material.</p>
    <dl className="compact-facts"><div><dt>Study frozen</dt><dd>22 October 2026</dd></div><div><dt>Execution</dt><dd>Recorded research only</dd></div>
      <div><dt>Historical target</dt><dd>Signed hull distance, eV/atom</dd></div><div><dt>Calibrated radius</dt><dd>q × max(disagreement, 0.01 eV/atom)</dd></div></dl>
    <p>Historical near-stable retrieval uses ≤0.05 eV/atom; on/below-reference-hull hits use ≤0. Fresh QE energies have a different reference and are not interchangeable feedback labels.</p>
    <label className="field">Search these sources<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="File label or description" /></label>
    <p className="small-text" role="status">{filtered.length} of {selected.length} source records</p>
    {ids !== null && ids.some((id) => !selected.some((source) => source.sourceId === id)) && <p className="scope-note">Some requested source records are unavailable in this release.</p>}
    {filtered.length === 0 ? <DataNotice status="unavailable" /> : <ul className="source-list">{filtered.map((source) => <li key={source.sourceId}>
      <h3>{source.label}</h3><p>{source.description}</p><dl><dt>Source ID</dt><dd><code>{source.sourceId}</code></dd><dt>SHA-256</dt><dd><code className="hash">{source.sha256}</code></dd><dt>Bytes</dt><dd className="numeric">{formatNumber(source.bytes, 0)}</dd></dl>
    </li>)}</ul>}
    <details className="attribution-details"><summary>Data and software attribution</summary>{data.methods.attributions.map((item) => <section key={item.name}>
      <h3>{item.name}</h3><p>{item.credit}</p><p>{item.role}. {item.modifications}</p><p><a href={item.url} target="_blank" rel="noreferrer">Upstream project ↗</a> · {item.licenceUrl ? <a href={item.licenceUrl} target="_blank" rel="noreferrer">{item.licence}</a> : item.licence}</p>
    </section>)}</details>
    <p className="small-text">Publication links remain unavailable until checked public destinations exist.</p>
    <ul className="publication-list">{data.methods.externalPublicationLinks.map((item) => <li key={item.kind}>{item.label}<span>Not yet published</span></li>)}</ul>
  </Modal>;
}

export function GlossaryDrawer({ data, onClose }: { data: CoreData; onClose: () => void }) {
  const [search, setSearch] = useState('');
  const terms = data.glossary.terms.filter((term) => {
    const aliases = term.id === 'disagreement' ? 'uncertainty ensemble standard deviation' : term.id === 'calibration-radius' ? 'uncertainty confidence interval' : '';
    return `${term.label} ${term.definition} ${aliases}`.toLowerCase().includes(search.toLowerCase());
  });
  return <Modal title="Research glossary" onClose={onClose}>
    <label className="field">Find a term<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Try “uncertainty”" /></label>
    {terms.length === 0 ? <p className="scope-note" role="status">No glossary terms match this search. Try “calibration” or “near-stable”.</p> : <dl className="glossary-list">{terms.map((term) => <div key={term.id}><dt>{term.label}</dt><dd>{term.definition}{term.unit && <span className="term-unit">Unit: {term.unit}</span>}</dd></div>)}</dl>}
  </Modal>;
}
