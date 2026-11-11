import { useEffect, useRef } from 'react';
import type { RouteState } from '../state/route.ts';
import { createReplayPlayback, nextReplayStep, replayNextLabel, replayPhaseLabel } from './playback.ts';

export interface ReplayPlaybackConfig {
  readonly state: RouteState;
  readonly playing: boolean;
  readonly setPlaying: (playing: boolean) => void;
  readonly update: (patch: Partial<RouteState>, replace?: boolean) => void;
  readonly registerCancellation: (callback: () => void) => () => void;
  readonly historyReady: boolean;
  readonly reset: () => void;
}

/** One timer owner, registered with the application's existing route controller. */
export function useReplayPlayback(config: ReplayPlaybackConfig) {
  const latest = useRef(config);
  latest.current = config;
  const controllerRef = useRef<ReturnType<typeof createReplayPlayback> | null>(null);
  if (controllerRef.current === null) controllerRef.current = createReplayPlayback({
    state: config.state, historyReady: config.historyReady,
    update: (patch, replace) => latest.current.update(patch, replace),
    setPlaying: playing => latest.current.setPlaying(playing),
    reset: () => latest.current.reset(),
  });
  const controller = controllerRef.current;

  useEffect(() => {
    controller.sync(config.state, config.historyReady, config.playing);
  }, [controller, config.state, config.historyReady, config.playing]);

  useEffect(() => {
    const unregister = config.registerCancellation(controller.cancel);
    const pauseWhenHidden = () => { if (document.hidden) controller.pause(); };
    document.addEventListener('visibilitychange', pauseWhenHidden);
    return () => {
      unregister();
      document.removeEventListener('visibilitychange', pauseWhenHidden);
      // Strict Mode reconnects effects on the same mounted controller. Cancel
      // instead of disposing, so the reconnected instance remains usable.
      controller.cancel();
    };
  }, [controller, config.registerCancellation]);

  const available = nextReplayStep(config.state, config.historyReady) !== null;
  return {
    play: controller.play, pause: controller.pause, next: controller.next, resetReplay: controller.resetReplay,
    canPlay: available, canNext: available,
    phaseLabel: replayPhaseLabel(config.state, config.historyReady),
    nextLabel: replayNextLabel(config.state, config.historyReady),
  };
}
