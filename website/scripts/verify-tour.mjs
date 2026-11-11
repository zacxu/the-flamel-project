/** Exercise the actual presentation controller with a deterministic monotonic clock. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { TOUR_STEPS, TOUR_TOTAL_SECONDS, createTourController } = await import(pathToFileURL(path.join(root, 'src/tour/model.ts')));
const { DEFAULT_ROUTE, normalizeRoute } = await import(pathToFileURL(path.join(root, 'src/state/route.ts')));
const manifest = JSON.parse(await fs.readFile(path.join(root, 'public/research/manifest.json')));
const dataset = async name => JSON.parse(await fs.readFile(path.join(root, 'public/research', manifest.files.find(file => file.logicalName === name).path)));
const registry = await dataset('structures/index.json');
const dft = await dataset('dft.json');
const checks = [];
const check = (name, condition) => { assert.ok(condition, name); checks.push({ check: name, passed: true }); };
const equal = (name, actual, expected) => { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); };
function fixture() {
  let time = 0, id = 0; const timers = new Map(); const presented = []; const cancelled = [];
  const controller = createTourController({ now: () => time,
    schedule(callback) { const key = ++id; timers.set(key, { callback, due: time + 250 }); return key; },
    cancel(key) { if (timers.has(key)) cancelled.push(timers.get(key).callback); timers.delete(key); },
  }, scene => presented.push({ at: time, id: scene.id }));
  return { controller, presented, cancelled, timers, advance(ms) {
    const target = time + ms;
    while (timers.size) { const entry = [...timers].sort((a, b) => a[1].due - b[1].due)[0];
      if (entry[1].due > target) break; timers.delete(entry[0]); time = entry[1].due; entry[1].callback(); }
    time = target;
  }, setClock(ms) { time = ms; }, fireNext() { const entry = [...timers][0]; if (entry) { timers.delete(entry[0]); entry[1].callback(); } } };
}
equal('Exactly six required tour steps', TOUR_STEPS.length, 6);
equal('Required step durations remain 25/45/35/30/25/20 seconds', TOUR_STEPS.map(step => step.seconds), [25, 45, 35, 30, 25, 20]);
equal('Total script duration is exactly three minutes', TOUR_TOTAL_SECONDS, 180);
const scenes = TOUR_STEPS.flatMap(step => step.scenes);
equal('All scene identifiers are unique', new Set(scenes.map(scene => scene.id)).size, scenes.length);
for (const [index, step] of TOUR_STEPS.entries()) {
  equal(`Step ${index + 1} begins at offset zero`, step.scenes[0].at, 0);
  check(`Step ${index + 1} subscenes are ordered inside their exact duration`, step.scenes.every((scene, i) => scene.at >= 0 && scene.at < step.seconds && (!i || scene.at > step.scenes[i - 1].at)));
}
let state = DEFAULT_ROUTE;
for (const scene of scenes) {
  const example = scene.exampleId ? registry.coreExamples.find(item => item.id === scene.exampleId) : null;
  const candidate = example ? registry.candidates.find(item => item.candidateId === example.candidateId) : null;
  const stage = candidate ? registry.stages.find(item => item.candidateId === candidate.candidateId && item.stage === scene.stage) : null;
  if (scene.exampleId) { check(`${scene.id} resolves its actual core entity`, !!candidate); check(`${scene.id} resolves its requested saved stage`, !!stage); }
  const next = normalizeRoute({ ...state, ...scene.patch, view: scene.view,
    ...(candidate ? { candidateId: candidate.candidateId, stageId: stage.stageId } : {}) }, registry);
  equal(`${scene.id} route uses the exact requested view`, next.state.view, scene.view);
  check(`${scene.id} has no unavailable selection repair`, next.notices.every(notice => notice.startsWith('Reveal state')));
  state = next.state;
}
equal('Replay visits all five ten-query boundaries in one fixed split', scenes.filter(scene => /^replay-(ten|twenty|thirty|forty|fifty)$/.test(scene.id)).map(scene => scene.patch.budget), [10, 20, 30, 40, 50]);
check('Every split replay uses only Quality and Full', scenes.filter(scene => scene.view === 'replay' && scene.patch.mode === 'seed').every(scene => scene.patch.seed === 20261022 && scene.patch.policies.join(',') === 'quality,full'));
equal('The final replay shows five-split aggregate data', scenes.find(scene => scene.id === 'replay-aggregate').patch.mode, 'aggregate');
equal('Symmetry energy does not switch primary yield into the supplement', scenes.find(scene => scene.id === 'symmetry-energy').patch.scope, 'primary');
equal('Coverage demonstration uses the verified low/high Full splits', scenes.filter(scene => scene.id === 'uncertainty-low' || scene.id === 'uncertainty-high').map(scene => [scene.patch.seed, scene.patch.endpoint]), [[20261023, 'full'], [20261024, 'full']]);
equal('Selective risk demonstration returns to the complete population', scenes.filter(scene => scene.id === 'uncertainty-retain' || scene.id === 'uncertainty-all').map(scene => scene.patch.retainedFraction), [0.1, 1]);
check('Perturbation filter selects one real incomplete terminal-SCF record', dft.jobs.filter(job => job.role === 'perturbation').length === 1 && dft.jobs.filter(job => job.role === 'perturbation').every(job => job.terminalScfAccepted === false && job.energyEVPerAtom === null && job.maxForceEVPerAngstrom === null && job.maxFullStressKbar === null));
{
  const f = fixture(); equal('Tour never starts automatically', f.controller.getSnapshot().status, 'idle'); equal('Idle owns no timer', f.timers.size, 0);
  f.controller.start(); equal('Start presents the overview immediately', f.presented[0], { at: 0, id: 'idea' }); equal('Start owns one timer', f.timers.size, 1);
  const boundaries = [25, 70, 105, 135, 160, 180]; let elapsed = 0;
  for (const [i, boundary] of boundaries.entries()) {
    f.advance((boundary - elapsed) * 1000 - 250); equal(`Immediately before ${boundary}s the current step remains ${i + 1}`, f.controller.getSnapshot().step, i);
    f.advance(250); equal(`At exact ${boundary}s boundary the correct step/status is selected`, [f.controller.getSnapshot().step, f.controller.getSnapshot().status], i === 5 ? [5, 'complete'] : [i + 1, 'running']); elapsed = boundary;
  }
  equal('Complete walkthrough presents all scripted subscenes once', f.presented.map(item => item.id), scenes.map(scene => scene.id));
  equal('Completed tour owns no timer', f.timers.size, 0); f.advance(60_000); equal('Completion cannot continue changing the view', f.presented.length, scenes.length);
}
{
  const f = fixture(); f.controller.start(); f.advance(14_000); f.controller.pause(); const before = f.controller.getSnapshot(); const count = f.presented.length;
  equal('Pause removes the timer', f.timers.size, 0); f.advance(120_000); equal('Paused time does not advance presentation', f.controller.getSnapshot(), before);
  for (const callback of f.cancelled) callback(); equal('Cancelled/stale timer cannot present another scene', f.presented.length, count);
  f.controller.resume(); equal('Resume owns exactly one timer', f.timers.size, 1); f.advance(10_750); equal('Resume keeps the remaining original-step time', f.controller.getSnapshot().step, 0); f.advance(250); equal('Resume reaches the correct remaining boundary', f.controller.getSnapshot().step, 1);
  f.controller.pause(); f.controller.next(); equal('Next while paused selects next step at zero, still paused', [f.controller.getSnapshot().step, f.controller.getSnapshot().elapsed, f.controller.getSnapshot().status], [2, 0, 'paused']);
  equal('Manual paused navigation owns no timer', f.timers.size, 0); f.controller.previous(); equal('Previous restores exact previous step preset', f.controller.getSnapshot().scene.id, 'replay-zero');
  f.controller.resume(); f.controller.next(); equal('Next while running owns one fresh timer', f.timers.size, 1); f.controller.exit(); equal('Exit returns ordinary browsing to idle', f.controller.getSnapshot().status, 'idle'); equal('Exit cancels timer', f.timers.size, 0);
  const ended = f.presented.length; for (const callback of f.cancelled) callback(); equal('Exited tour cannot later overwrite ordinary browsing', f.presented.length, ended);
  f.controller.start(); f.controller.start(); equal('Repeated start owns only one timer', f.timers.size, 1); equal('Restart begins at overview', f.controller.getSnapshot().scene.id, 'idea'); f.controller.dispose(); equal('Disposal cleans all timers', f.timers.size, 0);
}
{
  const f = fixture(); f.controller.start(); for (let i = 0; i < 5; i++) f.controller.next(); equal('Five manual next commands reach step six', f.controller.getSnapshot().step, 5);
  f.controller.next(); equal('Last next command finishes presentation', f.controller.getSnapshot().status, 'complete'); equal('Manual finish cleans timers', f.timers.size, 0);
  f.controller.previous(); equal('Previous from completion allows paused rehearsal', f.controller.getSnapshot().status, 'paused');
  f.controller.exit(); f.controller.resume(); equal('Resume cannot implicitly start an exited tour', f.controller.getSnapshot().status, 'idle'); f.controller.next(); equal('Next cannot implicitly start an exited tour', f.controller.getSnapshot().status, 'idle');
}
{
  const f = fixture(); f.controller.start(); f.setClock(181_000); f.fireNext(); equal('A delayed callback safely reaches final completion', [f.controller.getSnapshot().step, f.controller.getSnapshot().status], [5, 'complete']); equal('Delayed completion selects the final evidence scene', f.controller.getSnapshot().scene.id, 'evidence-sources'); equal('Delayed completion leaves no stale timer', f.timers.size, 0);
}
const sources = ['src/tour/model.ts', 'src/tour/useTour.ts', 'src/tour/TourContext.tsx', 'src/tour/GuidedTour.tsx', 'src/App.tsx', 'src/views/Workflow.tsx', 'src/views/Replay.tsx', 'src/views/CrystalLab.tsx', 'src/views/Evidence.tsx', 'src/findings/GenerationFindings.tsx', 'src/components/CrystalViewer.tsx'];
const sourceFiles = await Promise.all(sources.map(async file => { const bytes = await fs.readFile(path.join(root, file)); return { path: file, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }; }));
await fs.writeFile(path.join(root, 'reports/W6_TOUR_VALIDATION.json'), JSON.stringify({ schemaVersion: 1, status: 'passed', checkedAt: new Date().toISOString(), checkCount: checks.length, steps: TOUR_STEPS.length, subscenes: scenes.length, totalSeconds: TOUR_TOTAL_SECONDS, scope: 'Actual pure controller, exact monotonic scheduling, cancellation, presets and saved structure/DFT joins. Browser rehearsal and visual/accessibility checks are recorded separately.', dataReleaseId: manifest.dataReleaseId, sourceFiles, checks }, null, 2) + '\n');
console.log(`W6 guided tour: ${checks.length} checks passed; six steps, ${scenes.length} subscenes, exactly 180 seconds.`);
