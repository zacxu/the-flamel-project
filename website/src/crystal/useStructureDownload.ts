import { useEffect, useMemo, useState } from 'react';
import type { SavedStage } from '../data/contracts';
import { DATA_RELEASE } from '../data/release';
import { structureCif } from './geometry';

export function useStructureDownload(record: SavedStage | null) {
  const text = useMemo(() => record ? structureCif(record, DATA_RELEASE.dataReleaseId) : null, [record]);
  const [asset, setAsset] = useState<{ text: string; url: string } | null>(null);
  useEffect(() => {
    if (text === null) { setAsset(null); return; }
    const url = URL.createObjectURL(new Blob([text], { type: 'chemical/x-cif;charset=utf-8' }));
    setAsset({ text, url });
    return () => URL.revokeObjectURL(url);
  }, [text]);
  return text !== null && asset?.text === text ? asset : null;
}
