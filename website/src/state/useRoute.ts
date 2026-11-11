import { useEffect, useState, useSyncExternalStore } from 'react';
import { createRouteController, type RouteAdapter } from './route.ts';

function browserAdapter(): RouteAdapter {
  return {
    readHash: () => window.location.hash,
    writeHash(hash, replace) {
      const url = `${window.location.pathname}${window.location.search}${hash}`;
      if (replace) window.history.replaceState(null, '', url);
      else window.history.pushState(null, '', url);
    },
    listen(callback) {
      window.addEventListener('popstate', callback);
      window.addEventListener('hashchange', callback);
      return () => {
        window.removeEventListener('popstate', callback);
        window.removeEventListener('hashchange', callback);
      };
    },
  };
}

/** Persistent selections use history; playback and temporary drawers stay local. */
export function useRoute() {
  const [controller] = useState(() => createRouteController(browserAdapter()));
  const snapshot = useSyncExternalStore(controller.subscribe, controller.getSnapshot);
  useEffect(() => controller.connect(), [controller]);
  return { ...snapshot, update: controller.update, navigate: controller.navigate, reset: controller.reset,
    setPlaying: controller.setPlaying, registerCancellation: controller.registerCancellation,
    bindStructureIndex: controller.bindStructureIndex };
}
