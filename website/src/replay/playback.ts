import type { BatchBudget, Round } from '../data/contracts.ts';
import type { RouteState } from '../state/route.ts';

export const REPLAY_DWELL_MS = 1400;

export interface ReplayStep {
  readonly patch: Partial<RouteState>;
  readonly phase: 'preview' | 'reveal';
}

/** Advance one saved batch phase. No inference, selection, or per-query refit runs here. */
export function nextReplayStep(state: RouteState, historyReady: boolean): ReplayStep | null {
  if (state.view !== 'replay' || state.mode !== 'seed' || !historyReady || state.budget >= 50) return null;
  const nextBatch = (state.budget / 10 + 1) as Round;
  if (state.batch !== nextBatch || state.revealed) {
    return { phase: 'preview', patch: { batch: nextBatch, revealed: false } };
  }
  return { phase: 'reveal', patch: { batch: nextBatch, budget: (state.budget + 10) as BatchBudget, revealed: true } };
}

export function replayPhaseLabel(state: RouteState, historyReady: boolean): string {
  if (state.mode === 'aggregate') return 'Aggregate overview · individual playback unavailable';
  if (!historyReady) return 'Loading saved query history';
  if (state.budget === 50) return 'All five batches revealed · 50 recorded queries';
  return `Batch ${state.batch} · ${state.revealed ? 'recorded outcomes revealed' : 'predictions only'}`;
}

export function replayNextLabel(state: RouteState, historyReady: boolean): string {
  const step = nextReplayStep(state, historyReady);
  if (!step) return state.budget === 50 ? 'Replay complete' : 'Next batch phase';
  return step.phase === 'preview' ? `Preview batch ${state.budget / 10 + 1}` : `Reveal batch ${state.batch}`;
}

export interface PlaybackClock {
  setTimeout(callback: () => void, delay: number): unknown;
  clearTimeout(handle: unknown): void;
}
export interface PlaybackOptions {
  readonly state: RouteState;
  readonly historyReady: boolean;
  readonly update: (patch: Partial<RouteState>, replace?: boolean) => void;
  readonly setPlaying: (playing: boolean) => void;
  readonly reset: () => void;
  readonly clock?: PlaybackClock;
  readonly dwellMs?: number;
}

function replayContext(state: RouteState): string {
  return [state.view, state.mode, state.seed, state.policy, state.policies.join(','), state.budget, state.batch, state.revealed].join('|');
}

/**
 * The browser hook and independent timer tests share this controller. The local
 * projection is updated before the route callback, so a synchronous route
 * cancellation can invalidate the epoch before another timeout is scheduled.
 */
export function createReplayPlayback(options: PlaybackOptions) {
  const clock = options.clock ?? {
    setTimeout: (callback: () => void, delay: number) => globalThis.setTimeout(callback, delay),
    clearTimeout: (handle: unknown) => globalThis.clearTimeout(handle as ReturnType<typeof setTimeout>),
  };
  const dwellMs = options.dwellMs ?? REPLAY_DWELL_MS;
  if (!Number.isFinite(dwellMs) || dwellMs <= 0) throw new Error('Replay dwell must be a positive finite duration.');
  let state = options.state;
  let ready = options.historyReady;
  let timer: unknown;
  let running = false;
  let epoch = 0;
  let disposed = false;

  function cancel() {
    epoch++;
    running = false;
    if (timer !== undefined) { clock.clearTimeout(timer); timer = undefined; }
  }
  function pause() { cancel(); options.setPlaying(false); }
  function applyStep(): boolean {
    const step = nextReplayStep(state, ready);
    if (!step) return false;
    state = { ...state, ...step.patch };
    // Every automatic phase replaces the current URL entry. Manual Next pushes
    // one explicit inspection state, while timer playback cannot flood history.
    options.update(step.patch, running);
    return true;
  }
  function schedule() {
    if (!running || disposed) return;
    const scheduledEpoch = epoch;
    timer = clock.setTimeout(() => {
      if (!running || disposed || scheduledEpoch !== epoch) return;
      timer = undefined;
      if (!applyStep() || state.budget === 50) { pause(); return; }
      if (running && scheduledEpoch === epoch) schedule();
    }, dwellMs);
  }

  return {
    /** Cancellation registration must be side-effect free with respect to route state. */
    cancel,
    play() {
      cancel();
      if (disposed || !nextReplayStep(state, ready)) { options.setPlaying(false); return; }
      running = true;
      options.setPlaying(true);
      schedule();
    },
    pause,
    next() {
      pause();
      if (!disposed) applyStep();
    },
    resetReplay() { pause(); if (!disposed) options.reset(); },
    /** Reconcile external selection, history, data availability and Pause. */
    sync(nextState: RouteState, historyReady: boolean, playing: boolean) {
      if (disposed) return;
      const interrupted = replayContext(nextState) !== replayContext(state) || !historyReady || !playing;
      const wasRunning = running;
      state = nextState;
      ready = historyReady;
      if (interrupted) {
        cancel();
        if (wasRunning) options.setPlaying(false);
      }
    },
    dispose() { cancel(); disposed = true; },
    getSnapshot: () => ({ state, running, pending: timer !== undefined, epoch, disposed }),
  };
}
