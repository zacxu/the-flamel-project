import { TOUR_STEPS, TOUR_TOTAL_SECONDS, type TourSnapshot, type createTourController } from './model';
import './tour.css';

const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
type Controller = ReturnType<typeof createTourController>;
export function GuidedTour({ snapshot, controller, available }: { snapshot: TourSnapshot; controller: Controller; available: boolean }) {
  const start = () => { controller.start(); window.requestAnimationFrame(() => document.querySelector<HTMLButtonElement>('[data-tour-action="pause"]')?.focus({ preventScroll: true })); };
  if (snapshot.status === 'idle') return <section className="tour-launch" aria-label="Guided presentation"><div><strong>A three-minute research tour</strong><span>Six scenes through the recorded study. You can pause, skip or return to exploring.</span></div><button className="button button-secondary" disabled={!available} onClick={start}>Start guided tour</button></section>;
  const complete = snapshot.status === 'complete';
  const step = TOUR_STEPS[snapshot.step];
  const elapsed = TOUR_STEPS.slice(0, snapshot.step).reduce((sum, item) => sum + item.seconds, 0) + snapshot.elapsed;
  const exit = () => { controller.exit(); window.requestAnimationFrame(() => document.querySelector<HTMLButtonElement>('.tour-launch button')?.focus({ preventScroll: true })); };
  return <aside className="guided-tour" aria-label="Guided presentation controls">
    <div className="tour-heading"><p className="eyebrow">{complete ? 'Tour complete' : `Step ${snapshot.step + 1} of ${TOUR_STEPS.length} · ${snapshot.status}`}</p><span className="tour-clock" aria-label={`${Math.floor(elapsed)} of ${TOUR_TOTAL_SECONDS} presentation seconds`}>{clock(elapsed)} / 3:00</span></div>
    <h2 id="tour-heading">{step.title}</h2><p className="tour-caption" role="status" aria-live="polite" aria-atomic="true">{complete ? 'The recorded study is ready to explore. Exit the tour to continue browsing, or restart the presentation.' : snapshot.scene?.caption}</p>
    <progress value={elapsed} max={TOUR_TOTAL_SECONDS} aria-label="Guided presentation progress" />
    <div className="tour-actions"><button className="text-button" onClick={controller.previous} disabled={snapshot.step === 0}>Previous tour step</button>{complete ? <button className="button button-secondary" onClick={start}>Restart tour</button> : <><button data-tour-action="pause" className="button button-secondary" onClick={snapshot.status === 'running' ? controller.pause : controller.resume}>{snapshot.status === 'running' ? 'Pause tour' : 'Resume tour'}</button><button className="button button-primary" onClick={controller.next}>{snapshot.step === TOUR_STEPS.length - 1 ? 'Finish tour' : 'Next tour step'}</button></>}<button className="text-button" onClick={exit}>Exit tour</button></div>
    <p className="tour-browse-note">Using a page control or normal navigation exits the tour. Hiding this tab pauses it. Timings describe presentation only.</p>
  </aside>;
}
