/** Real shipped controller + route adapter: exhaustive playback and timer cleanup. */
const phase = process.argv.includes('--phase=W6') ? 'W6' : 'W3';

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { DEFAULT_ROUTE, SEEDS, POLICIES, formatRoute, createRouteController } =
  await import(pathToFileURL(path.join(website, 'src/state/route.ts')));
const { createReplayPlayback, nextReplayStep, replayNextLabel, replayPhaseLabel, REPLAY_DWELL_MS } =
  await import(pathToFileURL(path.join(website, 'src/replay/playback.ts')));
const checks = [];
function check(name, condition) { assert.ok(condition, name); checks.push({ check: name, passed: true }); }
function equal(name, actual, expected) { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); }
function fakeClock() {
  let now = 0, sequence = 0;
  const timers = new Map(), callbacks = [];
  return {
    setTimeout(callback, delay) { const id = ++sequence; timers.set(id, { callback, due: now + delay }); callbacks.push(callback); return id; },
    clearTimeout(id) { timers.delete(id); },
    advance(ms) {
      const target = now + ms;
      let limit = 100;
      while (limit--) {
        const next = [...timers.entries()].filter(([, timer]) => timer.due <= target).sort((a, b) => a[1].due - b[1].due || a[0] - b[0])[0];
        if (!next) { now = target; return; }
        now = next[1].due; timers.delete(next[0]); next[1].callback();
      }
      throw new Error('Timer loop exceeded safety bound');
    },
    pending: () => timers.size,
    escaped: () => callbacks.at(-1),
  };
}
function fixture(initial = {}, clock = fakeClock(), options = {}) {
  let hash = formatRoute({ ...DEFAULT_ROUTE, view: 'replay', mode: 'seed', budget: 0, batch: 1, revealed: false, ...initial });
  let listener;
  const writes = [], updates = [];
  const route = createRouteController({ readHash: () => hash,
    writeHash(value, replace) { hash = value; writes.push({ hash, replace }); },
    listen(callback) { listener = callback; return () => { listener = undefined; }; },
  });
  let historyReady = options.historyReady ?? true;
  const disconnect = route.connect();
  const playback = createReplayPlayback({ state: route.getSnapshot().state, historyReady, clock,
    dwellMs: options.dwellMs,
    update(patch, replace) { updates.push({ patch, replace }); route.update(patch, replace); options.onUpdate?.(patch); },
    setPlaying: route.setPlaying,
    reset: route.reset,
  });
  const unregister = route.registerCancellation(playback.cancel);
  const unsubscribe = route.subscribe(() => { const snapshot = route.getSnapshot(); playback.sync(snapshot.state, historyReady, snapshot.playing); });
  return { route, playback, clock, writes, updates,
    external(patch) { hash = formatRoute({ ...route.getSnapshot().state, ...patch }); listener?.(); },
    ready(value) { historyReady = value; const snapshot = route.getSnapshot(); playback.sync(snapshot.state, historyReady, snapshot.playing); },
    destroy() { unregister(); unsubscribe(); playback.dispose(); disconnect(); },
  };
}

equal('Human-readable recorded phase dwell is 1.4 seconds', REPLAY_DWELL_MS, 1400);
for (const seed of SEEDS) for (const policy of POLICIES) {
  const f = fixture({ seed, policy, policies: [policy] });
  const tag = `${seed}/${policy}`;
  f.playback.play();
  check(`${tag}: starts playing saved history`, f.route.getSnapshot().playing && f.clock.pending() === 1);
  f.clock.advance(REPLAY_DWELL_MS - 1);
  equal(`${tag}: predictions dwell before first label reveal`, f.route.getSnapshot().state.budget, 0);
  for (let batch = 1; batch <= 5; batch++) {
    f.clock.advance(batch === 1 ? 1 : REPLAY_DWELL_MS);
    const revealed = f.route.getSnapshot().state;
    equal(`${tag}: exactly ten recorded labels reveal in batch ${batch}`, [revealed.budget, revealed.batch, revealed.revealed], [batch * 10, batch, true]);
    if (batch < 5) {
      f.clock.advance(REPLAY_DWELL_MS);
      const preview = f.route.getSnapshot().state;
      equal(`${tag}: next preview retains completed budget after batch ${batch}`, [preview.budget, preview.batch, preview.revealed], [batch * 10, batch + 1, false]);
    }
  }
  equal(`${tag}: five reveals and four previews, never per-query refits`, f.updates.length, 9);
  check(`${tag}: complete means paused with no pending timer`, !f.route.getSnapshot().playing && f.clock.pending() === 0);
  check(`${tag}: automated phases replace history entries`, f.updates.every(update => update.replace === true));
  const finalHash = f.writes.at(-1)?.hash;
  f.clock.advance(REPLAY_DWELL_MS * 10);
  equal(`${tag}: no sixth batch after completion`, [f.updates.length, f.writes.at(-1)?.hash], [9, finalHash]);
  f.playback.play();
  equal(`${tag}: complete history cannot autoplay again`, [f.clock.pending(), f.route.getSnapshot().playing], [0, false]);
  f.destroy();
}

for (const [name, interrupt] of [
  ['Pause', f => f.playback.pause()],
  ['view change', f => f.route.navigate('findings')],
  ['aggregate mode', f => f.route.update({ mode: 'aggregate' })],
  ['seed switch', f => f.route.update({ seed: 20261023 })],
  ['inspected policy switch', f => f.route.update({ policy: 'quality' })],
  ['policy comparison change', f => f.route.update({ policies: ['full'] })],
  ['manual budget change', f => f.route.update({ budget: 20 })],
  ['manual batch change', f => { f.playback.next(); f.route.update({ batch: 1 }); }],
  ['browser history event', f => f.external({ budget: 10 })],
  ['hidden browser document pause', f => f.playback.pause()],
  ['history data loss', f => f.ready(false)],
  ['full Reset', f => f.playback.resetReplay()],
  ['unmount', f => f.destroy()],
]) {
  const f = fixture();
  f.playback.play();
  const staleCallback = f.clock.escaped();
  interrupt(f);
  const count = f.updates.length;
  check(`${name}: all pending timers cancelled`, f.clock.pending() === 0);
  staleCallback(); // Already queued browser callback must also be harmless.
  f.clock.advance(REPLAY_DWELL_MS * 10);
  equal(`${name}: no queued or later advances after interruption`, f.updates.length, count);
  check(`${name}: local playback flag is false`, !f.playback.getSnapshot().running);
  if (name !== 'unmount') f.destroy();
}

const manual = fixture();
manual.playback.next();
equal('Manual Next reveals first ten labels', [manual.route.getSnapshot().state.budget, manual.route.getSnapshot().state.revealed], [10, true]);
manual.playback.next();
equal('Manual Next then previews next batch without extra labels', [manual.route.getSnapshot().state.budget, manual.route.getSnapshot().state.batch, manual.route.getSnapshot().state.revealed], [10, 2, false]);
check('Manual Next creates explicit history entries', manual.updates.every(update => update.replace === false));
equal('Next label distinguishes hidden labels', replayNextLabel(manual.route.getSnapshot().state, true), 'Reveal batch 2');
manual.route.update({ budget: 30, batch: 1 });
manual.playback.next();
equal('Inspecting an older batch resumes at first unrevealed batch', [manual.route.getSnapshot().state.budget, manual.route.getSnapshot().state.batch, manual.route.getSnapshot().state.revealed], [30, 4, false]);
manual.playback.next();
equal('Resumed preview reveals next ten labels once', manual.route.getSnapshot().state.budget, 40);
manual.playback.resetReplay();
equal('Replay Reset restores the complete documented route defaults', manual.route.getSnapshot().state, DEFAULT_ROUTE);
manual.destroy();

for (const state of [
  { ...DEFAULT_ROUTE, view: 'replay' },
  { ...DEFAULT_ROUTE, view: 'replay', mode: 'seed' },
  { ...DEFAULT_ROUTE, view: 'findings', mode: 'seed', budget: 0, batch: 1, revealed: false },
]) equal(`Unavailable replay does not mutate ${state.view}/${state.mode}/${state.budget}`, nextReplayStep(state, true), null);
const notReady = fixture({}, fakeClock(), { historyReady: false });
notReady.playback.play(); notReady.playback.next();
equal('Missing or incomplete histories cannot advance', [notReady.updates.length, notReady.clock.pending()], [0, 0]);
equal('Loading state is explicit', replayPhaseLabel(notReady.route.getSnapshot().state, false), 'Loading saved query history');
notReady.ready(true);
equal('Data arrival does not autoplay without explicit Play', notReady.clock.pending(), 0);
notReady.playback.play();
equal('Explicit Play starts after history arrival', notReady.clock.pending(), 1);
notReady.destroy();

const racing = fixture();
racing.playback.play();
const stale = racing.clock.escaped();
racing.playback.pause(); racing.playback.play();
stale();
equal('Stale callback cannot clear a newer timer handle', [racing.clock.pending(), racing.playback.getSnapshot().pending], [1, true]);
racing.playback.pause();
equal('New timer remains cancellable after stale callback', racing.clock.pending(), 0);
racing.destroy();

// Exercise actual platform timers, not only a fake scheduler. Pause occurs from
// inside the first real route update, proving re-entrant cancellation is safe.
let real;
const actualClock = { setTimeout: (callback, delay) => setTimeout(callback, delay), clearTimeout: handle => clearTimeout(handle) };
real = fixture({}, actualClock, { dwellMs: 15, onUpdate: () => real.playback.pause() });
real.playback.play();
await new Promise(resolve => setTimeout(resolve, 85));
equal('Actual timer reveals exactly one batch before inline Pause', [real.updates.length, real.route.getSnapshot().state.budget], [1, 10]);
check('Actual timer is paused without a dangling handle', !real.playback.getSnapshot().running && !real.playback.getSnapshot().pending && !real.route.getSnapshot().playing);
real.destroy();

const report = { phase, status: 'passed', completedAt: new Date().toISOString(),
  checks: checks.length, failures: 0, historiesExercised: 25, automaticPhasesPerHistory: 9,
  platformTimerCancellationVerified: true, newScientificExperiments: 0, results: checks };
await fs.mkdir(path.join(website, 'reports'), { recursive: true });
await fs.writeFile(path.join(website, `reports/${phase}_PLAYBACK_VALIDATION.json`), `${JSON.stringify(report, null, 2)}\n`);
console.log(`${phase} playback: ${checks.length} checks passed; 25 histories, deterministic batching and actual timer cancellation.`);
