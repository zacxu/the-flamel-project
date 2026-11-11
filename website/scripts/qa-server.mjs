/** Loopback-only website fault fixture. This serves the built bytes without
 * modifying the public release or adding anything to the deployed application.
 * Write a mode to .cache/w2-network-mode.txt to change subsequent responses. */
import fs from 'node:fs/promises';
import { appendFileSync } from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = await fs.realpath(path.join(website, 'dist'));
const modeFile = path.join(website, '.cache/w2-network-mode.txt');
const args = process.argv.slice(2);
if (args.some((arg, index) => index !== 0 && index !== 1) || (args.length > 0 && args[0] !== '--port') || args.length === 1) {
  throw new Error('Usage: node scripts/qa-server.mjs [--port 4175]');
}
const port = args.length === 2 ? Number(args[1]) : 4175;
if (!Number.isSafeInteger(port) || port < 1 || port > 65535) throw new Error('Port must be an integer from 1 to 65535.');
const mime = { '.webp': 'image/webp', '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml' };
const validModes = new Set(['ok', 'missing', 'corrupt', 'pending', 'stage-missing', 'image-missing', 'history-missing', 'chart-missing', 'viewer-missing', 'no-webgl', 'renderer-error', 'viewer-context-loss', 'reduced-motion', 'generation-missing', 'uncertainty-missing', 'dft-missing', 'ui-image-missing', 'ui-image-corrupt', 'tour-observer']);
async function readMode() {
  try {
    const mode = (await fs.readFile(modeFile, 'utf8')).trim();
    return validModes.has(mode) ? mode : 'ok';
  } catch (error) {
    if (error.code === 'ENOENT') return 'ok';
    throw error;
  }
}
function reply(response, status, body, type = 'text/plain; charset=utf-8') {
  if (response.destroyed || response.writableEnded) return;
  if (process.env.FLAMEL_RECORD_REQUESTS === '1') {
    appendFileSync(path.join(website, '.cache/w6-http-requests.jsonl'), JSON.stringify({
      time: new Date().toISOString(), path: response.qaPath ?? null,
      method: response.qaMethod ?? null, status, bodyBytes: Buffer.byteLength(body),
    }) + '\n');
  }
  response.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store', 'Content-Length': Buffer.byteLength(body),
    'X-Content-Type-Options': 'nosniff' });
  response.end(body);
}
async function waitForMode(request, response) {
  let elapsed = 0;
  while (elapsed < 30000 && !request.destroyed && !response.destroyed) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    elapsed += 100;
    const mode = await readMode();
    if (mode !== 'pending') return mode;
  }
  return 'pending';
}

const server = http.createServer(async (request, response) => {
  try {
    if (request.method !== 'GET' && request.method !== 'HEAD') return reply(response, 405, 'Method not allowed.');
    const url = new URL(request.url, `http://127.0.0.1:${port}`);
    const pathname = decodeURIComponent(url.pathname);
    response.qaPath = pathname;
    response.qaMethod = request.method;
    if (pathname.includes('\\') || pathname.includes('\0')) return reply(response, 400, 'Invalid path.');
    let target = path.resolve(dist, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (target !== dist && !target.startsWith(dist + path.sep)) return reply(response, 403, 'Path outside fixture root.');
    try {
      target = await fs.realpath(target);
      if (!target.startsWith(dist + path.sep)) return reply(response, 403, 'Path outside fixture root.');
    } catch { return reply(response, 404, 'File unavailable.'); }
    const isManifest = pathname.endsWith('/manifest.json');
    let mode = await readMode();
    if (isManifest && mode === 'pending') mode = await waitForMode(request, response);
    if (response.destroyed) return;
    if (isManifest && (mode === 'missing' || mode === 'pending')) return reply(response, 503, 'Fixture manifest unavailable.');
    const isAtomicStage = pathname.includes('/structures/') && pathname.endsWith('.json') && !/\/structures\/index\.[a-f0-9]+\.json$/.test(pathname);
    if (mode === 'generation-missing' && /\/generation\.[a-f0-9]+\.json$/.test(pathname)) return reply(response, 404, 'Fixture generation evidence unavailable.');
    if (mode === 'uncertainty-missing' && /\/uncertainty\.[a-f0-9]+\.json$/.test(pathname)) return reply(response, 404, 'Fixture uncertainty evidence unavailable.');
    if (mode === 'dft-missing' && /\/dft\.[a-f0-9]+\.json$/.test(pathname)) return reply(response, 404, 'Fixture DFT evidence unavailable.');
    if (mode === 'history-missing' && /\/replay\/seed-.*\.json$/.test(pathname)) return reply(response, 404, 'Fixture replay history unavailable.');
    if (mode === 'chart-missing' && /\/assets\/ReplayChart-.*\.js$/.test(pathname)) return reply(response, 404, 'Fixture chart chunk unavailable.');
    if (mode === 'viewer-missing' && /\/assets\/CrystalViewer-.*\.js$/.test(pathname)) return reply(response, 404, 'Fixture viewer chunk unavailable.');
    if (mode === 'stage-missing' && isAtomicStage) return reply(response, 404, 'Fixture atomic stage unavailable.');
    if (mode === 'image-missing' && pathname.endsWith('.png')) return reply(response, 404, 'Fixture image unavailable.');
    if (mode === 'ui-image-missing' && pathname.startsWith('/ui/figures/')) return reply(response, 404, 'Fixture presentation derivative unavailable.');
    let body = await fs.readFile(target);
    if (mode === 'ui-image-corrupt' && pathname.startsWith('/ui/figures/')) {
      body = Buffer.from(body); body[body.length - 1] ^= 1;
    }
    // Fault controls are injected only into loopback fixture responses. Neither
    // dist nor public bytes change, and these controls are never shipped.
    if (pathname === '/' || pathname === '/index.html') {
      let fixture = '';
      // Passive DOM/event observations only: no inputs, route mutation or
      // clock changes. Console observations let a full timed browser run be
      // audited without sampling every short scene. Never emitted into dist.
      if (mode === 'tour-observer') fixture = `document.addEventListener('DOMContentLoaded',()=>{let last='';const log=()=>{const caption=document.querySelector('.tour-caption')?.textContent;const heading=document.querySelector('.tour-heading')?.textContent;const key=caption+'|'+(heading?.includes('complete')?'complete':'');if(caption&&key!==last){last=key;requestAnimationFrame(()=>console.info('W6-TOUR-SCENE '+JSON.stringify({at:Date.now(),caption,heading,hash:location.hash,progress:document.querySelector('.guided-tour progress')?.value,selects:Array.from(document.querySelectorAll('select')).map(e=>({label:e.getAttribute('aria-label')||e.parentElement.textContent.slice(0,45),value:e.value}))})))}};new MutationObserver(log).observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['value']});document.addEventListener('click',e=>{const t=e.target.closest('button,a,input,select,summary');if(t)console.info('W6-TOUR-INPUT '+JSON.stringify({at:Date.now(),text:t.textContent?.slice(0,120),tag:t.tagName}))},true);log()});`;
      if (mode === 'no-webgl') fixture = `const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /^webgl/.test(type)?null:original.call(this,type,...args)};`;
      if (mode === 'renderer-error') fixture = `WebGL2RenderingContext.prototype.drawElements=function(){throw new Error('Loopback QA injected draw failure')};`;
      if (mode === 'reduced-motion') fixture = `const original=window.matchMedia.bind(window);window.matchMedia=query=>query==='(prefers-reduced-motion: reduce)'?{matches:true,media:query,onchange:null,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){},dispatchEvent(){return true}}:original(query);`;
      if (mode === 'viewer-context-loss') fixture = `document.addEventListener('DOMContentLoaded',()=>{const style='position:fixed;bottom:12px;right:12px;z-index:100;padding:14px';const b=document.createElement('button');b.textContent='W4 QA: lose WebGL context';b.style.cssText=style;b.onclick=()=>{const c=document.querySelector('canvas.crystal-canvas');const gl=c?.getContext('webgl2');const ext=gl?.getExtension('WEBGL_lose_context');if(ext)ext.loseContext();else b.textContent='W4 QA: context extension unavailable'};document.body.append(b);const t=document.createElement('button');t.textContent='W4 QA: test default touch pan';t.style.cssText=style+';bottom:70px';t.onclick=()=>{const c=document.querySelector('canvas.crystal-canvas');if(!c){t.textContent='W4 QA: touch test needs canvas';return}const r=c.getBoundingClientRect();const e=new PointerEvent('pointerdown',{bubbles:true,cancelable:true,pointerType:'touch',pointerId:99,clientX:r.left+10,clientY:r.top+10});const allowed=c.dispatchEvent(e);c.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerType:'touch',pointerId:99,clientX:r.left+10,clientY:r.top+160}));t.textContent=allowed&&getComputedStyle(c).touchAction==='pan-y'?'W4 QA: touch pan allowed; default not prevented':'W4 QA: touch pan check failed'};document.body.append(t)});`;
      if (fixture) body = Buffer.from(body.toString('utf8').replace('</head>', `<script>${fixture}</script></head>`));
    }
    if (isManifest && mode === 'corrupt' && body.length > 0) {
      body = Buffer.from(body);
      body[Math.max(0, body.length - 2)] ^= 1;
    }
    const type = mime[path.extname(target)] ?? 'application/octet-stream';
    if (request.method === 'HEAD') {
      response.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store', 'Content-Length': body.length, 'X-Content-Type-Options': 'nosniff' });
      return response.end();
    }
    reply(response, 200, body, type);
  } catch (error) {
    if (error instanceof URIError) return reply(response, 400, 'Invalid encoded path.');
    if (error.code === 'ENOENT' || error.code === 'EISDIR') return reply(response, 404, 'File unavailable.');
    console.error('QA fixture request failed:', error.message);
    reply(response, 500, 'Fixture request failed.');
  }
});
server.listen(port, '127.0.0.1', () => {
  console.log(`Website QA fixture: http://127.0.0.1:${port}/`);
  console.log(`Network mode file: ${modeFile}`);
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.close(() => process.exit(0)));
