import { useEffect, useRef, useState } from 'react';
import { useResearch } from './data/ResearchData';
import { useRoute } from './state/useRoute';
import { DataNotice, GlossaryDrawer, SourceDrawer, ViewBoundary } from './components/Shared';
import { Overview } from './views/Overview';
import { Workflow } from './views/Workflow';
import { Replay } from './views/Replay';
import { CrystalLab } from './views/CrystalLab';
import { Findings } from './views/Findings';
import { Evidence } from './views/Evidence';
import { formatRoute, type View } from './state/route';
import { GuidedTour } from './tour/GuidedTour';
import { TourContext } from './tour/TourContext';
import { useTour } from './tour/useTour';
import { UI_RELEASE_ID } from './generated/uiRelease';

const NAV: readonly { id: View; label: string; number: string }[] = [
  { id: 'overview', label: 'Overview', number: '01' }, { id: 'workflow', label: 'Workflow', number: '02' },
  { id: 'replay', label: 'Replay', number: '03' }, { id: 'crystals', label: 'Crystal Lab', number: '04' },
  { id: 'findings', label: 'Findings', number: '05' }, { id: 'evidence', label: 'Evidence', number: '06' },
];

export default function App() {
  const { status, data, error, retry } = useResearch();
  const { state, update: routeUpdate, reset: routeReset, routeNotice, bindStructureIndex, playing, setPlaying, registerCancellation } = useRoute();
  const [drawer, setDrawer] = useState<'sources' | 'glossary' | null>(null);
  const [sourceIds, setSourceIds] = useState<readonly string[] | null>(null);
  const [linkStatus, setLinkStatus] = useState('');
  const main = useRef<HTMLElement>(null);
  const focusedView = useRef<View | null>(null);
  const tour = useTour(scene => {
    setDrawer(null);
    const example = scene.exampleId ? data?.structures.coreExamples.find(item => item.id === scene.exampleId) : undefined;
    const candidate = example ? data?.structures.candidates.find(item => item.candidateId === example.candidateId) : undefined;
    const stage = candidate ? data?.structures.stages.find(item => item.candidateId === candidate.candidateId && item.stage === scene.stage) : undefined;
    routeUpdate({ ...scene.patch, view: scene.view, ...(candidate ? { candidateId: candidate.candidateId, stageId: stage?.stageId ?? candidate.defaultStageId } : {}) }, true);
  }, () => setPlaying(false));
  const stopTour = () => { if (tour.status !== 'idle') { tour.controller.exit(); setPlaying(false); } };
  const update = (patch: Parameters<typeof routeUpdate>[0], replace = false) => { stopTour(); routeUpdate(patch, replace); };
  const navigate = (view: View, patch: Parameters<typeof routeUpdate>[0] = {}) => update({ ...patch, view });
  const reset = () => { stopTour(); routeReset(); };
  useEffect(() => {
    const anchor = tour.scene?.anchor;
    if (!anchor || tour.status === 'idle') return;
    let done = false;
    const reveal = () => {
      const element = document.getElementById(anchor);
      if (!element || done) return;
      done = true;
      const toolbar = document.querySelector('.guided-tour');
      const offset = toolbar && ['sticky', 'fixed'].includes(window.getComputedStyle(toolbar).position) ? toolbar.getBoundingClientRect().height : 0;
      window.scrollTo({ top: Math.max(0, window.scrollY + element.getBoundingClientRect().top - offset - 20), behavior: 'instant' });
    };
    reveal();
    const observer = new MutationObserver(reveal);
    if (!done && main.current) observer.observe(main.current, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [tour.scene?.id, tour.status]);
  useEffect(() => { setDrawer(null); }, [state.view, state.mode, state.seed, state.policy]);
  useEffect(() => {
    if (tour.status === 'idle' && drawer === null && focusedView.current !== state.view) {
      main.current?.focus({ preventScroll: true });
      window.scrollTo(0, 0);
      focusedView.current = state.view;
    }
  }, [state.view, drawer, tour.status]);
  useEffect(() => { if (data) bindStructureIndex(data.structures); }, [data, bindStructureIndex]);
  const onSources = (ids?: readonly string[]) => { stopTour(); setPlaying(false); setSourceIds(ids ?? null); setDrawer('sources'); };
  const onGlossary = () => { stopTour(); setPlaying(false); setDrawer('glossary'); };
  const props = data ? { data, state, update, onSources, onGlossary, playing, setPlaying, registerCancellation, reset } : null;
  const copyLink = async () => { stopTour(); setPlaying(false); try { await navigator.clipboard.writeText(window.location.href); setLinkStatus('Link copied.'); }
    catch { setLinkStatus('Copy the address from your browser to share this selection.'); } };
  return <TourContext.Provider value={tour}>
    <a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); main.current?.focus(); }}>Skip to content</a>
    <header className="site-header"><div className="header-top"><a className="brand" href="#/overview" onClick={(event) => { event.preventDefault(); navigate('overview'); }} aria-label="The Flamel Project overview">
      <svg className="brand-mark" viewBox="0 0 40 44" fill="none" aria-hidden="true">
        <rect width="40" height="44" fill="var(--paper)" />
        <path d="M20 2 37 12v20L20 42 3 32V12L20 2Z M20 2v40 M3 12l34 20 M37 12 3 32" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <circle cx="20" cy="22" r="4" fill="currentColor" />
      </svg><span>The Flamel<br /><b>Project</b></span></a>
      <div className="header-context"><span className="status-dot" />Recorded research<span className="header-date">22 OCT 2026</span></div>
      <div className="header-tools"><button className="text-button" disabled={!data} onClick={onGlossary}>Glossary</button><button className="text-button" disabled={!data} onClick={() => onSources()}>Sources ↗</button></div></div>
      <nav className="main-nav" aria-label="Research views">{NAV.map((view) => <a key={view.id} href={formatRoute({ ...state, view: view.id })} aria-current={state.view === view.id ? 'page' : undefined} onClick={(event) => { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return; event.preventDefault(); navigate(view.id); }}><span>{view.number}</span>{view.label}</a>)}</nav>
    </header>
    <GuidedTour snapshot={tour} controller={tour.controller} available={status === 'ready' && data !== null} />
    <main id="main-content" ref={main} tabIndex={-1} className={`main-content view-${state.view}`} onClickCapture={stopTour} onChangeCapture={stopTour}>
      {routeNotice && <p className="route-notice" role="status">{routeNotice}</p>}
      {status !== 'ready' || !data || !props ? <><div className="view-header"><span className="eyebrow">A materials discovery prototype</span><h1>Explore the search for new crystals.</h1><p className="lede">Symmetry-conditioned generation, predictive uncertainty and genuine first-principles validation, examined through recorded research.</p></div><DataNotice status={status} error={error} retry={retry} /><p className="scope-note">No new stable material was established. Navigation remains available while evidence loads.</p></>
        : <ViewBoundary key={state.view}>{state.view === 'overview' ? <Overview data={data} navigate={navigate} onSources={onSources} onGlossary={onGlossary} />
          : state.view === 'workflow' ? <Workflow data={data} navigate={navigate} onSources={onSources} onGlossary={onGlossary} />
          : state.view === 'replay' ? <Replay {...props} /> : state.view === 'crystals' ? <CrystalLab {...props} />
          : state.view === 'findings' ? <Findings {...props} /> : <Evidence {...props} />}</ViewBoundary>}
    </main>
    <footer className="site-footer" data-ui-build={UI_RELEASE_ID}><div><span className="footer-brand">The Flamel Project</span><p>A research prototype. Evidence before discovery claims.</p></div><div className="footer-actions"><button className="text-button" onClick={copyLink}>Copy view link ↗</button><button className="text-button" onClick={() => { setDrawer(null); setLinkStatus(''); reset(); }}>Reset exploration</button><span role="status" className="small-text">{linkStatus}</span></div></footer>
    {data && drawer === 'sources' && <SourceDrawer data={data} ids={sourceIds} onClose={() => setDrawer(null)} />}
    {data && drawer === 'glossary' && <GlossaryDrawer data={data} onClose={() => setDrawer(null)} />}
  </TourContext.Provider>;
}
