/** W4 renderer acceptance: the shipped frame owner, resource scope, camera and failure gate. */
const phase = process.argv.includes('--phase=CRYSTAL_LAB') ? 'CRYSTAL_LAB' : process.argv.includes('--phase=W6') ? 'W6' : 'W4';

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const moduleAt = name => import(pathToFileURL(path.join(website, 'src/crystal', name)));
const { createFrameOwner, createResourceScope, createFailureGate } = await moduleAt('lifecycle.ts');
const { fitDistanceForSphere } = await moduleAt('camera.ts');
const { cellCorners, fractionalToCartesian, geometryBounds, wrapFractional } = await moduleAt('geometry.ts');
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const checks = [];
function check(name, condition) { assert.ok(condition, name); checks.push({ check: name, passed: true }); }
function equal(name, actual, expected) { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); }
function fakeFrames(renderHook = () => {}) {
  let sequence = 0;
  const queued = new Map();
  const ever = [];
  const rendered = [], errors = [];
  const owner = createFrameOwner({
    requestFrame(callback) { const handle = ++sequence; queued.set(handle, callback); ever.push(callback); return handle; },
    cancelFrame(handle) { queued.delete(handle); },
    render(delta) { rendered.push(delta); renderHook(delta); },
    onError(error) { errors.push(error); },
  });
  return { owner, rendered, errors, queued,
    escaped: () => ever.at(-1),
    flush(time = 1000) { const callbacks = [...queued.values()]; queued.clear(); for (const callback of callbacks) callback(time); },
  };
}

const f = fakeFrames();
equal('Construction is idle: no requestAnimationFrame', f.queued.size, 0);
for (let i = 0; i < 20; i += 1) f.owner.invalidate();
equal('Concurrent invalidations coalesce to one frame', f.queued.size, 1);
f.flush();
equal('A demand-rendered frame leaves no idle loop', f.queued.size, 0);
equal('First frame starts with zero elapsed time', f.rendered, [0]);
f.owner.setContinuous(true);
for (let i = 0; i < 12; i += 1) {
  equal(`Auto-rotation frame ${i}: exactly one owner`, f.queued.size, 1);
  f.flush(2000 + i * 16);
}
const beforeOffscreen = f.rendered.length;
const offscreenEscape = f.escaped();
f.owner.setVisible(false);
equal('Off-screen transition cancels pending work', f.queued.size, 0);
offscreenEscape(4000);
equal('An already-queued off-screen callback is ignored', f.rendered.length, beforeOffscreen);
f.owner.invalidate();
equal('Off-screen invalidation cannot renew a loop', f.queued.size, 0);
f.owner.setVisible(true);
equal('Returning on-screen renews one active loop', f.queued.size, 1);
f.flush(5000);
equal('Resume time excludes the hidden interval', f.rendered.at(-1), 0);
const hiddenEscape = f.escaped();
const beforeHidden = f.rendered.length;
f.owner.setHidden(true);
equal('Document hiding cancels pending work', f.queued.size, 0);
hiddenEscape(6000);
equal('An already-queued hidden callback is ignored', f.rendered.length, beforeHidden);
f.owner.setVisible(false);
f.owner.setHidden(false);
equal('Visibility alone cannot resume an off-screen viewer', f.queued.size, 0);
f.owner.setContinuous(false);
f.owner.setVisible(true);
f.flush(7000);
equal('Returning idle viewers render once without auto-rotation', f.queued.size, 0);
f.owner.setContinuous(true);
f.flush(8000);
f.flush(18000);
equal('Long intervals are capped at 100 ms', f.rendered.at(-1), 0.1);
const disposedEscape = f.escaped();
const beforeDispose = f.rendered.length;
f.owner.dispose();
f.owner.dispose();
for (const action of [() => f.owner.invalidate(), () => f.owner.setVisible(true), () => f.owner.setHidden(false), () => f.owner.setContinuous(true)]) action();
disposedEscape(19000);
equal('Disposed viewers never render or schedule late work', [f.rendered.length, f.queued.size], [beforeDispose, 0]);
check('Disposed ownership status is explicit', f.owner.disposed);

for (let mount = 0; mount < 40; mount += 1) {
  const old = fakeFrames();
  old.owner.setContinuous(true);
  const escaped = old.escaped();
  old.owner.dispose();
  const replacement = fakeFrames();
  replacement.owner.invalidate();
  escaped(1000);
  replacement.flush(1000);
  equal(`StrictMode/replacement ${mount}: no old-frame render`, old.rendered.length, 0);
  equal(`StrictMode/replacement ${mount}: one replacement paint`, replacement.rendered.length, 1);
  replacement.owner.dispose();
}

const cleanupOrder = [];
const scope = createResourceScope();
scope.defer(() => cleanupOrder.push('first'));
scope.defer(() => { cleanupOrder.push('throwing'); throw new Error('deliberate cleanup failure'); });
scope.defer(() => cleanupOrder.push('last'));
equal('Cleanup exceptions are collected without stopping later resources', scope.dispose().length, 1);
equal('Resources clean up in reverse acquisition order', cleanupOrder, ['last', 'throwing', 'first']);
scope.dispose();
equal('Repeated scope disposal does not repeat resource releases', cleanupOrder.length, 3);
scope.defer(() => cleanupOrder.push('late resource'));
equal('A late acquisition on a disposed scope is released immediately', cleanupOrder.at(-1), 'late resource');

const gpuScope = createResourceScope();
const disposalEvents = [];
for (const [name, resource] of [['geometry', new THREE.SphereGeometry(1, 10, 8)], ['material', new THREE.MeshStandardMaterial()]]) {
  resource.addEventListener('dispose', () => disposalEvents.push(name));
  gpuScope.defer(() => resource.dispose());
}
const contextTarget = new EventTarget();
const fallbackReasons = [];
const fail = createFailureGate(() => gpuScope.dispose(), reason => fallbackReasons.push(reason));
const onContextLoss = event => fail('Context unavailable; show saved figure', event);
contextTarget.addEventListener('webglcontextlost', onContextLoss);
gpuScope.defer(() => contextTarget.removeEventListener('webglcontextlost', onContextLoss));
const loss = new Event('webglcontextlost', { cancelable: true });
contextTarget.dispatchEvent(loss);
check('Context-loss handler prevents browser default recovery', loss.defaultPrevented);
equal('Context loss releases actual Three geometry/material resources once', disposalEvents, ['material', 'geometry']);
equal('Context loss reports one saved-figure fallback', fallbackReasons.length, 1);
contextTarget.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
fail('A repeated construction/render error');
equal('Context handler and failure gate cannot report a second fallback', fallbackReasons.length, 1);

let failingOwner;
const failedFrames = new Map();
const renderFailureScope = createResourceScope();
const renderFailureReasons = [];
const failRender = createFailureGate(() => renderFailureScope.dispose(), reason => renderFailureReasons.push(reason));
failingOwner = createFrameOwner({
  requestFrame(callback) { failedFrames.set(1, callback); return 1; },
  cancelFrame(handle) { failedFrames.delete(handle); },
  render() { throw new Error('deliberate draw failure'); },
  onError() { failRender('Interactive render failed'); },
});
renderFailureScope.defer(() => failingOwner.dispose());
failingOwner.setContinuous(true);
const failedCallback = failedFrames.get(1);
failedFrames.clear();
failedCallback(0);
check('A draw exception disposes the owner', failingOwner.disposed);
equal('A draw exception requests the saved fallback exactly once', renderFailureReasons, ['Interactive render failed']);
equal('A draw exception leaves no repeating frame', failedFrames.size, 0);

// The installed controls are exercised without a DOM or GPU for camera semantics.
const controlCamera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
controlCamera.position.set(0, 0, 10);
const controls = new OrbitControls(controlCamera);
controls.enableDamping = false;
controls.saveState();
controls.dollyIn(1 / 1.2); controls.update();
check('Installed OrbitControls zoom-in convention actually decreases distance', controls.getDistance() < 10);
controls.dollyOut(1 / 1.2); controls.update();
check('Installed OrbitControls zoom-out restores the original distance', Math.abs(controls.getDistance() - 10) < 1e-12);
controls.rotateLeft(Math.PI / 12); controls.update();
check('Installed OrbitControls rotate method changes camera azimuth', Math.abs(controls.getAzimuthalAngle()) > 0.1);
controls.reset();
check('Installed OrbitControls reset restores the saved camera', controlCamera.position.distanceTo(new THREE.Vector3(0, 0, 10)) < 1e-12);

const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const manifestBytes = await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath));
equal('Viewer checks use the unchanged pinned research manifest', hash(manifestBytes), DATA_RELEASE.manifestSha256);
const manifest = JSON.parse(manifestBytes);
const stageEntries = manifest.files.filter(entry => /^structures\/.+\.json$/.test(entry.logicalName) && entry.logicalName !== 'structures/index.json');
const aspectRatios = [0.45, 0.65, 1, 1.5, 2.8];
for (const item of stageEntries) {
  const bytes = await fs.readFile(path.join(website, 'public/research', item.path));
  equal(`Saved stage bytes remain pinned: ${item.logicalName}`, hash(bytes), item.sha256);
  const stage = JSON.parse(bytes);
  const geometry = stage.geometry;
  const positions = geometry.fractionalCoordinates.map(fractional => fractionalToCartesian(wrapFractional(fractional, geometry.pbc), geometry.latticeRowsAngstrom));
  const bounds = geometryBounds(geometry.latticeRowsAngstrom, positions);
  const centre = new THREE.Vector3(...bounds.center);
  const direction = new THREE.Vector3(1.35, 1.05, 1.6).normalize();
  const points = [...cellCorners(geometry.latticeRowsAngstrom), ...positions];
  for (const aspect of aspectRatios) {
    const camera = new THREE.PerspectiveCamera(40, aspect, bounds.radius / 1000, bounds.radius * 100);
    camera.position.copy(centre).addScaledVector(direction, fitDistanceForSphere(bounds.radius, aspect));
    camera.lookAt(centre); camera.updateMatrixWorld(); camera.updateProjectionMatrix();
    check(`${stage.stageId}: cell and physical sites fit aspect ${aspect}`, points.every(point => {
      const projected = new THREE.Vector3(...point).project(camera);
      return Math.abs(projected.x) <= 1 && Math.abs(projected.y) <= 1 && projected.z >= -1 && projected.z <= 1;
    }));
  }
}
for (const args of [[0, 1], [1, 0], [1, -1], [NaN, 1], [1, 1, 180], [1, 1, 40, 0.8]]) {
  assert.throws(() => fitDistanceForSphere(...args));
  checks.push({ check: `Invalid camera fit rejected: ${args.join(',')}`, passed: true });
}

const realRendered = [];
const realOwner = createFrameOwner({
  requestFrame: callback => setTimeout(() => callback(performance.now()), 2),
  cancelFrame: handle => clearTimeout(handle),
  render: delta => realRendered.push(delta),
  onError: error => { throw error; },
});
realOwner.setContinuous(true);
await new Promise(resolve => setTimeout(resolve, 25));
check('The owner also renders through a real platform timer adapter', realRendered.length > 0);
realOwner.dispose();
const afterRealDispose = realRendered.length;
await new Promise(resolve => setTimeout(resolve, 25));
equal('A disposed real timer adapter produces no late render', realRendered.length, afterRealDispose);

const sources = {};
for (const relative of ['src/components/CrystalViewer.tsx', 'src/components/CrystalViewerControls.tsx', 'src/crystal/orientation.ts', 'src/crystal/controls.css', 'src/crystal/lifecycle.ts', 'src/crystal/camera.ts', 'src/crystal/viewer.css', 'scripts/verify-viewer.mjs']) {
  sources[relative] = hash(await fs.readFile(path.join(website, relative)));
}
const report = { phase, status: 'passed', generatedAt: new Date().toISOString(), checksPassed: checks.length,
  dataReleaseId: DATA_RELEASE.dataReleaseId, stageCount: stageEntries.length, testedAspectRatios: aspectRatios,
  scope: 'Shipped pure RAF owner, epoch cancellation, failure gate, reverse/idempotent resources, actual Three math/material disposal, saved-stage perspective fitting.',
  limitations: ['This Node check does not create a native WebGL context or prove GPU draw success. Browser QA records native renderer or saved-figure fallback separately.',
    'Native document visibility and intersection event delivery are checked in browser QA where supported; injected controller checks prove their frame-owner actions.'],
  sources, checks };
await fs.mkdir(path.join(website, 'reports'), { recursive: true });
await fs.writeFile(path.join(website, `reports/${phase}_VIEWER_VALIDATION.json`), JSON.stringify(report, null, 2) + '\n');
console.log(`${phase} viewer validation passed: ${checks.length} checks; ${stageEntries.length} saved stages; ${aspectRatios.length} viewport aspect ratios.`);
