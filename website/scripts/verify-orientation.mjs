/** Targeted saved-cell orientation checks; no renderer, new physical sites or historical report writes. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as THREE from 'three';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const modulePath = path.join(website, 'src/crystal/orientation.ts');
const { makeLatticeAxes, latticeViewDirection, latticeViewUp, cartesianOrientationAxes } = await import(pathToFileURL(modulePath));
const checks = [];
const check = (name, condition) => { assert.ok(condition, name); checks.push({ check: name, passed: true }); };
const equal = (name, actual, expected) => { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); };
const near = (name, actual, expected, tolerance = 1e-10) => check(name, Math.abs(actual - expected) <= tolerance);
const vectorNear = (name, actual, expected) => check(name, actual.distanceTo(new THREE.Vector3(...expected)) <= 1e-10);

const fixtures = [
  { name: 'orthogonal', rows: [[4, 0, 0], [0, 5, 0], [0, 0, 6]] },
  { name: 'skew', rows: [[3, 0, 0], [1.7, 2.8, 0], [0.8, -0.4, 4.2]] },
  { name: 'permuted and signed', rows: [[0, 0, -4], [5, 0, 0], [0, -6, 0]] },
  { name: 'near parallel', rows: [[1, 0, 0], [0.99, 0.01, 0], [0, 0, 1]] },
];
for (const fixture of fixtures) {
  const before = JSON.stringify(fixture.rows);
  let labelDisposed = 0, geometryDisposed = 0, materialDisposed = 0, textureDisposed = 0;
  const labelFactory = () => {
    const texture = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
    texture.addEventListener('dispose', () => { textureDisposed++; });
    const material = new THREE.SpriteMaterial({ map: texture });
    material.addEventListener('dispose', () => { materialDisposed++; });
    return { sprite: new THREE.Sprite(material), dispose() { labelDisposed++; texture.dispose(); material.dispose(); } };
  };
  const axes = makeLatticeAxes(fixture.rows, labelFactory);
  equal(`${fixture.name}: exactly three shafts, three arrowheads and three labels`, axes.group.children.length, 9);
  axes.group.traverse(object => {
    if (object.isMesh) {
      object.geometry.addEventListener('dispose', () => { geometryDisposed++; });
      if (!object.name.includes('arrowhead')) object.material.addEventListener('dispose', () => { materialDisposed++; });
    }
  });
  axes.group.updateMatrixWorld(true);
  ['a', 'b', 'c'].forEach((label, index) => {
    const row = new THREE.Vector3(...fixture.rows[index]);
    const direction = latticeViewDirection(label, fixture.rows);
    vectorNear(`${fixture.name}: +${label} camera direction follows ROW ${index}`, direction, row.clone().normalize().toArray());
    const up = latticeViewUp(direction);
    near(`${fixture.name}: ${label} robust camera up is unit length`, up.length(), 1);
    near(`${fixture.name}: ${label} robust camera up is perpendicular`, up.dot(direction), 0);
    check(`${fixture.name}: ${label} camera up is finite`, up.toArray().every(Number.isFinite));
    const shaft = axes.group.getObjectByName(`${label} lattice shaft`);
    const head = axes.group.getObjectByName(`${label} lattice arrowhead`);
    const labelSprite = axes.group.getObjectByName(`${label} saved lattice vector`);
    const shaftHeight = shaft.geometry.parameters.height;
    const headHeight = head.geometry.parameters.height;
    vectorNear(`${fixture.name}: ${label} shaft begins at saved origin`, shaft.localToWorld(new THREE.Vector3(0, -shaftHeight / 2, 0)), [0, 0, 0]);
    const shaftEnd = shaft.localToWorld(new THREE.Vector3(0, shaftHeight / 2, 0));
    const headStart = head.localToWorld(new THREE.Vector3(0, -headHeight / 2, 0));
    near(`${fixture.name}: ${label} shaft and arrowhead meet`, shaftEnd.distanceTo(headStart), 0);
    vectorNear(`${fixture.name}: ${label} arrow tip is the exact saved row endpoint`, head.localToWorld(new THREE.Vector3(0, headHeight / 2, 0)), fixture.rows[index]);
    near(`${fixture.name}: ${label} label stays collinear with saved vector`, labelSprite.position.clone().cross(row).length(), 0);
    check(`${fixture.name}: ${label} label follows the positive vector endpoint`, labelSprite.position.dot(direction) > row.length());
  });
  equal(`${fixture.name}: source lattice is not mutated`, JSON.stringify(fixture.rows), before);
  const scene = new THREE.Scene(); scene.add(axes.group);
  axes.dispose(); axes.dispose();
  equal(`${fixture.name}: all owned buffers disposed exactly once`, geometryDisposed, 6);
  equal(`${fixture.name}: all shared-axis and sprite materials disposed exactly once`, materialDisposed, 6);
  equal(`${fixture.name}: all label textures disposed exactly once`, textureDisposed, 3);
  equal(`${fixture.name}: all label cleanup callbacks run exactly once`, labelDisposed, 3);
  equal(`${fixture.name}: disposal detaches axis group and clears scene references`, [scene.children.length, axes.group.children.length], [0, 0]);
}

let partialLabels = 0, partialDisposed = 0;
assert.throws(() => makeLatticeAxes(fixtures[0].rows, () => {
  if (++partialLabels === 2) throw new Error('Injected canvas failure');
  return { sprite: new THREE.Sprite(new THREE.SpriteMaterial()), dispose() { partialDisposed++; } };
}), /Injected canvas failure/);
equal('Partial axis construction disposes completed labels before propagating failure', partialDisposed, 1);
for (const invalid of [[[0, 0, 0], [0, 1, 0], [0, 0, 1]], [[1, 0, 0], [2, 0, 0], [0, 0, 1]], [[NaN, 0, 0], [0, 1, 0], [0, 0, 1]]]) {
  assert.throws(() => latticeViewDirection('a', invalid), /finite nonsingular/);
}
check('Invalid and singular saved lattices are rejected', true);
for (const invalid of [new THREE.Vector3(), new THREE.Vector3(Infinity, 0, 0)]) assert.throws(() => latticeViewUp(invalid), /finite nonzero/);
check('Invalid camera directions are rejected', true);
vectorNear('Isometric preset preserves the existing initial camera direction', latticeViewDirection('iso', fixtures[0].rows), new THREE.Vector3(1.35, 1.05, 1.6).normalize().toArray());

const identity = cartesianOrientationAxes(new THREE.Quaternion());
equal('Cartesian compass labels XYZ independently of lattice abc', identity.map(axis => axis.label), ['x', 'y', 'z']);
equal('Identity compass projects positive X right and positive Y upward', identity.map(({ x, y, depth }) => [x, y, depth]), [[1, -0, 0], [0, -1, 0], [0, -0, 1]]);
const rotatedCamera = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI / 2);
const rotated = cartesianOrientationAxes(rotatedCamera);
near('Compass applies inverse camera orientation: world X points down after +90-degree camera roll', rotated[0].y, 1);
near('Compass applies inverse camera orientation: world Y points right after +90-degree camera roll', rotated[1].x, 1);
for (const axis of rotated) near(`Projected ${axis.label} retains a unit 3D orientation`, Math.hypot(axis.x, axis.y, axis.depth), 1);

const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const manifest = JSON.parse(await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath)));
const stageFiles = manifest.files.filter(file => /^structures\/(?!index\.json$).+\.json$/.test(file.logicalName));
check('Actual recorded geometry stages are included in orientation verification', stageFiles.length > 0);
for (const file of stageFiles) {
  const stage = JSON.parse(await fs.readFile(path.join(website, 'public/research', file.path)));
  const before = JSON.stringify(stage);
  for (const [index, label] of ['a', 'b', 'c'].entries()) {
    const direction = latticeViewDirection(label, stage.geometry.latticeRowsAngstrom);
    vectorNear(`${stage.stageId}: ${label} matches saved row vector`, direction, new THREE.Vector3(...stage.geometry.latticeRowsAngstrom[index]).normalize().toArray());
    near(`${stage.stageId}: ${label} camera-up basis is nonsingular`, latticeViewUp(direction).cross(direction).length(), 1);
  }
  equal(`${stage.stageId}: orientation computation does not mutate saved stage`, JSON.stringify(stage), before);
}
const report = { generatedAt: new Date().toISOString(), dataReleaseId: DATA_RELEASE.dataReleaseId,
  moduleSha256: crypto.createHash('sha256').update(await fs.readFile(modulePath)).digest('hex'),
  actualSavedStages: stageFiles.length, passed: true, checkCount: checks.length, checks };
await fs.writeFile(path.join(website, 'reports/CRYSTAL_LAB_ORIENTATION_VALIDATION.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(`Crystal orientation: ${checks.length} checks passed across ${stageFiles.length} saved stages.`);
