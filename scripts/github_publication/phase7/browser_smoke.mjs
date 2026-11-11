/** Fresh-profile Chrome loopback smoke for exact built bytes; no hosting access.
 * Uses Node 24's built-in WebSocket and Chrome DevTools Protocol.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createHash } from 'node:crypto';

const args = new Map();
for (const argument of process.argv.slice(2)) {
  const matched = argument.match(/^--(website-root|browser|output)=(.+)$/);
  assert.ok(matched && !args.has(matched[1]), 'Usage: --website-root=<built website> --browser=<Chrome executable> --output=<new external folder>');
  args.set(matched[1], matched[2]);
}
assert.equal(args.size, 3);
const website = path.resolve(args.get('website-root'));
const output = path.resolve(args.get('output'));
const source = path.dirname(website);
const browserPath = path.resolve(args.get('browser'));
assert.ok(output !== source && !output.startsWith(source + path.sep), 'Smoke output must be outside source');
for (const selected of [website, output, browserPath]) {
  for (let current = selected; ; current = path.dirname(current)) {
    try { assert.ok(!(await fs.lstat(current)).isSymbolicLink(), 'Smoke paths cannot traverse links'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (path.dirname(current) === current) break;
  }
}
await fs.mkdir(output); // A reused profile/output is deliberately rejected.
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const record = JSON.parse(await fs.readFile(path.join(website, 'reports/W6_RELEASE_PACKAGE.json'), 'utf8'));
const payload = new Map();
for (const row of record.files) {
  assert.ok(!row.path.split('/').some(part => ['', '.', '..'].includes(part)) && !row.path.includes('\\'));
  const bytes = await fs.readFile(path.join(website, 'dist', row.path));
  assert.equal(bytes.length, row.bytes);
  assert.equal(digest(bytes), row.sha256);
  payload.set(row.path, bytes);
}
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.csv': 'text/csv; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8' };
const responses = [];
const server = http.createServer((request, response) => {
  const name = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname).slice(1) || 'index.html';
  if (name === 'favicon.ico' && !payload.has(name)) { response.writeHead(204); response.end(); return; }
  const bytes = payload.get(name);
  responses.push({ path: name, status: bytes ? 200 : 404 });
  if (!bytes) { response.writeHead(404); response.end('Missing release file'); return; }
  response.writeHead(200, { 'Content-Type': types[path.extname(name)] ?? 'application/octet-stream', 'Cache-Control': 'no-store' });
  response.end(bytes);
});
const stdout = await fs.open(path.join(output, 'chrome-stdout.log'), 'wx');
const stderr = await fs.open(path.join(output, 'chrome-stderr.log'), 'wx');
let browser, socket, connection, version;
const checks = [], pageErrors = [], consoleErrors = [], requestFailures = [], externalRequests = [];
function check(name, value, detail) { checks.push({ name, passed: Boolean(value), detail }); assert.ok(value, name); }
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
class Protocol {
  constructor(ws) {
    this.ws = ws; this.next = 1; this.pending = new Map();
    ws.addEventListener('message', event => {
      const data = JSON.parse(event.data);
      if (data.id) {
        const entry = this.pending.get(data.id);
        if (entry) { clearTimeout(entry.timer); this.pending.delete(data.id); data.error ? entry.reject(new Error(data.error.message)) : entry.resolve(data.result); }
      } else {
        if (data.method === 'Runtime.exceptionThrown') pageErrors.push(data.params.exceptionDetails);
        if (data.method === 'Runtime.consoleAPICalled' && data.params.type === 'error') consoleErrors.push(data.params.args.map(arg => arg.description ?? arg.value));
        if (data.method === 'Network.loadingFailed' && !data.params.canceled) requestFailures.push(data.params.errorText);
        if (data.method === 'Network.requestWillBeSent') {
          const url = data.params.request.url;
          if (/^https?:/.test(url) && !url.startsWith(connection)) externalRequests.push(url);
        }
      }
    });
    ws.addEventListener('close', () => {
      for (const item of this.pending.values()) { clearTimeout(item.timer); item.reject(new Error('DevTools connection closed')); }
      this.pending.clear();
    });
  }
  send(method, params = {}) {
    const id = this.next++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error('DevTools timeout: ' + method)); }, 20000);
      this.pending.set(id, { resolve, reject, timer });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async value(expression) {
    const result = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  }
  async until(expression, label) {
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) { if (await this.value(expression)) return; await sleep(150); }
    throw new Error('Browser readiness timeout: ' + label);
  }
}
let error = null;
try {
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  connection = 'http://127.0.0.1:' + server.address().port + '/';
  const profile = path.join(output, 'chrome-profile');
  browser = spawn(browserPath, ['--headless=new', '--remote-debugging-port=0', '--user-data-dir=' + profile,
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-sync',
    '--disable-component-update', '--disable-default-apps', '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader', '--window-size=1440,1000', 'about:blank'],
    { windowsHide: true, stdio: ['ignore', stdout.fd, stderr.fd] });
  const startupError = new Promise((resolve, reject) => browser.once('error', reject));
  let port;
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline && !port) {
    try { port = Number((await fs.readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); }
    catch (readError) { if (readError.code !== 'ENOENT') throw readError; }
    if (!port) await Promise.race([sleep(100), startupError]);
  }
  assert.ok(port, 'Isolated Chrome must expose its own debugger port');
  const targets = await (await fetch('http://127.0.0.1:' + port + '/json/list')).json();
  const page = targets.find(target => target.type === 'page');
  assert.ok(page, 'Fresh profile provides a page target');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); });
  socket = new Protocol(ws);
  version = await socket.send('Browser.getVersion');
  for (const method of ['Page.enable', 'Runtime.enable', 'Network.enable']) await socket.send(method);
  await socket.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await socket.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  await socket.send('Page.navigate', { url: connection });
  await socket.until('Boolean(document.querySelector("main.view-overview #overview-title") && ![...document.querySelectorAll("header button")].find(b => b.textContent === "Glossary")?.disabled)', 'hydrated overview');
  const home = await socket.value('({heading:document.querySelector("h1")?.textContent,build:document.querySelector("footer")?.dataset.uiBuild,links:document.querySelectorAll("nav[aria-label=\\"Research views\\"] a").length})');
  check('Home hydrated actual recorded datasets', Boolean(home.heading) && home.links === 6, home);
  check('Browser footer binds the exact built package identity', home.build === record.uiBuildId, home.build);
  const homeShot = await socket.send('Page.captureScreenshot', { format: 'png' });
  await fs.writeFile(path.join(output, 'home.png'), Buffer.from(homeShot.data, 'base64'), { flag: 'wx' });
  await socket.send('Page.navigate', { url: connection + '#/crystals' });
  await socket.until('document.querySelector("main.view-crystals h1")?.textContent === "Inspect the actual cells."', 'Crystal Lab route');
  await socket.until('Boolean(document.querySelector(".crystal-viewer canvas") && !document.querySelector("button[aria-label=\\"Rotate crystal left\\"]")?.disabled)', 'interactive saved crystal');
  const crystal = await socket.value('({canvas:document.querySelector(".crystal-viewer canvas")?.getAttribute("aria-label"),axes:document.querySelectorAll("[data-cartesian-axis]").length,sites:document.querySelector(".crystal-atom-card select")?.options.length,badge:document.querySelector(".crystal-viewport-badge")?.textContent})');
  check('Crystal route drew the real saved structure in canvas', Boolean(crystal.canvas) && crystal.badge.includes('Interactive 3D') && crystal.sites > 1, crystal);
  check('Saved lattice legend and XYZ compass are present', crystal.axes === 3 && await socket.value('Boolean(document.querySelector("[aria-label=\\"Lattice axis legend\\"]"))'), crystal.axes);
  const before = await socket.value('document.querySelector(".crystal-camera-metrics")?.textContent');
  await socket.value('document.querySelector("button[aria-label=\\"Rotate crystal left\\"]").click()');
  await socket.until('document.querySelector(".crystal-camera-metrics")?.textContent !== ' + JSON.stringify(before), 'rotation readout');
  const after = await socket.value('document.querySelector(".crystal-camera-metrics")?.textContent');
  check('Actual rotate control changes the camera readout', Boolean(before && after) && before !== after, { before, after });
  await socket.value('[...document.querySelectorAll("button")].find(b => b.textContent.includes("Lattice axes")).click()');
  await socket.until('!document.querySelector("[aria-label=\\"Lattice axis legend\\"]")', 'axes hidden');
  check('Axes toggle updates the rendered legend', await socket.value('!document.querySelector("[aria-label=\\"Lattice axis legend\\"]")'), 'Hidden after activating actual control');
  await socket.value('[...document.querySelectorAll("button")].find(b => b.textContent.includes("Lattice axes")).click()');
  await socket.until('Boolean(document.querySelector("[aria-label=\\"Lattice axis legend\\"]"))', 'axes restored');
  const siteBefore = await socket.value('document.querySelector(".crystal-site-meta strong")?.textContent');
  await socket.value('(() => { const s=document.querySelector(".crystal-atom-card select");s.selectedIndex=1;s.dispatchEvent(new Event("change",{bubbles:true})); })()');
  await socket.until('document.querySelector(".crystal-site-meta strong")?.textContent !== ' + JSON.stringify(siteBefore), 'physical site selection');
  check('Site inspector selects another actual physical site', await socket.value('document.querySelector(".crystal-site-meta strong")?.textContent !== ' + JSON.stringify(siteBefore)), 'Selected the second saved physical site');
  await socket.value('[...document.querySelectorAll("button")].find(b => b.textContent === "Reset view").click()');
  await socket.until('document.querySelector(".crystal-camera-metrics")?.textContent === ' + JSON.stringify(before), 'camera reset');
  check('Reset view restores the starting camera readout', await socket.value('document.querySelector(".crystal-camera-metrics")?.textContent === ' + JSON.stringify(before)), before);
  await socket.value('document.querySelector(".crystal-viewport").scrollIntoView({block:"start"})');
  await sleep(150);
  const crystalShot = await socket.send('Page.captureScreenshot', { format: 'png' });
  await fs.writeFile(path.join(output, 'crystals.png'), Buffer.from(crystalShot.data, 'base64'), { flag: 'wx' });
  check('No page exceptions or console errors', pageErrors.length === 0 && consoleErrors.length === 0, { pageErrors, consoleErrors });
  check('No failed application requests', requestFailures.length === 0 && responses.every(row => row.status === 200), { requestFailures, responses: responses.length });
  check('Application fetched only loopback release bytes', externalRequests.length === 0, externalRequests);
  for (const row of record.files) check('Release bytes preserved: ' + row.path, digest(await fs.readFile(path.join(website, 'dist', row.path))) === row.sha256, row.sha256);
} catch (caught) { error = String(caught.stack ?? caught); }
finally {
  if (socket) { try { await socket.send('Browser.close'); } catch {} socket.ws.close(); }
  if (browser && browser.exitCode === null) {
    await Promise.race([once(browser, 'exit'), sleep(5000)]);
    if (browser.exitCode === null) { browser.kill(); await Promise.race([once(browser, 'exit'), sleep(5000)]); }
  }
  server.closeAllConnections();
  if (server.listening) await new Promise(resolve => server.close(resolve));
  await stdout.close(); await stderr.close();
}
const result = {
  status: error ? 'FAIL' : 'PASS', scope: 'Fresh-profile headless Chrome loopback smoke; actual hydrated UI, saved geometry and DOM-activated controls. Not full manual/touch/production acceptance.',
  checked_at: new Date().toISOString(), ui_build_id: record.uiBuildId, browser: version,
  check_count: checks.length, passed: checks.filter(row => row.passed).length, checks,
  error, page_errors: pageErrors, console_errors: consoleErrors, request_failures: requestFailures,
  external_application_requests: externalRequests, observed_http_requests: responses.length,
  loopback_server_closed: !server.listening, browser_closed: browser?.exitCode !== null,
  fresh_profile_only: true, existing_profile_accessed: false, hosting_accessed: false, new_scientific_experiments: 0
};
await fs.writeFile(path.join(output, 'browser-smoke.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
console.log(JSON.stringify({ status: result.status, checks: result.check_count, ui_build_id: record.uiBuildId, output, error }, null, 2));
if (error) process.exitCode = 1;
