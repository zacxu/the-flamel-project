import { useCsvDownload } from '../replay/useCsvDownload';

/** Uses the same immutable text as the currently displayed selection. */
export function TableDownload({ text, filename, label }: { text: string; filename: string; label: string }) {
  const asset = useCsvDownload(text);
  return asset ? <a className="button button-secondary" href={asset.url} download={filename}>{label}</a> : <span className="small-text" role="status">Preparing displayed CSV…</span>;
}
