import { useEffect, useState } from 'react';
import { UI_FIGURES } from '../generated/uiFigures';
import { useResearchAsset, type ResearchAssetState } from './ResearchData';

/** Optional pixel-identical presentation copy; evidence originals stay pinned.
 * A failed or hash-mismatched copy falls back through the research loader. */
export function usePresentationAsset(logicalName: string | null): ResearchAssetState {
  const derivative = logicalName ? UI_FIGURES[logicalName] : undefined;
  const key = derivative?.sha256 ?? null;
  const [state, setState] = useState<{ key: string | null; url: string | null; failed: boolean }>({ key: null, url: null, failed: false });
  const [attempt, setAttempt] = useState(0);
  const current = state.key === key ? state : { key, url: null, failed: false };
  const original = useResearchAsset(!derivative || current.failed ? logicalName : null);
  useEffect(() => {
    if (!derivative) return;
    const controller = new AbortController();
    let ownedUrl: string | null = null;
    let active = true;
    setState({ key, url: null, failed: false });
    void (async () => {
      const base = new URL(import.meta.env.BASE_URL, window.location.href);
      const response = await fetch(new URL(derivative.path, base), { credentials: 'same-origin', cache: 'force-cache', signal: controller.signal });
      if (!response.ok) throw new Error('Presentation image unavailable');
      const bytes = await response.arrayBuffer();
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
      if (digest !== derivative.sha256 || bytes.byteLength !== derivative.bytes) throw new Error('Presentation image integrity mismatch');
      if (!active) return;
      ownedUrl = URL.createObjectURL(new Blob([bytes], { type: 'image/webp' }));
      setState({ key, url: ownedUrl, failed: false });
    })().catch(() => { if (active) setState({ key, url: null, failed: true }); });
    return () => { active = false; controller.abort(); if (ownedUrl) URL.revokeObjectURL(ownedUrl); };
  }, [derivative, key, attempt]);
  if (!derivative || current.failed) return original;
  return { url: current.url, status: current.url ? 'ready' : 'loading', error: null,
    retry: () => setAttempt(value => value + 1) };
}
