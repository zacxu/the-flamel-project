// Read-only browser acceptance for the existing InfinityFree site. Run in Node 24 with playwright-core and Chrome.
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { parseArgs } = require('node:util');
const { chromium } = require('playwright-core');

const site = 'https://theflamelproject.42web.io';
const refresh = site + '/refresh';
const submission = 'https://scientificintelligence.org/campaigns/osi-hackathon-2026/submissions/7';
const { values: options } = parseArgs({ options: {
  'package-record': { type: 'string' }, output: { type: 'string' }, 'site-only': { type: 'boolean' },
  'predecessor-root': { type: 'string' }, rollback: { type: 'boolean' }
}});
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

async function readLive(page, pathname) {
  return page.evaluate(async pathname => {
    const response = await fetch(pathname, {cache: 'no-store', mode: 'same-origin', redirect: 'error', signal: AbortSignal.timeout(30000)});
    const bytes = await response.arrayBuffer();
    const hash = await crypto.subtle.digest('SHA-256', bytes);
    return {path: pathname, status: response.status, bytes: bytes.byteLength,
      sha256: [...new Uint8Array(hash)].map(n => n.toString(16).padStart(2, '0')).join(''),
      cacheControl: response.headers.get('cache-control'), type: response.headers.get('content-type')};
  }, pathname);
}

async function verifyDownload(page, expected, output) {
  const link = page.locator('a[download="' + expected.filename + '"]');
  const [download] = await Promise.all([page.waitForEvent('download'), link.click()]);
  assert.equal(download.suggestedFilename(), expected.filename);
  const destination = path.join(output, expected.filename);
  await download.saveAs(destination);
  const bytes = await fs.readFile(destination);
  const sha256 = digest(bytes);
  assert.equal(sha256, expected.sha256);
  assert.equal(bytes.length, expected.bytes);
  return {filename: expected.filename, sha256, bytes: bytes.length};
}

async function main() {
  assert(options['package-record'] && options.output, 'Supply --package-record and --output <new folder>');
  const output = path.resolve(options.output);
  const record = JSON.parse(await fs.readFile(options['package-record'], 'utf8'));
  const defaults = JSON.parse(await fs.readFile(path.join(__dirname, '../../../website/reports/W7_LIVE_DOWNLOAD_VALIDATION.json'), 'utf8'));
  assert(record.fileCount === record.files.length && record.files.length > 0);
  assert(new Set(record.files.map(file => file.path)).size === record.files.length);
  for (const file of record.files) {
    assert(file.path.split('/').every(part => /^[A-Za-z0-9_.-]+$/.test(part) && part !== '.' && part !== '..'));
    assert(/^[0-9a-f]{64}$/.test(file.sha256) && Number.isSafeInteger(file.bytes) && file.bytes >= 0);
  }
  const entry = record.files.find(file => file.path === 'index.html');
  assert(entry);
  await fs.mkdir(output);
  const report = {status:'PARTIAL', operation: options.rollback ? 'verify-restored-website' : 'verify-website', checkedAt:new Date().toISOString(), submission, permanentUrl:refresh,
    expectedBuild:record.uiBuildId, packageRecordSha256:digest(await fs.readFile(options['package-record'])),
    submissionChecked:false, payload:[], entries:[], downloads:[], predecessor:[], errors:[]};
  let browser;
  try {
    browser = await chromium.launch({executablePath: process.env.CHROME_PATH || undefined,
      channel: process.env.CHROME_PATH ? undefined : 'chrome', headless:true,
      args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
    report.browser = browser.version();
    const context = await browser.newContext({acceptDownloads:true, viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
    let page = await context.newPage();
    if (!options['site-only']) {
      try {
        const source = await page.goto(submission, {waitUntil:'domcontentloaded'});
        assert.equal(source.status(), 200);
        const link = page.locator('a[href="' + refresh + '"]:visible').first();
        await link.waitFor({timeout:20000});
        report.submissionLink = {text:(await link.innerText()).trim(), href:await link.getAttribute('href')};
        const popup = (await link.getAttribute('target')) === '_blank';
        if (popup) [page] = await Promise.all([context.waitForEvent('page'),link.click()]);
        else await link.click();
        await page.waitForURL(url => url.origin === site && url.pathname === '/refresh', {timeout:30000});
        report.submissionChecked = true;
      } catch (error) {
        report.errors.push('Submission click: ' + error.message.split('\n')[0]);
      }
    }
    if (!report.submissionChecked) await page.goto(refresh, {waitUntil:'domcontentloaded'});
    const footer = page.locator('footer[data-ui-build]');
    await footer.waitFor({timeout:45000});
    report.liveBuild = await footer.getAttribute('data-ui-build');
    assert.equal(report.liveBuild, record.uiBuildId);
    for (const pathname of ['/refresh', '/']) {
      const actual = await readLive(page, pathname);
      report.entries.push(actual);
      assert.equal(actual.status,200);
      assert.equal(actual.sha256,entry.sha256);
      assert.equal(actual.bytes,entry.bytes);
      assert.match(actual.type, /text\/html/i);
      if (pathname === '/refresh') assert.match(actual.cacheControl || '', /(?:^|,)\s*no-store\s*(?:,|$)/i);
    }
    await page.screenshot({path:path.join(output, 'overview.png')});
    for (const file of record.files) {
      const actual = await readLive(page, '/' + file.path);
      report.payload.push({...actual, matches:actual.status === 200 && actual.bytes === file.bytes && actual.sha256 === file.sha256});
    }
    const mismatches = report.payload.filter(row => !row.matches);
    if (mismatches.length) report.errors.push('Release payload mismatches: ' + mismatches.map(row => row.path).join(', '));
    if (options['predecessor-root']) {
      // Check immutable assets unique to the predecessor. Shared paths were verified above.
      const currentPaths = new Set(record.files.map(file => file.path));
      for (const folder of ['assets','release-manifests']) {
        const directory = path.join(options['predecessor-root'],folder);
        for (const file of await fs.readdir(directory,{withFileTypes:true})) {
          assert(file.isFile() && /^[A-Za-z0-9_.-]+$/.test(file.name));
          const name = folder + '/' + file.name;
          if (currentPaths.has(name)) continue;
          const expected = await fs.readFile(path.join(directory,file.name));
          const actual = await readLive(page,'/' + name);
          const matches = actual.status === 200 && actual.bytes === expected.length && actual.sha256 === digest(expected);
          report.predecessor.push({...actual,matches});
          if (!matches) report.errors.push('Predecessor file mismatch: ' + name);
        }
      }
    }
    // Bind the scientific export expectations to the data release actually served by this snapshot.
    const manifestName = '/release-manifests/' + record.uiBuildId + '.json';
    const manifestRow = record.files.find(file => '/' + file.path === manifestName);
    assert(manifestRow, 'Snapshot must include the selected UI release manifest');
    const manifest = await page.evaluate(async pathname => {
      const response = await fetch(pathname, {cache:'no-store',mode:'same-origin',redirect:'error',signal:AbortSignal.timeout(30000)});
      const bytes = await response.arrayBuffer();
      const hash = await crypto.subtle.digest('SHA-256', bytes);
      const parsed = JSON.parse(new TextDecoder().decode(bytes));
      return {ui:parsed.uiBuildId,data:parsed.dataReleaseId,
        sha256:[...new Uint8Array(hash)].map(n=>n.toString(16).padStart(2,'0')).join('')};
    },manifestName);
    assert.equal(manifest.ui, record.uiBuildId);
    assert.equal(manifest.data, defaults.dataReleaseId, 'Load verified export expectations for the restored scientific data');
    if (options.rollback) assert.equal(manifest.sha256, manifestRow.sha256, 'Restored manifest must match the captured bytes');
    report.downloadDataReleaseId = manifest.data;
    const cif = defaults.downloads.find(item => item.kind === 'cif');
    const csv = defaults.downloads.find(item => item.kind === 'comparison');
    await page.goto(refresh + '#/crystals');
    const viewport = page.locator('.crystal-viewer canvas');
    await viewport.waitFor({timeout:35000});
    // Older production builds predate the axis compass and labeled camera control dock.
    const modernControls = !options.rollback || record.uiBuildId === 'ui-w6-351e6182d7af3a9d062d' ||
      await page.locator('.crystal-viewer-details, [data-cartesian-axis]').count() > 0;
    if (modernControls) {
      assert.equal(await page.locator('[data-cartesian-axis]').count(),3);
      const axes = page.getByLabel('Lattice axis legend');
      await axes.waitFor();
      const metrics = page.locator('.crystal-camera-metrics');
      await page.locator('.crystal-viewer-details > summary').click();
      await metrics.waitFor();
      const before = await metrics.textContent();
      await page.getByRole('button', {name:'Rotate crystal left'}).click();
      await page.waitForFunction(before => document.querySelector('.crystal-camera-metrics')?.textContent !== before, before);
      await page.getByRole('button',{name:/Lattice axes/}).click();
      await axes.waitFor({state:'hidden'});
      await page.getByRole('button',{name:/Lattice axes/}).click();
      await axes.waitFor();
      await page.getByRole('button',{name:'Reset view', exact:true}).click();
      await page.waitForFunction(before => document.querySelector('.crystal-camera-metrics')?.textContent === before, before);
      report.viewer = {canvas:true,xyzAxes:3,rotationChanged:true,resetRestored:true,latticeAxesToggle:true};
    } else {
      report.viewer = {canvas:true, controls:'predecessor predates axis and camera control dock'};
    }
    await viewport.scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'crystals.png')});
    report.downloads.push(await verifyDownload(page, cif, output));
    await page.goto(refresh + csv.selection.hash);
    report.downloads.push(await verifyDownload(page,csv,output));
    report.status = report.errors.length ? 'PARTIAL' : options['site-only'] ? 'PASS_SITE_ONLY' : 'PASS';
  } catch (error) {
    report.errors.push(error.message.split('\n').slice(0,4).join(' '));
  } finally {
    await browser?.close();
    await fs.writeFile(path.join(output,'live-acceptance.json'),JSON.stringify(report,null,2) + '\n');
  }
  console.log(JSON.stringify({status:report.status,liveBuild:report.liveBuild,submissionChecked:report.submissionChecked,
    entries:report.entries,files:report.payload.length,matched:report.payload.filter(row=>row.matches).length,
    downloads:report.downloads,errors:report.errors}));
  if (report.status === 'PARTIAL') process.exitCode = 1;
}
main().catch(error => {console.error(error.message);process.exitCode = 1;});