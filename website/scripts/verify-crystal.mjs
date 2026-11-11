/** W4: exercise shipped helpers, then independently parse each CIF with NumPy/pymatgen. */
const phase = process.argv.includes('--phase=W6') ? 'W6' : 'W4';

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'), root = path.dirname(website);
const helpers = await import(pathToFileURL(path.join(website, 'src/crystal/geometry.ts')));
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const checks = [], sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const check = (description, condition) => { assert.ok(condition, description); checks.push({ check: description, passed: true }); };
const equal = (description, actual, expected) => { assert.deepEqual(actual, expected, description); checks.push({ check: description, passed: true }); };
const close = (description, actual, expected, tolerance = 1e-10) => check(description, Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance);
const manifestBytes = await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath));
equal('Pinned data manifest identity', sha(manifestBytes), DATA_RELEASE.manifestSha256);
const manifest = JSON.parse(manifestBytes);
async function read(logicalName) {
  const file = manifest.files.find((item) => item.logicalName === logicalName);
  assert.ok(file, logicalName);
  const bytes = await fs.readFile(path.join(website, 'public/research', file.path));
  equal(`Public saved payload hash: ${logicalName}`, sha(bytes), file.sha256);
  return JSON.parse(bytes);
}
const index = await read('structures/index.json');
const stages = await Promise.all(index.stages.map((entry) => read(entry.logicalFile)));
const exportReport = JSON.parse(await fs.readFile(path.join(website, 'reports/W1_EXPORT.json')));
const sourceById = new Map(Object.values(exportReport.inputAllowlist).map((item) => [item.sourceId, item]));
equal('All recorded stages represented', stages.length, 26);
equal('Every recorded candidate represented', index.candidates.length, 14);
const frozenInputsBefore = {};
for (const source of Object.values(exportReport.inputAllowlist)) {
  frozenInputsBefore[source.path] = sha(await fs.readFile(path.join(root, source.path)));
  equal(`Frozen original input before display/export checks: ${source.path}`, frozenInputsBefore[source.path], source.sha256);
}
const fixtures = [];
for (const stage of stages) {
  const name = stage.stageId, g = stage.geometry, before = JSON.stringify(stage);
  const source = sourceById.get(stage.sourceId); assert.ok(source, name);
  const original = JSON.parse(await fs.readFile(path.join(root, source.path)));
  equal(`Exact saved fractional coordinates: ${name}`, g.fractionalCoordinates, original.sites.map((s) => s.abc));
  equal(`Exact saved lattice rows: ${name}`, g.latticeRowsAngstrom, original.lattice.matrix);
  equal(`Source site species and occupancies: ${name}`, g.sites.map((s) => s.species), original.sites.map((s) => s.species.map((sp) => ({ element: sp.element, occupancy: sp.occu }))));
  const positions = g.fractionalCoordinates.map((f) => helpers.fractionalToCartesian(f, g.latticeRowsAngstrom));
  const wrapped = g.fractionalCoordinates.map((f) => helpers.wrapFractional(f, g.pbc));
  for (let i = 0; i < g.actualAtoms; i++) for (let axis = 0; axis < 3; axis++) {
    close(`Source Cartesian site ${i} axis ${axis}: ${name}`, positions[i][axis], original.sites[i].xyz[axis], 1e-8);
    close(`Cartesian inverse site ${i} axis ${axis}: ${name}`, helpers.cartesianToFractional(positions[i], g.latticeRowsAngstrom)[axis], g.fractionalCoordinates[i][axis], 1e-12);
    check(`Display periodic axis range site ${i} axis ${axis}: ${name}`, wrapped[i][axis] >= 0 && wrapped[i][axis] < 1);
    close(`Display wrapping is an integer translation site ${i} axis ${axis}: ${name}`, g.fractionalCoordinates[i][axis] - wrapped[i][axis], Math.round(g.fractionalCoordinates[i][axis] - wrapped[i][axis]), 1e-12);
  }
  close(`Positive row determinant equals saved volume: ${name}`, helpers.determinant(g.latticeRowsAngstrom), g.volumeAngstrom3, 1e-8);
  close(`Minimum exact periodic site distance: ${name}`, helpers.minimumPeriodicDistance(g), g.minimumPeriodicDistanceAngstrom, 1e-8);
  const corners = helpers.cellCorners(g.latticeRowsAngstrom), edges = helpers.cellEdges(g.latticeRowsAngstrom);
  equal(`Eight cell corners: ${name}`, corners.length, 8); equal(`Twelve physical cell edges: ${name}`, edges.length, 12);
  const bounds = helpers.geometryBounds(g.latticeRowsAngstrom, positions);
  for (const point of [...corners, ...positions]) check(`Camera sphere encloses saved cell/site: ${name}`, Math.hypot(...point.map((n, axis) => n - bounds.center[axis])) <= bounds.radius + 1e-12);
  for (const [a, b] of edges) check(`Cell edge follows one basis vector: ${name}`, g.latticeRowsAngstrom.some((row) => row.every((n, axis) => Math.abs(n - b[axis] + a[axis]) < 1e-12)));
  if (stage.parentStageId) {
    const parent = stages.find((item) => item.stageId === stage.parentStageId);
    check(`Recorded stage lineage stays inside exact entity: ${name}`, parent?.candidateId === stage.candidateId && parent.sourceId === stage.recordedParentSourceId);
  }
  const cif = helpers.structureCif(stage, DATA_RELEASE.dataReleaseId);
  check(`CIF has source/stage/release provenance: ${name}`, [stage.sourceId, stage.sourceSha256, stage.stageId, DATA_RELEASE.dataReleaseId].every((s) => cif.includes(s)));
  check(`CIF has no private path: ${name}`, !/[A-Za-z]:[\\/]|\\Users\\|\/Users\//i.test(cif));
  for (const f of g.fractionalCoordinates) check(`CIF retains raw full-precision coordinates: ${name}`, cif.includes(f.join(' ')));
  equal(`Pure helpers and CIF do not mutate saved record: ${name}`, JSON.stringify(stage), before);
  const distances = g.fractionalCoordinates.map((a) => g.fractionalCoordinates.map((b) => helpers.distancePeriodic(a, b, g.latticeRowsAngstrom, g.pbc)));
  fixtures.push({ stage, sourcePath: source.path, cartesian: positions, wrapped, bounds, distances, cif, cifSha256: sha(cif) });
}
equal('Recorded nonorthogonal stages remain explicit', stages.filter(({geometry:{latticeRowsAngstrom:m}}) => [[0,1],[0,2],[1,2]].some(([a,b]) => Math.abs(m[a].reduce((n,x,i)=>n+x*m[b][i],0))>1e-6)).map((s)=>s.stageId).sort(), [...index.validation.nonOrthogonalStageIds].sort());
const skew = [[1,0,0],[.99,.01,0],[0,0,1]], fractionalA = [.49,.49,0];
const naiveDistance = Math.hypot(...helpers.fractionalToCartesian(fractionalA, skew));
const exactDistance = helpers.distancePeriodic(fractionalA, [0,0,0], skew, [true,true,true]);
check('Skew lattice closest image beats independent component rounding', exactDistance < naiveDistance / 10);
close('Skew closest image outside nearest rounded image is found', exactDistance, Math.hypot(.49 + -.51 * .99, -.51 * .01), 1e-12);
equal('Partial PBC leaves nonperiodic axis unchanged', helpers.wrapFractional([-1.25,2.25,-3], [true,false,true]), [.75,2.25,0]);
close('No PBC gives direct Cartesian distance', helpers.distancePeriodic([0,0,0], [1,0,0], skew, [false,false,false]), 1);
close('Partial PBC never shifts a nonperiodic axis', helpers.distancePeriodic([0,0,0], [0,0,2.1], skew, [true,true,false]), 2.1);
close('Whole periodic translation has zero distance', helpers.distancePeriodic([3,-4,2], [0,0,0], skew, [true,true,true]), 0);
assert.throws(() => helpers.inverseLattice([[1,0,0],[1,0,0],[0,0,1]])); checks.push({check:'Singular cell rejected instead of fabricating coordinates',passed:true});
const compositionKey = (g) => {
  const counts={}; for(const site of g.sites)for(const specie of site.species)counts[specie.element]=(counts[specie.element]??0)+specie.occupancy;
  const rows=Object.entries(counts).sort(([a],[b])=>a.localeCompare(b));return rows.map(([e,n])=>`${e}:${(n/rows[0][1]).toPrecision(14)}`).join('|');
};
const comparisonFixtures=[];
for(const a of stages)for(const b of stages){
  const actual=helpers.comparableEnergy(a,b);
  const compatible=!!(a.energy&&b.energy&&compositionKey(a.geometry)===compositionKey(b.geometry)&&a.energy.engine===b.energy.engine&&a.energy.unit===b.energy.unit&&a.energy.settingsScope===b.energy.settingsScope&&isDeepStrictEqual(a.energy.settings,b.energy.settings));
  equal(`Energy gate: ${a.stageId} -> ${b.stageId}`,actual.compatible,compatible);
  equal(`Energy delta availability: ${a.stageId} -> ${b.stageId}`,actual.deltaEVPerAtom,compatible?b.energy.value-a.energy.value:null);
  comparisonFixtures.push({left:a.stageId,right:b.stageId,...actual});
}
const mgo=stages.find((s)=>s.stageId==='phase1_mgo_attempt_000--model_relaxed');
const partial=structuredClone(mgo);partial.geometry.pbc=[true,false,true];
assert.throws(()=>helpers.structureCif(partial),/three periodic axes/);checks.push({check:'CIF rejects nonperiodic geometry instead of silently imposing crystal PBC',passed:true});
for(const [field,value] of [['checkpointSha256','changed'],['optimizer','BFGS'],['maxSteps',400],['imposedSymmetry',true],['packageVersion',null]]){
  const changed=structuredClone(mgo);changed.energy.settings[field]=value;
  equal(`Shared display scope cannot mask changed actual setting ${field}`,helpers.comparableEnergy(mgo,changed).compatible,false);
}
for(const required of Object.keys(mgo.energy.settings)){
  const changed=structuredClone(mgo);delete changed.energy.settings[required];
  equal(`Unknown actual setting ${required} blocks delta`,helpers.comparableEnergy(mgo,changed).deltaEVPerAtom,null);
}
for(const [field,value] of [['checkpointSha256','unknown'],['optimizer','unknown'],['maxSteps',0],['forceThresholdEVPerAngstrom',-1]]){
  const changed=structuredClone(mgo);changed.energy.settings[field]=value;
  equal(`Shared invalid/unknown CHGNet setting ${field} blocks delta even against itself`,helpers.comparableEnergy(changed,changed).compatible,false);
}
const qe=stages.find((s)=>s.stageId==='phase1_mgo_attempt_000--accepted_dft');
for(const [field,value] of [['executableSha256','unknown'],['pseudoSha256ByElement',{Mg:'unknown',O:'unknown'}],['kMesh',[0,0,0]],['nspin',0]]){
  const changed=structuredClone(qe);changed.energy.settings[field]=value;
  equal(`Shared invalid/unknown QE setting ${field} blocks delta even against itself`,helpers.comparableEnergy(changed,changed).compatible,false);
}
for(const [left,right,delta] of [
  ['phase1_mgo_attempt_000--model_relaxed','phase4_supplementary_mgo_rocksalt_p1_attempt_010--model_relaxed',0.35687923431396484],
  ['phase4_tio2_rutile_nontrivial_attempt_000--model_relaxed','phase4_tio2_rutile_p1_attempt_000--model_relaxed',0.05580647786458215],
]) close(`Recorded one-per-arm CHGNet delta right-left: ${left}`,helpers.comparableEnergy(stages.find((s)=>s.stageId===left),stages.find((s)=>s.stageId===right)).deltaEVPerAtom,delta,1e-12);
const cache=path.join(website,'.cache');await fs.mkdir(cache,{recursive:true});
const fixturePath=path.join(cache,'w4-crystal-fixtures.json');
await fs.writeFile(fixturePath,JSON.stringify({dataReleaseId:DATA_RELEASE.dataReleaseId,fixtures,comparisons:comparisonFixtures,edgeCases:[{name:'highly_skew_closest_image',lattice:skew,a:fractionalA,b:[0,0,0],pbc:[true,true,true],distance:exactDistance}]},null,2)+'\n');
const python=process.env.FLAMEL_PYTHON||path.join(root,'.envs/analysis/Scripts/python.exe');
const result=spawnSync(python,[path.join(website,'scripts/verify-crystal.py'),fixturePath],{cwd:website,encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}});
if(result.stdout)process.stdout.write(result.stdout);if(result.stderr)process.stderr.write(result.stderr);if(result.error)throw result.error;assert.equal(result.status,0,'Independent NumPy/pymatgen CIF and saved geometry checks');
const pythonReport=JSON.parse(await fs.readFile(path.join(cache,'w4-cif-validation.json')));
for(const source of Object.values(exportReport.inputAllowlist))equal(`Frozen original input after display/export checks: ${source.path}`,sha(await fs.readFile(path.join(root,source.path))),frozenInputsBefore[source.path]);
const report={phase,status:'passed',generatedAt:new Date().toISOString(),dataReleaseId:DATA_RELEASE.dataReleaseId,manifestSha256:DATA_RELEASE.manifestSha256,newExperiments:0,scope:'Pure saved geometry, strict energy compatibility, and full-precision explicit-site CIF; no new symmetry inference or structure matching.',counts:{stages:26,candidates:14,orderedEnergyComparisons:676,cifRoundtrips:26,nodeChecks:checks.length,pythonChecks:pythonReport.checks.length,totalChecks:checks.length+pythonReport.checks.length},nonOrthogonalStageIds:index.validation.nonOrthogonalStageIds,checks:[...checks,...pythonReport.checks],cifExports:fixtures.map(({stage,cifSha256})=>({stageId:stage.stageId,sha256:cifSha256})),limits:['CIF standard cells preserve lattice metric; custom tags also retain exact original Cartesian basis rows.','Explicit P1 CIF representation does not assert the saved structure was generated with P1 or infer symmetry.','Strict identical k-mesh/settings gate declines the differently sampled accepted MgO QE cells.']};
await fs.writeFile(path.join(website,`reports/${phase}_GEOMETRY_VALIDATION.json`),JSON.stringify(report,null,2)+'\n');
console.log(`${phase} saved geometry/CIF verification passed: ${report.counts.totalChecks} checks; all 26 saved stages and 676 energy comparisons.`);
