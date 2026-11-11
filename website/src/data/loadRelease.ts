import { DATA_RELEASE } from './release.ts';

/** Small runtime guard at the public-data boundary; detailed scientific checks
 * run offline in validate_export.py before any UI build. */
type FileEntry = Readonly<{
  logicalName: string; path: string; sha256: string; bytes: number; mediaType: string;
}>;
type PinnedManifest = Readonly<{
  schemaVersion: number; studyId: string; dataReleaseId: string;
  generatedAt: string; studyFrozenAt: string | null;
  sourceInventorySha256: string; files: readonly FileEntry[];
}>;

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

async function verifiedBytes(url: URL, expectedHash: string, expectedBytes?: number): Promise<Uint8Array<ArrayBuffer>> {
  const response = await fetch(url, { cache: 'force-cache', credentials: 'same-origin' });
  if (!response.ok) throw new Error(`Research data unavailable (HTTP ${response.status}).`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (expectedBytes !== undefined && bytes.byteLength !== expectedBytes) throw new Error('Research file size mismatch.');
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)))
    .map((part) => part.toString(16).padStart(2, '0')).join('');
  if (hash !== expectedHash) throw new Error('Research file integrity mismatch. Reload the complete release.');
  return bytes;
}

export class ResearchRelease {
  private readonly root: URL;
  private pendingManifest?: Promise<PinnedManifest>;
  private readonly datasets = new Map<string, Promise<unknown>>();

  /** Pass the same-origin application base URL, including its trailing slash.
   * W2 supplies new URL(import.meta.env.BASE_URL, window.location.href). */
  constructor(applicationBaseUrl: URL) {
    this.root = new URL('research/', applicationBaseUrl);
  }

  manifest(): Promise<PinnedManifest> {
    this.pendingManifest ??= this.loadManifest();
    return this.pendingManifest;
  }

  private async loadManifest(): Promise<PinnedManifest> {
    const url = new URL(DATA_RELEASE.manifestPath.replace(/^research\//, ''), this.root);
    const bytes = await verifiedBytes(url, DATA_RELEASE.manifestSha256);
    const value: unknown = JSON.parse(new TextDecoder().decode(bytes));
    if (!object(value) || value.schemaVersion !== DATA_RELEASE.schemaVersion ||
      value.studyId !== DATA_RELEASE.studyId || value.dataReleaseId !== DATA_RELEASE.dataReleaseId ||
      !Array.isArray(value.files) || typeof value.generatedAt !== 'string' ||
      !(value.studyFrozenAt === null || typeof value.studyFrozenAt === 'string') ||
      typeof value.sourceInventorySha256 !== 'string') throw new Error('Unsupported research manifest.');
    const seen = new Set<string>();
    for (const entry of value.files) {
      if (!object(entry) || typeof entry.logicalName !== 'string' || typeof entry.path !== 'string' ||
        typeof entry.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(entry.sha256) ||
        typeof entry.bytes !== 'number' || !Number.isSafeInteger(entry.bytes) || entry.bytes < 0 ||
        typeof entry.mediaType !== 'string' || entry.path.includes('..') || entry.path.includes('\\') ||
        !entry.path.startsWith(`releases/${DATA_RELEASE.dataReleaseId}/`) || seen.has(entry.logicalName)) {
        throw new Error('Invalid research manifest file entry.');
      }
      const fileUrl = new URL(entry.path, this.root);
      if (fileUrl.origin !== this.root.origin || !fileUrl.pathname.startsWith(this.root.pathname)) {
        throw new Error('Research assets must stay within the same-origin release.');
      }
      seen.add(entry.logicalName);
    }
    return value as PinnedManifest;
  }

  async file(logicalName: string): Promise<FileEntry> {
    const manifest = await this.manifest();
    const entry = manifest.files.find((file) => file.logicalName === logicalName);
    if (!entry) throw new Error(`Research file is unavailable: ${logicalName}`);
    return entry;
  }

  /** Verify before rendering/downloading an image or text asset. */
  async asset(logicalName: string): Promise<Blob> {
    const entry = await this.file(logicalName);
    const bytes = await verifiedBytes(new URL(entry.path, this.root), entry.sha256, entry.bytes);
    return new Blob([bytes], { type: entry.mediaType });
  }

  /** Returns unknown deliberately: views must narrow to their typed contract. */
  dataset(logicalName: string): Promise<unknown> {
    let pending = this.datasets.get(logicalName);
    if (!pending) {
      pending = this.loadDataset(logicalName);
      this.datasets.set(logicalName, pending);
    }
    return pending;
  }

  private async loadDataset(logicalName: string): Promise<unknown> {
    const entry = await this.file(logicalName);
    if (entry.mediaType !== 'application/json') throw new Error('Requested asset is not a JSON dataset.');
    const bytes = await verifiedBytes(new URL(entry.path, this.root), entry.sha256, entry.bytes);
    const value: unknown = JSON.parse(new TextDecoder().decode(bytes));
    if (!object(value) || value.schemaVersion !== DATA_RELEASE.schemaVersion ||
      value.studyId !== DATA_RELEASE.studyId || value.dataset !== logicalName.replace(/\.json$/, '')) {
      throw new Error('Research dataset identity mismatch.');
    }
    return value;
  }
}
