import type { BatchBudget, EvaluationPolicy, Policy, ReplaySeed, Round, StructureIndex } from '../data/contracts.ts';

export type View = 'overview' | 'workflow' | 'replay' | 'crystals' | 'findings' | 'evidence';
export interface RouteState {
  readonly view: View;
  readonly mode: 'aggregate' | 'seed';
  readonly seed: ReplaySeed;
  readonly policies: readonly Policy[];
  readonly policy: Policy;
  /** Number of completed, revealed historical queries, at recorded boundaries. */
  readonly budget: BatchBudget;
  readonly batch: Round;
  readonly revealed: boolean;
  readonly candidateId: string;
  readonly stageId: string;
  readonly scope: 'primary' | 'supplementary';
  readonly endpoint: EvaluationPolicy;
  readonly retainedFraction: number;
}
export const VIEWS: readonly View[] = ['overview', 'workflow', 'replay', 'crystals', 'findings', 'evidence'];
export const POLICIES: readonly Policy[] = ['quality', 'full', 'quality_diversity', 'random', 'uncertainty'];
export const SEEDS: readonly ReplaySeed[] = [20261022, 20261023, 20261024, 20261025, 20261026];
export const BUDGETS: readonly BatchBudget[] = [0, 10, 20, 30, 40, 50];
export const RETAINED_FRACTIONS: readonly number[] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];
export const DEFAULT_ROUTE: RouteState = Object.freeze({
  view: 'overview', mode: 'aggregate', seed: 20261022,
  policies: Object.freeze(['quality', 'full'] as Policy[]), policy: 'full',
  budget: 50, batch: 5, revealed: false,
  candidateId: 'phase1_mgo_attempt_000', stageId: 'phase1_mgo_attempt_000--accepted_dft',
  scope: 'primary', endpoint: 'full', retainedFraction: 1,
});
type StructureRegistry = Pick<StructureIndex, 'candidates' | 'stages'>;
export interface NormalizedRoute { readonly state: RouteState; readonly notices: readonly string[] }
export interface ParsedRoute extends NormalizedRoute { readonly canonicalHash: string; readonly needsNormalization: boolean }
type UnknownRoute = Partial<Record<keyof RouteState, unknown>>;
const ownKeys = ['view', 'mode', 'seed', 'policies', 'policy', 'budget', 'batch', 'revealed',
  'candidateId', 'stageId', 'scope', 'endpoint', 'retainedFraction'] as const;
const idPattern = /^[A-Za-z0-9_.:-]{1,180}$/;

function member<T extends string | number>(value: unknown, choices: readonly T[], fallback: T,
  name: string, notices: string[]): T {
  if (choices.includes(value as T)) return value as T;
  if (value !== undefined) notices.push(`The ${name} selection was unavailable and was reset.`);
  return fallback;
}
function numeric(value: unknown): unknown {
  // Reject blanks, exponent notation, hexadecimal and lossy integer parsing.
  return typeof value === 'string' && /^\d+(?:\.\d+)?$/.test(value) ? Number(value) : value;
}
function safeId(value: unknown, fallback: string, name: string, notices: string[]): string {
  if (typeof value === 'string' && idPattern.test(value)) return value;
  if (value !== undefined) notices.push(`The ${name} identifier was invalid and was reset.`);
  return fallback;
}

/** Pure validation shared by URL parsing, local updates and history restoration. */
export function normalizeRoute(raw: UnknownRoute, registry?: StructureRegistry): NormalizedRoute {
  const notices: string[] = [];
  const view = member(raw.view, VIEWS, DEFAULT_ROUTE.view, 'view', notices);
  const mode = member(raw.mode, ['aggregate', 'seed'] as const, DEFAULT_ROUTE.mode, 'mode', notices);
  const seed = member(numeric(raw.seed), SEEDS, DEFAULT_ROUTE.seed, 'seed', notices);
  let policies = Array.isArray(raw.policies) ? raw.policies : typeof raw.policies === 'string' ? raw.policies.split(',') : undefined;
  if (policies === undefined) policies = [...DEFAULT_ROUTE.policies];
  else if (policies.length === 0 || policies.some((value) => !POLICIES.includes(value as Policy))) {
    notices.push('The visible policy selection was unavailable and was reset.');
    policies = [...DEFAULT_ROUTE.policies];
  }
  const selectedPolicies = POLICIES.filter((policy) => policies.includes(policy));
  if (policies.length !== selectedPolicies.length) notices.push('Repeated policies were removed.');
  let policy = member(raw.policy, POLICIES, DEFAULT_ROUTE.policy, 'inspected policy', notices);
  if (!selectedPolicies.includes(policy)) {
    policy = selectedPolicies[0];
    notices.push('The inspected policy was changed to a visible policy.');
  }
  const budget = member(numeric(raw.budget), BUDGETS, DEFAULT_ROUTE.budget, 'query budget', notices);
  let batch = member(numeric(raw.batch), [1, 2, 3, 4, 5] as const, DEFAULT_ROUTE.batch, 'batch', notices);
  let revealed: boolean;
  if (mode === 'aggregate') {
    batch = Math.max(1, budget / 10) as Round;
    revealed = false;
  } else {
    const latestInspectable = Math.min(5, budget / 10 + 1) as Round;
    if (batch > latestInspectable) {
      batch = latestInspectable;
      notices.push('The inspected batch was moved to the next recorded batch.');
    }
    revealed = batch * 10 <= budget;
  }
  const requestedReveal = raw.revealed === 'true' ? true : raw.revealed === 'false' ? false : raw.revealed;
  if (requestedReveal !== undefined && requestedReveal !== revealed) {
    notices.push('Reveal state was aligned with the completed query budget and replay mode.');
  }
  const state: RouteState = {
    view, mode, seed, policies: Object.freeze(selectedPolicies), policy, budget, batch, revealed,
    candidateId: safeId(raw.candidateId, DEFAULT_ROUTE.candidateId, 'candidate', notices),
    stageId: safeId(raw.stageId, DEFAULT_ROUTE.stageId, 'stage', notices),
    scope: member(raw.scope, ['primary', 'supplementary'] as const, DEFAULT_ROUTE.scope, 'cohort scope', notices),
    endpoint: member(raw.endpoint, [...POLICIES, 'initial_shared'], DEFAULT_ROUTE.endpoint, 'uncertainty endpoint', notices),
    retainedFraction: member(numeric(raw.retainedFraction), RETAINED_FRACTIONS, DEFAULT_ROUTE.retainedFraction, 'retained fraction', notices),
  };
  if (!registry) return { state, notices };
  const candidate = normalizeCandidateSelection(state, registry);
  return { state: candidate.state, notices: [...notices, ...candidate.notices] };
}

/** Bind identifiers to the actual saved registry; never invent an unavailable later stage. */
export function normalizeCandidateSelection(state: RouteState, registry: StructureRegistry): NormalizedRoute {
  const notices: string[] = [];
  let candidate = registry.candidates.find((item) => item.candidateId === state.candidateId);
  if (!candidate) {
    candidate = registry.candidates.find((item) => item.candidateId === DEFAULT_ROUTE.candidateId) ?? registry.candidates[0];
    if (!candidate) return { state, notices: ['The saved structure catalog is unavailable; structure selection is disabled.'] };
    notices.push('The candidate was unavailable; a saved catalog example was selected.');
  }
  const recorded = (stageId: string) => candidate.stageIds.includes(stageId) &&
    registry.stages.some((stage) => stage.stageId === stageId && stage.candidateId === candidate.candidateId);
  let stageId = state.stageId;
  if (!recorded(stageId)) {
    stageId = recorded(candidate.defaultStageId) ? candidate.defaultStageId : candidate.stageIds.find(recorded) ?? '';
    notices.push(stageId ? 'The stage did not belong to this candidate; its saved default stage was selected.' :
      'This candidate has no available saved stage.');
  }
  if (candidate.candidateId === state.candidateId && stageId === state.stageId) return { state, notices };
  return { state: { ...state, candidateId: candidate.candidateId, stageId }, notices };
}

export function formatRoute(state: RouteState): string {
  const values = new URLSearchParams();
  for (const key of ownKeys) {
    // Defaults are restored by the parser; these two values are derived there.
    if (key === 'view' || key === 'revealed' || (key === 'batch' && state.mode === 'aggregate')) continue;
    const value = state[key];
    const encoded = Array.isArray(value) ? value.join(',') : String(value);
    const fallback = DEFAULT_ROUTE[key];
    const defaultEncoded = Array.isArray(fallback) ? fallback.join(',') : String(fallback);
    if (encoded !== defaultEncoded) values.set(key, encoded);
  }
  const query = values.toString();
  if (state.view === 'overview' && !query) return '';
  return `#/${state.view}${query ? `?${query}` : ''}`;
}

export function parseRoute(hash: string, registry?: StructureRegistry): ParsedRoute {
  const notices: string[] = [];
  const raw: UnknownRoute = {};
  if (hash && hash !== '#') {
    const match = /^#\/([^/?#]+)(?:\?([^#]*))?$/.exec(hash);
    if (!match) notices.push('The link format was invalid and the default view was selected.');
    else {
      raw.view = match[1];
      const params = new URLSearchParams(match[2] ?? '');
      for (const [key, value] of params) {
        if (key === 'view' || !ownKeys.includes(key as keyof RouteState)) {
          notices.push('An unrecognized link parameter was removed.');
        } else if (params.getAll(key).length !== 1) {
          notices.push('An ambiguous repeated link parameter was reset.');
        } else raw[key as keyof RouteState] = value;
      }
    }
  }
  const normalized = normalizeRoute(raw, registry);
  const canonicalHash = formatRoute(normalized.state);
  return { ...normalized, notices: [...new Set([...notices, ...normalized.notices])], canonicalHash,
    needsNormalization: hash !== canonicalHash };
}

export interface RouteAdapter {
  readHash(): string;
  writeHash(hash: string, replace: boolean): void;
  listen(callback: () => void): () => void;
}
export interface RouteSnapshot {
  readonly state: RouteState;
  readonly routeNotice: string | null;
  readonly playing: boolean;
}
/** One controller is shared by the React hook and the independent history/timer tests. */
export function createRouteController(adapter: RouteAdapter) {
  let registry: StructureRegistry | undefined;
  const initial = parseRoute(adapter.readHash());
  let snapshot: RouteSnapshot = { state: initial.state, routeNotice: initial.notices.join(' ') || null, playing: false };
  const listeners = new Set<() => void>();
  const cancellations = new Set<() => void>();
  let unlisten: (() => void) | undefined;
  const emit = () => { for (const listener of listeners) listener(); };
  const cancel = () => {
    for (const callback of cancellations) {
      // One broken cleanup must not leave other playback timers running.
      try { callback(); } catch { /* Each registered cleanup is still attempted. */ }
    }
  };
  const contextChanged = (before: RouteState, after: RouteState) =>
    before.view !== after.view || before.mode !== after.mode || before.seed !== after.seed || before.policy !== after.policy;
  function commit(next: NormalizedRoute, write: 'push' | 'replace' | 'external', forceCancel = false) {
    const interrupted = forceCancel || contextChanged(snapshot.state, next.state) ||
      (snapshot.playing && next.state.budget === 50);
    if (interrupted) cancel();
    const notice = next.notices.join(' ') || null;
    const playing = interrupted ? false : snapshot.playing;
    const changed = formatRoute(snapshot.state) !== formatRoute(next.state) || snapshot.routeNotice !== notice || snapshot.playing !== playing;
    if (changed) snapshot = { state: next.state, routeNotice: notice, playing };
    if (write !== 'external') {
      const hash = formatRoute(next.state);
      if (hash !== adapter.readHash()) adapter.writeHash(hash, write === 'replace');
    }
    if (changed) emit();
  }
  function restore() {
    const parsed = parseRoute(adapter.readHash(), registry);
    if (parsed.needsNormalization) adapter.writeHash(parsed.canonicalHash, true);
    // Native hash navigation can notify both popstate and hashchange. The
    // second notification sees our repaired canonical hash; it must not erase
    // the explanation produced by the first event. A genuinely different
    // valid route still clears the previous notice.
    const duplicateCanonicalState = !parsed.notices.length &&
      parsed.canonicalHash === formatRoute(snapshot.state);
    const notices = duplicateCanonicalState && snapshot.routeNotice ? [snapshot.routeNotice] : parsed.notices;
    // Browser navigation always cancels timers, even when only a recorded batch changes.
    commit({ state: parsed.state, notices }, 'external', true);
  }
  function update(patch: Partial<RouteState>, replace = false) {
    const raw: UnknownRoute = { ...snapshot.state, ...patch };
    // Derived reveal changes during ordinary navigation are expected, not malformed links.
    if (!Object.hasOwn(patch, 'revealed')) delete raw.revealed;
    commit(normalizeRoute(raw, registry), replace ? 'replace' : 'push');
  }
  return {
    getSnapshot: () => snapshot,
    subscribe(callback: () => void) { listeners.add(callback); return () => { listeners.delete(callback); }; },
    connect() {
      if (!unlisten) unlisten = adapter.listen(restore);
      const parsed = parseRoute(adapter.readHash(), registry);
      if (parsed.needsNormalization) adapter.writeHash(parsed.canonicalHash, true);
      // Strict-mode effect reconnection must not erase the explanation of a repaired link.
      const sameCanonicalState = parsed.canonicalHash === formatRoute(snapshot.state);
      const notices = !parsed.notices.length && sameCanonicalState && snapshot.routeNotice ? [snapshot.routeNotice] : parsed.notices;
      commit({ state: parsed.state, notices }, 'external');
      return () => {
        unlisten?.(); unlisten = undefined; cancel();
        if (snapshot.playing) { snapshot = { ...snapshot, playing: false }; emit(); }
      };
    },
    update,
    navigate(view: View, patch: Partial<RouteState> = {}) { update({ ...patch, view }); },
    reset() { commit({ state: DEFAULT_ROUTE, notices: [] }, 'push', true); },
    setPlaying(playing: boolean) {
      const allowed = playing && snapshot.state.mode === 'seed' && snapshot.state.budget < 50;
      if (!allowed && snapshot.playing) cancel();
      if (snapshot.playing !== allowed) { snapshot = { ...snapshot, playing: allowed }; emit(); }
    },
    registerCancellation(callback: () => void) { cancellations.add(callback); return () => { cancellations.delete(callback); }; },
    bindStructureIndex(index: StructureRegistry) {
      registry = index;
      const next = normalizeRoute(snapshot.state, registry);
      // Asynchronous catalog arrival should retain an earlier malformed-link notice.
      const notices = snapshot.routeNotice ? [...new Set([snapshot.routeNotice, ...next.notices])] : next.notices;
      commit({ state: next.state, notices }, 'replace');
    },
  };
}
