import { useEffect, useState } from 'react';

/** An anchor always downloads the exact current display projection. Suppress a
 * previous URL immediately during a reveal/rewind or selection change. */
export function useCsvDownload(text: string | null) {
  const [asset, setAsset] = useState<{ text: string; url: string; bytes: number } | null>(null);
  useEffect(() => {
    if (text === null) { setAsset(null); return; }
    const blob = new Blob(['\uFEFF', text], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    setAsset({ text, url, bytes: blob.size });
    return () => URL.revokeObjectURL(url);
  }, [text]);
  return text !== null && asset?.text === text ? asset : null;
}
