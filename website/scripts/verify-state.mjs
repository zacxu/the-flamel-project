/** Exercise shipped route code, actual saved registry, history restoration and timer cancellation. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { DEFAULT_ROUTE, VIEWS, POLICIES, SEEDS, BUDGETS, RETAINED_FRACTIONS,
  parseRoute, formatRoute, normalizeCandidateSelection, createRouteController } =
  await import(pathToFileURL(path.join(website, 'src/state/route.ts')));
const checks = [];
function check(name, condition) { assert.ok(condition, name); checks.push({ check: name, passed: true }); }
function equal(name, actual, expected) { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); }
const manifest = JSON.parse(await fs.readFile(path.join(website, 'public/research/manifest.json')));
const registryEntry = manifest.files.find((file) => file.logicalName === 'structures/index.json');
const registry = JSON.parse(await fs.readFile(path.join(website, 'public/research', registryEntry.path)));

equal('Empty hash starts aggregate Quality versus Full at fifty queries', parseRoute('').state, DEFAULT_ROUTE);
check('Default route is canonical and round trips', !parseRoute(formatRoute(DEFAULT_ROUTE)).needsNormalization);
equal('All six paths are supported', VIEWS, ['overview', 'workflow', 'replay', 'crystals', 'findings', 'evidence']);
for (const view of VIEWS) {
  const route = parseRoute(formatRoute({ ...DEFAULT_ROUTE, view }));
  equal(`Reload preserves ${view}`, route.state.view, view);
  check(`Reload does not warn for valid ${view}`, route.notices.length === 0);
}
for (const malformed of ['#/missing', '#/overview/other', '#/replay#fragment', '#overview', 'https://example.org/#/replay']) {
  const parsed = parseRoute(malformed);
  equal(`Invalid path returns overview: ${malformed}`, parsed.state.view, 'overview');
  check(`Invalid path is explicit: ${malformed}`, parsed.notices.length > 0 && parsed.needsNormalization);
}
for (const [key, value, field, expected] of [
  ['mode', 'future', 'mode', 'aggregate'], ['seed', '20261027', 'seed', 20261022],
  ['seed', '2e7', 'seed', 20261022], ['seed', '0x13528ee', 'seed', 20261022],
  ['budget', '15', 'budget', 50], ['budget', '0.000001', 'budget', 50],
  ['budget', '-10', 'budget', 50], ['batch', '0', 'batch', 5],
  ['policy', 'oracle', 'policy', 'full'], ['endpoint', 'missing', 'endpoint', 'full'],
  ['scope', 'both', 'scope', 'primary'], ['retainedFraction', '0.35', 'retainedFraction', 1],
  ['retainedFraction', 'NaN', 'retainedFraction', 1], ['retainedFraction', '0', 'retainedFraction', 1],
  ['candidateId', '../../private', 'candidateId', DEFAULT_ROUTE.candidateId],
  ['stageId', '<script>', 'stageId', DEFAULT_ROUTE.stageId],
]) {
  const parsed = parseRoute(`#/overview?${new URLSearchParams({ [key]: value })}`);
  equal(`Invalid ${key}=${value} is bounded`, parsed.state[field], expected);
  check(`Invalid ${key}=${value} has a notice`, parsed.notices.length > 0);
}
equal('Empty policies restore comparison defaults', parseRoute('#/replay?policies=').state.policies, ['quality', 'full']);
equal('Duplicate policies are unique in documented order', parseRoute('#/replay?policies=full,quality,full').state.policies, ['quality', 'full']);
equal('Inspected policy follows a visible policy', parseRoute('#/replay?policies=random&policy=full').state.policy, 'random');
equal('Ambiguous duplicate parameters reset rather than choose an arbitrary seed', parseRoute('#/replay?seed=20261023&seed=20261024').state.seed, 20261022);
check('Unknown parameters are removed', !parseRoute('#/replay?admin=secret').canonicalHash.includes('admin'));
equal('Stored initial-shared uncertainty endpoint remains selectable', parseRoute('#/findings?endpoint=initial_shared').state.endpoint, 'initial_shared');
for (const retained of RETAINED_FRACTIONS) equal(`Saved retained fraction ${retained} survives reload`,
  parseRoute(`#/findings?retainedFraction=${retained}`).state.retainedFraction, retained);

for (const seed of SEEDS) for (const policy of POLICIES) for (const budget of BUDGETS) {
  const inspectedBatch = Math.min(5, Math.floor(budget / 10) + 1);
  const params = new URLSearchParams({ mode: 'seed', seed: String(seed), policies: policy, policy,
    budget: String(budget), batch: String(inspectedBatch), revealed: 'true' });
  const parsed = parseRoute(`#/replay?${params}`);
  equal(`Recorded replay identity ${seed}/${policy}/${budget}`, [parsed.state.seed, parsed.state.policy, parsed.state.budget], [seed, policy, budget]);
  check(`Unrevealed next batch cannot disclose labels ${seed}/${policy}/${budget}`,
    parsed.state.revealed === (budget === 50));
  equal(`Canonical seed reload ${seed}/${policy}/${budget}`, parseRoute(parsed.canonicalHash).state, parsed.state);
}
const completed = parseRoute('#/replay?mode=seed&budget=20&batch=1&revealed=false');
check('Previously completed first batch is explicitly revealed', completed.state.revealed && completed.state.batch === 1);
const future = parseRoute('#/replay?mode=seed&budget=0&batch=5&revealed=true');
check('Future batch request clamps to first saved predictions with labels hidden', future.state.batch === 1 && !future.state.revealed);
for (const budget of BUDGETS) {
  const aggregate = parseRoute(`#/replay?mode=aggregate&budget=${budget}&batch=1&revealed=true`).state;
  check(`Aggregate ${budget} has no revealed event history`, !aggregate.revealed);
}
for (const candidate of registry.candidates) for (const stageId of candidate.stageIds) {
  const state = { ...DEFAULT_ROUTE, view: 'crystals', candidateId: candidate.candidateId, stageId };
  equal(`Recorded candidate/stage pair ${stageId} survives reload`, parseRoute(formatRoute(state), registry).state, state);
}
const otherCandidate = registry.candidates.find((candidate) => candidate.candidateId !== DEFAULT_ROUTE.candidateId);
const mismatch = normalizeCandidateSelection({ ...DEFAULT_ROUTE, candidateId: otherCandidate.candidateId }, registry);
equal('A candidate never inherits the unrelated MgO DFT stage', mismatch.state.stageId, otherCandidate.defaultStageId);
check('Candidate/stage mismatch is disclosed', mismatch.notices.length > 0);
equal('Unknown candidate resets to the documented real MgO example',
  normalizeCandidateSelection({ ...DEFAULT_ROUTE, candidateId: 'unrecorded' }, registry).state.candidateId, DEFAULT_ROUTE.candidateId);
const twoAtomReference = registry.candidates.find((candidate) => candidate.candidateId === 'qe_source_reference_mgo_mp1265');
check('Real two-atom reference exists for independent identity check', twoAtomReference?.actualAtoms === 2);
equal('Two-atom source reference cannot masquerade as eight-atom continuation',
  normalizeCandidateSelection({ ...DEFAULT_ROUTE, stageId: twoAtomReference.defaultStageId }, registry).state.stageId, DEFAULT_ROUTE.stageId);

function memoryHistory(initial = '') {
  let entries = [initial], index = 0;
  const listeners = new Set();
  const writes = [];
  const announce = () => { for (const callback of listeners) callback(); };
  return {
    readHash: () => entries[index],
    writeHash(hash, replace) {
      writes.push({ hash, replace });
      if (replace) entries[index] = hash;
      else { entries = entries.slice(0, index + 1); entries.push(hash); index++; }
    },
    listen(callback) { listeners.add(callback); return () => listeners.delete(callback); },
    back() { if (index) { index--; announce(); } },
    forward() { if (index < entries.length - 1) { index++; announce(); } },
    visit(hash) { entries = entries.slice(0, index + 1); entries.push(hash); index++; announce(); },
    repeatNativeNotification: announce,
    get entries() { return [...entries]; }, get writes() { return [...writes]; },
    get listenerCount() { return listeners.size; },
  };
}
const history = memoryHistory();
const controller = createRouteController(history);
const disconnect = controller.connect();
equal('Default homepage keeps one entry without rewriting the address', [history.entries.length, history.writes.length], [1, 0]);
equal('Playback starts paused', controller.getSnapshot().playing, false);
controller.setPlaying(true);
equal('Aggregate playback cannot start', controller.getSnapshot().playing, false);
controller.navigate('replay', { mode: 'seed', seed: 20261024, budget: 0, batch: 1 });
const first = history.readHash();
controller.update({ budget: 10, batch: 2 });
const second = history.readHash();
check('State transitions create separate meaningful history entries', first !== second && history.entries.length === 3);
history.back();
equal('Back restores the prior seed and completed budget', [controller.getSnapshot().state.seed, controller.getSnapshot().state.budget], [20261024, 0]);
history.forward();
equal('Forward restores the exact later recorded boundary', controller.getSnapshot().state.budget, 10);
const previousEntries = history.entries.length;
controller.update({ retainedFraction: 0.7 }, true);
equal('Replace update avoids adding history entries', history.entries.length, previousEntries);
controller.bindStructureIndex(registry);
controller.update({ candidateId: otherCandidate.candidateId });
equal('Bound registry repairs later local candidate/stage updates', controller.getSnapshot().state.stageId, otherCandidate.defaultStageId);
history.visit('#/crystals?candidateId=unrecorded&stageId=made-up&seed=20261026');
equal('Direct unknown links are normalized once in place', controller.getSnapshot().state.candidateId, DEFAULT_ROUTE.candidateId);
check('Direct unknown links show a scoped notice', Boolean(controller.getSnapshot().routeNotice));
equal('Normalized browser entry matches controller state', parseRoute(history.readHash(), registry).state, controller.getSnapshot().state);
const repairNotice = controller.getSnapshot().routeNotice;
controller.bindStructureIndex(registry);
equal('Asynchronous source-registry validation retains repaired-link explanation', controller.getSnapshot().routeNotice, repairNotice);
history.visit('#/crystals?candidateId=qe_source_reference_mgo_mp1265&stageId=phase1_mgo_attempt_000--accepted_dft&budget=7&seed=invalid');
const nativeRepairNotice = controller.getSnapshot().routeNotice;
check('Native malformed navigation explains budget, seed and mismatched-stage repair',
  nativeRepairNotice?.includes('query budget') && nativeRepairNotice.includes('seed') && nativeRepairNotice.includes('stage'));
equal('Native malformed navigation selects the actual two-atom reference stage',
  controller.getSnapshot().state.stageId, twoAtomReference.defaultStageId);
const nativeRepairSnapshot = controller.getSnapshot();
history.repeatNativeNotification();
history.repeatNativeNotification();
equal('Duplicate popstate/hashchange notifications preserve the complete repaired-link notice',
  controller.getSnapshot().routeNotice, nativeRepairNotice);
check('Duplicate canonical notifications keep a stable state snapshot', controller.getSnapshot() === nativeRepairSnapshot);
history.visit(formatRoute({ ...controller.getSnapshot().state, view: 'workflow' }));
equal('A meaningfully different valid native navigation clears the old warning', controller.getSnapshot().routeNotice, null);
history.visit('#/crystals?budget=7');
check('A subsequent malformed native navigation creates a new notice', Boolean(controller.getSnapshot().routeNotice));
controller.update({ view: 'overview' });
equal('An ordinary valid local update clears a repaired-link notice', controller.getSnapshot().routeNotice, null);
controller.reset();
equal('Full reset restores every persistent field', controller.getSnapshot().state, DEFAULT_ROUTE);
equal('Full reset clears warnings and pauses', [controller.getSnapshot().routeNotice, controller.getSnapshot().playing], [null, false]);

let staleAdvances = 0, cancellationCalls = 0;
let timer;
const unregister = controller.registerCancellation(() => { cancellationCalls++; clearTimeout(timer); });
for (const [label, patch] of [
  ['view', { view: 'workflow' }], ['mode', { mode: 'aggregate' }],
  ['seed', { seed: 20261025 }], ['inspected policy', { policy: 'quality' }],
]) {
  controller.navigate('replay', { mode: 'seed', seed: 20261024, policy: 'full', policies: ['quality', 'full'], budget: 0, batch: 1 });
  controller.setPlaying(true);
  check(`Playback may be prepared for seed mode before ${label} change`, controller.getSnapshot().playing);
  timer = setTimeout(() => staleAdvances++, 20);
  const before = cancellationCalls;
  controller.update(patch);
  check(`${label} change cancels timers and pauses`, cancellationCalls > before && !controller.getSnapshot().playing);
  await new Promise((resolve) => setTimeout(resolve, 30));
}
equal('No cancelled callback advances a stale route', staleAdvances, 0);
controller.navigate('replay', { mode: 'seed', budget: 40, batch: 5 });
controller.setPlaying(true);
controller.update({ budget: 50, batch: 5 });
check('Reaching the final boundary pauses playback', !controller.getSnapshot().playing);
controller.update({ budget: 0, batch: 1 });
controller.setPlaying(true);
timer = setTimeout(() => staleAdvances++, 20);
history.back();
check('Browser navigation cancels even when only a saved batch differs', !controller.getSnapshot().playing);
await new Promise((resolve) => setTimeout(resolve, 30));
equal('No callback survives browser navigation', staleAdvances, 0);
controller.navigate('replay', { mode: 'seed', budget: 0, batch: 1 });
controller.setPlaying(true);
timer = setTimeout(() => staleAdvances++, 20);
controller.reset();
check('Reset cancels current timers and pauses', !controller.getSnapshot().playing);
await new Promise((resolve) => setTimeout(resolve, 30));
equal('No callback survives reset', staleAdvances, 0);
unregister();
let remainingCleanup = 0;
const removeBroken = controller.registerCancellation(() => { throw new Error('intentional cleanup fault'); });
const removeHealthy = controller.registerCancellation(() => remainingCleanup++);
controller.reset();
check('One cleanup fault does not skip other timer cancellations', remainingCleanup === 1);
removeBroken(); removeHealthy();
let notifications = 0;
const unsubscribe = controller.subscribe(() => notifications++);
const sameSnapshot = controller.getSnapshot();
controller.update({ view: 'overview' });
check('Canonical no-op retains a stable external-store snapshot', controller.getSnapshot() === sameSnapshot && notifications === 0);
unsubscribe();
disconnect();
equal('Unmount disconnects browser listeners', history.listenerCount, 0);
const reconnect = controller.connect();
equal('Strict-mode effect remount reconnects only one listener', history.listenerCount, 1);
reconnect();
const invalidHistory = memoryHistory('#/unknown?seed=bad');
const strictController = createRouteController(invalidHistory);
const firstDisconnect = strictController.connect();
const initialNotice = strictController.getSnapshot().routeNotice;
firstDisconnect();
const secondDisconnect = strictController.connect();
equal('Strict-mode reconnect retains the initial invalid-link explanation', strictController.getSnapshot().routeNotice, initialNotice);
secondDisconnect();
const asyncHistory = memoryHistory('#/crystals?candidateId=qe_source_reference_mgo_mp1265&stageId=phase1_mgo_attempt_000--accepted_dft&budget=7&seed=invalid');
const asyncController = createRouteController(asyncHistory);
const asyncDisconnect = asyncController.connect();
const beforeCatalogNotice = asyncController.getSnapshot().routeNotice;
check('Initial malformed link explains scalar repairs before the catalog arrives',
  beforeCatalogNotice?.includes('query budget') && beforeCatalogNotice.includes('seed'));
asyncController.bindStructureIndex(registry);
const afterCatalogNotice = asyncController.getSnapshot().routeNotice;
check('Async registry binding adds stage repair without removing initial scalar explanations',
  afterCatalogNotice?.includes('query budget') && afterCatalogNotice.includes('seed') && afterCatalogNotice.includes('stage'));
equal('Async binding repairs the exact initial candidate-stage mismatch', asyncController.getSnapshot().state.stageId, twoAtomReference.defaultStageId);
asyncHistory.repeatNativeNotification();
asyncHistory.repeatNativeNotification();
equal('Queued native notifications retain combined initial and catalog repair explanations',
  asyncController.getSnapshot().routeNotice, afterCatalogNotice);
asyncDisconnect();

const phase = process.argv.includes('--phase=SHORT_URL') ? 'SHORT_URL' : process.argv.includes('--phase=W6') ? 'W6' : process.argv.includes('--phase=W5') ? 'W5' : process.argv.includes('--phase=W4') ? 'W4' : process.argv.includes('--phase=W3') ? 'W3' : 'W2';
const report = { phase, scope: 'Shared route state, actual candidate registry, history and cancellation',
  status: 'passed', generatedAt: new Date().toISOString(), checksPassed: checks.length,
  actualSavedStagesChecked: registry.stages.length, actualSavedCandidatesChecked: registry.candidates.length,
  newResearchExperiments: 0, checks };
await fs.mkdir(path.join(website, 'reports'), { recursive: true });
await fs.writeFile(path.join(website, `reports/${phase}_STATE_VALIDATION.json`), JSON.stringify(report, null, 2) + '\n');
console.log(`${phase} shared-state verification passed: ${checks.length} checks; actual saved registry and history/timer transitions verified.`);
