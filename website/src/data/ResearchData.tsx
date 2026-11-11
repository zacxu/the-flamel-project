import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type {
  ClaimsDataset, DatasetFor, GlossaryDataset, JsonLogicalName, MethodsDataset,
  ProvenanceDataset, ReplayCurves, StructureIndex, StudySummary, ThemeDataset,
} from './contracts.ts';
import { guardDataset } from './guards.ts';
import { ResearchRelease } from './loadRelease.ts';

export interface CoreData {
  readonly summary: StudySummary;
  readonly methods: MethodsDataset;
  readonly theme: ThemeDataset;
  readonly claims: ClaimsDataset;
  readonly glossary: GlossaryDataset;
  readonly provenance: ProvenanceDataset;
  readonly structures: StructureIndex;
  readonly curves: ReplayCurves;
}
export type ResearchStatus = 'loading' | 'ready' | 'error';
export type AssetStatus = ResearchStatus | 'unavailable';
export interface ResearchContextValue {
  readonly status: ResearchStatus;
  readonly data: CoreData | null;
  readonly error: string | null;
  readonly retry: () => void;
  readonly release: ResearchRelease;
}
const ResearchContext = createContext<ResearchContextValue | null>(null);

function freshRelease(): ResearchRelease {
  return new ResearchRelease(new URL(import.meta.env.BASE_URL, window.location.href));
}
function message(error: unknown): string {
  return error instanceof Error ? error.message : 'The recorded research data could not be verified.';
}
async function loadDataset<Name extends JsonLogicalName>(release: ResearchRelease, name: Name): Promise<DatasetFor<Name>> {
  return guardDataset(name, await release.dataset(name));
}
async function loadCore(release: ResearchRelease): Promise<CoreData> {
  // Only these eight compact datasets bootstrap the shell. Seed histories,
  // full uncertainty/DFT tables, and atomic geometry remain on-demand.
  const [summary, methods, theme, claims, glossary, provenance, structures, curves] = await Promise.all([
    loadDataset(release, 'summary.json'), loadDataset(release, 'methods.json'),
    loadDataset(release, 'theme.json'), loadDataset(release, 'claims.json'),
    loadDataset(release, 'glossary.json'), loadDataset(release, 'provenance.json'),
    loadDataset(release, 'structures/index.json'), loadDataset(release, 'replay/curves.json'),
  ]);
  const knownSources = new Set(provenance.sources.map((source) => source.sourceId));
  for (const sourceId of [summary.sourceIds, methods.sourceIds, curves.sourceIds,
    claims.claims.flatMap((claim) => claim.sourceIds)].flat()) {
    if (!knownSources.has(sourceId)) throw new Error('Research source identity is missing from this release.');
  }
  return { summary, methods, theme, claims, glossary, provenance, structures, curves };
}

export function ResearchProvider({ children }: { readonly children: ReactNode }) {
  const [attempt, setAttempt] = useState(0);
  const release = useMemo(() => freshRelease(), [attempt]);
  const [state, setState] = useState<Omit<ResearchContextValue, 'retry' | 'release'> & { forRelease: ResearchRelease }>({
    status: 'loading', data: null, error: null, forRelease: release,
  });
  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  useEffect(() => {
    let active = true;
    setState({ status: 'loading', data: null, error: null, forRelease: release });
    void loadCore(release).then((data) => {
      if (active) setState({ status: 'ready', data, error: null, forRelease: release });
    }).catch((error: unknown) => {
      if (active) setState({ status: 'error', data: null, error: message(error), forRelease: release });
    });
    return () => { active = false; };
  }, [release]);
  const value = useMemo<ResearchContextValue>(() => ({
    ...(state.forRelease === release ? state : { status: 'loading', data: null, error: null }), retry, release,
  }), [state, retry, release]);
  return <ResearchContext.Provider value={value}>{children}</ResearchContext.Provider>;
}

export function useResearch(): ResearchContextValue {
  const context = useContext(ResearchContext);
  if (context === null) throw new Error('Research hooks require ResearchProvider.');
  return context;
}

export interface DatasetState<Name extends JsonLogicalName> {
  readonly data: DatasetFor<Name> | null;
  readonly status: AssetStatus;
  readonly error: string | null;
  readonly retry: () => void;
}
export function useResearchDataset<Name extends JsonLogicalName>(name: Name | null): DatasetState<Name> {
  const { release: sharedRelease } = useResearch();
  const [attempt, setAttempt] = useState(0);
  const release = useMemo(() => attempt === 0 ? sharedRelease : freshRelease(), [sharedRelease, attempt]);
  const [state, setState] = useState<Omit<DatasetState<Name>, 'retry'> & { forName: Name | null; forRelease: ResearchRelease }>({
    data: null, status: name === null ? 'unavailable' : 'loading', error: null, forName: name, forRelease: release,
  });
  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  useEffect(() => {
    let active = true;
    if (name === null) {
      setState({ data: null, status: 'unavailable', error: null, forName: name, forRelease: release });
      return () => { active = false; };
    }
    setState({ data: null, status: 'loading', error: null, forName: name, forRelease: release });
    void loadDataset(release, name).then((data) => {
      if (active) setState({ data, status: 'ready', error: null, forName: name, forRelease: release });
    }).catch((error: unknown) => {
      if (active) setState({ data: null, status: 'error', error: message(error), forName: name, forRelease: release });
    });
    return () => { active = false; };
  }, [release, name]);
  if (name === null) return { data: null, status: 'unavailable', error: null, retry };
  if (state.forName !== name || state.forRelease !== release) return { data: null, status: 'loading', error: null, retry };
  return { ...state, retry };
}

export interface ResearchAssetState {
  readonly url: string | null;
  readonly status: AssetStatus;
  readonly error: string | null;
  readonly retry: () => void;
}
/** Images and downloads receive verified Blob URLs, never a mutable raw path.
 * Each effect owns its URL and revokes it on replacement/unmount. A request
 * resolving after cleanup creates no URL, including React StrictMode remounts. */
export function useResearchAsset(logicalName: string | null): ResearchAssetState {
  const { release: sharedRelease } = useResearch();
  const [attempt, setAttempt] = useState(0);
  const release = useMemo(() => attempt === 0 ? sharedRelease : freshRelease(), [sharedRelease, attempt]);
  const [state, setState] = useState<Omit<ResearchAssetState, 'retry'> & { forName: string | null; forRelease: ResearchRelease }>({
    url: null, status: logicalName === null ? 'unavailable' : 'loading', error: null, forName: logicalName, forRelease: release,
  });
  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  useEffect(() => {
    let active = true;
    let ownedUrl: string | null = null;
    if (logicalName === null) {
      setState({ url: null, status: 'unavailable', error: null, forName: logicalName, forRelease: release });
      return () => { active = false; };
    }
    setState({ url: null, status: 'loading', error: null, forName: logicalName, forRelease: release });
    void release.asset(logicalName).then((blob) => {
      if (!active) return;
      ownedUrl = URL.createObjectURL(blob);
      setState({ url: ownedUrl, status: 'ready', error: null, forName: logicalName, forRelease: release });
    }).catch((error: unknown) => {
      if (active) setState({ url: null, status: 'error', error: message(error), forName: logicalName, forRelease: release });
    });
    return () => {
      active = false;
      if (ownedUrl !== null) URL.revokeObjectURL(ownedUrl);
    };
  }, [release, logicalName]);
  if (logicalName === null) return { url: null, status: 'unavailable', error: null, retry };
  if (state.forName !== logicalName || state.forRelease !== release) return { url: null, status: 'loading', error: null, retry };
  return { ...state, retry };
}
