/** Compact canonical URLs: exercise shipped state code without replacing historical W2-W7 evidence. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { DEFAULT_ROUTE, VIEWS, POLICIES, SEEDS, BUDGETS, RETAINED_FRACTIONS,
  normalizeRoute, parseRoute, formatRoute, createRouteController } =
  await import(pathToFileURL(path.join(website, 'src/state/route.ts')));
const groups = {}, examples = {};
function equal(group, actual, expected, message) {
  assert.deepEqual(actual, expected, message);
  groups[group] = (groups[group] ?? 0) + 1;
}
function check(group, condition, message) { equal(group, Boolean(condition), true, message); }
function legacyHash(state) {
  const values = new URLSearchParams();
  for (const [key, value] of Object.entries(state)) if (key !== 'view')
    values.set(key, Array.isArray(value) ? value.join(',') : String(value));
  return `#/${state.view}?${values}`;
}
function roundtrip(group, state) {
  const compact = formatRoute(state), parsed = parseRoute(compact);
  equal(group, parsed.state, state, `Compact URL preserves ${compact}`);
  equal(group, parsed.notices, [], `Canonical URL has no repair notices: ${compact}`);
  equal(group, parsed.needsNormalization, false, `Compact URL is already canonical: ${compact}`);
  check(group, !compact.includes('revealed='), 'Derived reveal flag is absent');
  if (state.mode === 'aggregate') check(group, !compact.includes('batch='), 'Derived aggregate batch is absent');
  const legacy = parseRoute(legacyHash(state));
  equal(group, legacy.state, state, 'Previously shared full-state link retains its state');
  equal(group, legacy.canonicalHash, compact, 'Previously shared full-state link shortens to the same canonical URL');
}

equal('default sections', formatRoute(DEFAULT_ROUTE), '', 'Homepage has no fragment or parameters');
equal('default sections', parseRoute('').needsNormalization, false, 'Bare homepage needs no rewrite');
equal('default sections', parseRoute('#/overview').canonicalHash, '', 'Old homepage fragment shortens to the bare root');
for (const view of VIEWS) {
  const state = { ...DEFAULT_ROUTE, view };
  const expected = view === 'overview' ? '' : `#/${view}`;
  equal('default sections', formatRoute(state), expected, `${view} has a short section path`);
  examples[view] = expected;
  roundtrip('default sections', state);
}

const policySets = Array.from({ length: (1 << POLICIES.length) - 1 }, (_, index) =>
  POLICIES.filter((_, bit) => ((index + 1) & (1 << bit)) !== 0));
for (const policies of policySets) for (const policy of policies) for (const budget of BUDGETS) {
  roundtrip('aggregate policies and budgets', normalizeRoute({ ...DEFAULT_ROUTE, view: 'replay', policies, policy, budget }).state);
  for (const seed of SEEDS) for (const batch of [1, 2, 3, 4, 5]) {
    const state = normalizeRoute({ ...DEFAULT_ROUTE, view: 'replay', mode: 'seed', policies, policy, budget, seed, batch,
      revealed: undefined }).state;
    roundtrip('seed policies budgets and batches', state);
  }
}
const preview = normalizeRoute({ ...DEFAULT_ROUTE, view: 'replay', mode: 'seed', budget: 10, batch: 2,
  revealed: undefined }).state;
const completed = normalizeRoute({ ...preview, batch: 1, revealed: undefined }).state;
check('seed preview identity', formatRoute(preview) !== formatRoute(completed), 'Preview and completed batch remain distinguishable');
equal('seed preview identity', parseRoute(formatRoute(preview)).state.revealed, false, 'Preview keeps labels hidden after reload');
equal('seed preview identity', parseRoute(formatRoute(completed)).state.revealed, true, 'Completed batch keeps labels revealed after reload');
examples.replayPreview = formatRoute(preview);

for (const retainedFraction of RETAINED_FRACTIONS) for (const endpoint of [...POLICIES, 'initial_shared'])
  for (const scope of ['primary', 'supplementary'])
    roundtrip('findings selections', { ...DEFAULT_ROUTE, view: 'findings', retainedFraction, endpoint, scope });
const manifest = JSON.parse(await fs.readFile(path.join(website, 'public/research/manifest.json')));
const indexEntry = manifest.files.find(file => file.logicalName === 'structures/index.json');
const registry = JSON.parse(await fs.readFile(path.join(website, 'public/research', indexEntry.path)));
for (const candidate of registry.candidates) for (const stageId of candidate.stageIds) {
  const state = { ...DEFAULT_ROUTE, view: 'crystals', candidateId: candidate.candidateId, stageId };
  roundtrip('saved structures', state);
  equal('saved structures', parseRoute(formatRoute(state), registry).state, state,
    `Registry-bound candidate-stage selection survives: ${stageId}`);
}
for (const hash of ['#', '#/overview?mode=aggregate', '#/replay?seed=bad', '#/replay?budget=7',
  '#/replay?seed=20261023&seed=20261024', '#/unknown', '#/replay?admin=secret', '#/replay?policies=full,quality,full',
  '#/replay?mode=seed&budget=0&batch=5&revealed=true']) {
  const parsed = parseRoute(hash);
  equal('legacy and malformed normalization', parseRoute(parsed.canonicalHash).state, parsed.state, 'Normalized short link preserves repaired state');
  equal('legacy and malformed normalization', parseRoute(parsed.canonicalHash).needsNormalization, false, 'Normalization converges in one replacement');
}

function memoryHistory(initial = '') {
  let entries = [initial], index = 0;
  const listeners = new Set(), writes = [];
  const announce = () => { for (const listener of listeners) listener(); };
  return {
    readHash: () => entries[index],
    writeHash(hash, replace) { writes.push({ hash, replace });
      if (replace) entries[index] = hash;
      else { entries = entries.slice(0, index + 1); entries.push(hash); index++; } },
    listen(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    back() { if (index > 0) { index--; announce(); } },
    forward() { if (index < entries.length - 1) { index++; announce(); } },
    repeat: announce,
    get writes() { return writes; }, get entries() { return entries; },
  };
}
const history = memoryHistory(), controller = createRouteController(history), disconnect = controller.connect();
equal('history and controller', history.writes.length, 0, 'Default homepage does not rewrite the address');
for (const view of VIEWS.slice(1)) controller.navigate(view);
equal('history and controller', history.entries, ['', '#/workflow', '#/replay', '#/crystals', '#/findings', '#/evidence'],
  'Default navigation uses only short section paths');
history.back();
equal('history and controller', controller.getSnapshot().state.view, 'findings', 'Back restores short section route');
history.forward();
equal('history and controller', controller.getSnapshot().state.view, 'evidence', 'Forward restores short section route');
controller.navigate('replay', { mode: 'seed', budget: 10, batch: 2 });
controller.setPlaying(true);
let cancellations = 0;
const unregister = controller.registerCancellation(() => cancellations++);
history.back();
check('history and controller', cancellations > 0 && !controller.getSnapshot().playing, 'Back still cancels playback');
history.forward();
equal('history and controller', controller.getSnapshot().state, preview, 'Forward restores exact seed preview');
controller.reset();
equal('history and controller', history.readHash(), '', 'Reset returns to root URL');
equal('history and controller', controller.getSnapshot().state, DEFAULT_ROUTE, 'Reset restores full state');
unregister(); disconnect();

const oldHistory = memoryHistory(legacyHash(DEFAULT_ROUTE)), oldController = createRouteController(oldHistory);
const oldDisconnect = oldController.connect();
equal('history and controller', oldHistory.writes, [{ hash: '', replace: true }], 'Old default link is shortened in place');
equal('history and controller', oldHistory.entries.length, 1, 'Canonical shortening adds no back-button entry');
const before = oldController.getSnapshot();
oldHistory.repeat(); oldHistory.repeat();
check('history and controller', oldController.getSnapshot() === before, 'Duplicate native URL notifications keep stable state');
oldDisconnect();

const report = { status: 'passed', scope: 'Compact route serialization, old-link compatibility and history preservation',
  generatedAt: new Date().toISOString(), checksPassed: Object.values(groups).reduce((a, b) => a + b, 0), groups, examples,
  structureCandidates: registry.candidates.length, structureStages: registry.stages.length,
  researchChanged: false, historicalReportsOverwritten: false };
await fs.writeFile(path.join(website, 'reports/SHORT_URL_COMPACT_URL_VALIDATION.json'), JSON.stringify(report, null, 2) + '\n');
console.log(`Short URL verification passed: ${report.checksPassed} checks; old full-state links and compact links preserve the same selections.`);
