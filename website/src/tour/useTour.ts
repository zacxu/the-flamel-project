import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { createTourController, type TourScene } from './model';

export function useTour(present: (scene: TourScene) => void, stopPlayback: () => void) {
  const callback = useRef(present); callback.current = present;
  const stop = useRef(stopPlayback); stop.current = stopPlayback;
  const [controller] = useState(() => createTourController({
    now: () => performance.now(), schedule: callback => window.setTimeout(callback, 250),
    cancel: handle => window.clearTimeout(handle as number),
  }, scene => { stop.current(); callback.current(scene); }));
  const snapshot = useSyncExternalStore(controller.subscribe, controller.getSnapshot);
  useEffect(() => {
    const visibility = () => { if (document.hidden) controller.pause(); };
    const history = () => controller.exit();
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('popstate', history); window.addEventListener('hashchange', history);
    return () => { document.removeEventListener('visibilitychange', visibility); window.removeEventListener('popstate', history); window.removeEventListener('hashchange', history); controller.exit(); };
  }, [controller]);
  return { ...snapshot, controller };
}
