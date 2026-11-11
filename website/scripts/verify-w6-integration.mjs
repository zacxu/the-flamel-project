/** W6 source/science integration gate. Browser and deployment evidence are separate. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(website);
const reportSpecs = [
  ['RESEARCH_VALIDATION', 'run-python.mjs', 'scripts/validate_export.py'],
  ['LOADER_VALIDATION', 'verify-loader.mjs'], ['DATA_GUARDS', 'verify-guards.mjs'],
  ['STATE_VALIDATION', 'verify-state.mjs'], ['REPLAY_VALIDATION', 'verify-replay.mjs'],
  ['PLAYBACK_VALIDATION', 'verify-playback.mjs'], ['GEOMETRY_VALIDATION', 'verify-crystal.mjs'],
  ['VIEWER_VALIDATION', 'verify-viewer.mjs'], ['GENERATION_VALIDATION', 'verify-generation.mjs'],
  ['UNCERTAINTY_VALIDATION', 'verify-uncertainty.mjs'], ['EVIDENCE_VALIDATION', 'verify-evidence.mjs'],
];
if (process.argv.includes('--run')) {
  const outcomes = await Promise.all(reportSpecs.map(([, script, argument]) => new Promise(resolve => {
    const child = spawn(process.execPath, [`scripts/${script}`, ...(argument ? [argument] : []), '--phase=W6'],
      { cwd: website, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', bytes => { output += bytes; });
    child.stderr.on('data', bytes => { output += bytes; });
    child.on('error', error => resolve({ script, code: -1, output: error.message }));
    child.on('close', code => resolve({ script, code, output }));
  })));
  for (const outcome of outcomes) {
    console.log(`${outcome.script}: ${outcome.code === 0 ? 'passed' : 'FAILED'}`);
    assert.equal(outcome.code, 0, outcome.output);
  }
}

const checks = [];
const check = (name, condition, detail) => {
  assert.ok(condition, `${name}${detail === undefined ? '' : `: ${JSON.stringify(detail)}`}`);
  checks.push({ check: name, passed: true, ...(detail === undefined ? {} : { detail }) });
};
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const bytesAt = relative => fs.readFile(path.join(website, relative));
const jsonAt = async relative => JSON.parse(await bytesAt(relative));
const baselineBytes = await bytesAt('reports/W6_BASELINE.json');
const baseline = JSON.parse(baselineBytes);
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
check('Current data identity matches W6 baseline', baseline.dataReleaseId === DATA_RELEASE.dataReleaseId);
check('Immutable manifest pinned by current source matches W6 baseline', baseline.manifestSha256 === DATA_RELEASE.manifestSha256);
check('Baseline original inputs total 103', Object.keys(baseline.sourceHashes).length === 103);
for (const [relative, expected] of Object.entries({ ...baseline.baseline, ...baseline.sourceHashes }))
  check(`Frozen parent input unchanged: ${relative}`, sha(await fs.readFile(path.join(root, relative))) === expected);
for (const [relative, expected] of Object.entries(baseline.publicFiles))
  check(`Curated public research payload unchanged: ${relative}`, sha(await bytesAt(`public/research/${relative}`)) === expected);
for (const relative of ['public/research/manifest.json', DATA_RELEASE.manifestPath])
  check(`Manifest unchanged: ${relative}`, sha(await bytesAt(relative.startsWith('public/') ? relative : `public/${relative}`)) === baseline.manifestSha256);
const historicalEvidence = [];
for (const [phase, closure] of Object.entries(baseline.historicalClosures)) {
  check(`Historical ${phase} completion unchanged`, sha(await bytesAt(`reports/${phase}_COMPLETION.json`)) === closure.sha256);
  for (const evidence of closure.evidence) {
    check(`Historical evidence unchanged: ${evidence.path}`, sha(await bytesAt(evidence.path)) === evidence.sha256);
    historicalEvidence.push(evidence.path);
  }
}

const independentReports = [];
for (const [name, script] of reportSpecs) {
  const relative = `reports/W6_${name}.json`, bytes = await bytesAt(relative), value = JSON.parse(bytes);
  check(`Fresh regression passed: ${name}`, value.status === 'passed');
  check(`No failed checks: ${name}`, (value.checksFailed ?? value.failures ?? 0) === 0 && !(value.failedChecks?.length));
  if (value.phase) check(`Regression has W6 output identity: ${name}`, value.phase === 'W6');
  if (value.dataReleaseId) check(`Regression uses pinned data: ${name}`, value.dataReleaseId === DATA_RELEASE.dataReleaseId);
  if (value.manifestSha256) check(`Regression uses pinned manifest: ${name}`, value.manifestSha256 === DATA_RELEASE.manifestSha256);
  const count = value.checksPassed ?? value.counts?.totalChecks ?? (Array.isArray(value.checks) ? value.checks.length : value.checks);
  check(`Positive scientific/state check count: ${name}`, Number.isInteger(count) && count > 0);
  independentReports.push({ path: relative, sha256: sha(bytes), checksPassed: count,
    verifier: `scripts/${script}`, verifierSha256: sha(await bytesAt(`scripts/${script}`)) });
}
const research = await jsonAt('reports/W6_RESEARCH_VALIDATION.json');
const replay = await jsonAt('reports/W6_REPLAY_VALIDATION.json');
const geometry = await jsonAt('reports/W6_GEOMETRY_VALIDATION.json');
const evidence = await jsonAt('reports/W6_EVIDENCE_VALIDATION.json');
const uncertainty = await jsonAt('reports/W6_UNCERTAINTY_VALIDATION.json');
const playback = await jsonAt('reports/W6_PLAYBACK_VALIDATION.json');
check('All five historical splits and policies exercised', replay.histories === 25 && replay.batches === 125 && replay.queryEvents === 1250);
check('All 31 nonempty policy subsets at six saved boundaries exercised', replay.comparisonVisibilitySubsets === 31 && replay.comparisonBudgets === 6);
check('All histories execute real timer cancellation', playback.historiesExercised === 25 && playback.platformTimerCancellationVerified);
check('All 26 saved geometries and 676 ordered strict energy comparisons checked', geometry.counts.stages === 26 && geometry.counts.orderedEnergyComparisons === 676 && geometry.counts.cifRoundtrips === 26);
check('All 30 uncertainty endpoints and 300 saved retention contexts checked', uncertainty.contexts === 30 && uncertainty.retentionSelections === 300);
check('All 19 QE attempts and 218 overlapping memberships remain represented', research.counts.dft.qeAttempts === 19 && research.counts.dft.referenceMemberships === 218);
check('Accepted geometries and source identities remain distinct', research.counts.dft.acceptedRelaxedGeometries === 3 && research.counts.dft.acceptedOriginalSourceIds === 2);
check('Full missing inventory retained', research.counts.dft.missingMemberships === 215);
check('All generation draws and excluded records retained', research.counts.generation.actualDraws === 88 && research.counts.generation.excludedLargerCellDiagnostics === 12);
check('All evidence source hashes survived verification', evidence.originalSourcesUnchanged === true);

// Independently calculated WCAG contrast from actual UI values and surface tokens.
// These tests verify rendered-presentation inputs, not the raw immutable figure palette.
const { policyColour } = await import(pathToFileURL(path.join(website, 'src/presentation/policyColours.ts')));
const manifest = await jsonAt('public/research/manifest.json');
const themeEntry = manifest.files.find(entry => entry.logicalName === 'theme.json');
const theme = await jsonAt(`public/research/${themeEntry.path}`);
const css = await fs.readFile(path.join(website, 'src/styles.css'), 'utf8');
const token = name => { const result = css.match(new RegExp(`--${name}:(#[0-9a-f]{6})`, 'i')); assert.ok(result, name); return result[1]; };
function luminance(hex) {
  const parts = hex.slice(1).match(/../g).map(value => parseInt(value, 16) / 255)
    .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return parts[0] * .2126 + parts[1] * .7152 + parts[2] * .0722;
}
function contrast(a, b) { const l = [luminance(a), luminance(b)].sort((x, y) => x - y); return (l[1] + .05) / (l[0] + .05); }
const contrastMeasurements = [];
for (const foreground of ['ink', 'muted', 'blue', 'copper']) for (const background of ['paper', 'white']) {
  const ratio = contrast(token(foreground), token(background));
  check(`Normal text ${foreground}/${background} meets 4.5:1`, ratio >= 4.5);
  contrastMeasurements.push({ role: 'normal text', foreground: token(foreground), background: token(background), ratio });
}
const surfaces = [token('paper'), token('white'), '#eeebe1', '#e3dfd3', '#e9eef0'];
for (const policy of ['quality', 'full', 'quality_diversity', 'random', 'uncertainty']) for (const background of surfaces) {
  const foreground = policyColour(theme, policy), ratio = contrast(foreground, background);
  check(`Policy graphic ${policy}/${background} meets 3:1`, ratio >= 3);
  contrastMeasurements.push({ role: 'policy graphic', policy, foreground, background, ratio });
}
check('Contrast corrections preserve the frozen source palette', theme.policyColours.full === '#CC79A7' && theme.policyColours.uncertainty === '#E69F00');
check('Contrast corrections preserve unchanged source theme bytes', sha(await bytesAt(`public/research/${themeEntry.path}`)) === themeEntry.sha256);
const presentationSourcePaths = ['src/presentation/policyColours.ts', 'src/views/Overview.tsx', 'src/views/Replay.tsx', 'src/replay/model.ts'];
const presentationSources = [];
for (const relative of presentationSourcePaths) {
  const bytes = await bytesAt(relative);
  check(`Shipped policy graphics use accessible helper: ${relative}`, bytes.toString('utf8').includes('policyColour'));
  presentationSources.push({ path: relative, sha256: sha(bytes) });
}

let tooling = null;
if (process.argv.includes('--include-tooling')) {
  const relative = 'reports/W6_TOOLING.json', bytes = await bytesAt(relative), value = JSON.parse(bytes);
  check('Final tooling completed with no failures', value.phase === 'W6' && value.status === 'passed' && value.checks_passed === value.checks_total);
  check('Final tooling binds current package manifest', value.package_json_sha256 === sha(await bytesAt('package.json')));
  check('Final tooling binds current immutable data', value.data_manifest_sha256 === DATA_RELEASE.manifestSha256);
  tooling = { path: relative, sha256: sha(bytes), checksPassed: value.checks_passed };
}
const report = { phase: 'W6', status: 'passed', generatedAt: new Date().toISOString(),
  scope: 'Integrated read-only source, arithmetic, saved-geometry, state/lifecycle and WCAG palette verification. Browser interaction, physical-device coverage and deployment are separately recorded.',
  dataReleaseId: DATA_RELEASE.dataReleaseId, manifestSha256: DATA_RELEASE.manifestSha256,
  baselineSha256: sha(baselineBytes), newScientificExperiments: 0, publishedOrDeployed: false,
  checksPassed: checks.length, checksFailed: 0, sourceRegressionChecks: independentReports.reduce((total, item) => total + item.checksPassed, 0),
  independentReports, tooling, presentationSources, contrastMeasurements,
  unchanged: { parentBaselineFiles: Object.keys(baseline.baseline).length, originalInputs: Object.keys(baseline.sourceHashes).length,
    curatedPayloads: Object.keys(baseline.publicFiles).length, historicalClosures: Object.keys(baseline.historicalClosures).length,
    historicalEvidenceFiles: new Set(historicalEvidence).size }, checks,
  limits: ['Source/lifecycle assertions do not certify native browser accessibility, screen-reader behavior or physical mobile devices.',
    'Numerical check totals include repeated contexts and are verification counts, not independent scientific observations.',
    'Fresh QE absolute energies remain separate from historical signed hull labels and CHGNet predictions.',
    'No new stable material, global novelty, symmetry-free architecture benefit or complete convex hull is established.'] };
await fs.writeFile(path.join(website, 'reports/W6_INTEGRATION_VALIDATION.json'), JSON.stringify(report, null, 2) + '\n');
console.log(`W6 integrated source gate: ${checks.length} checks; ${report.sourceRegressionChecks} read-only regression assertions across ${independentReports.length} reports.`);
