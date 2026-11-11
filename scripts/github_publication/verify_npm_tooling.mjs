/** Verify cached npm bytes before executing its CLI. Standard-library Node only. */
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
const expected = 'sha512-bKCmFRVT/BB+YPEYbZwQ1XUI3N5t4xKSpU1MxOjo7z3iWzKBJ0ZXRC1xFdEN+TC7N5TdywaBzf2dMXGJq/e2PQ==';
const website = path.resolve(process.argv[2] ?? '');
const archive = path.join(website, '.tooling', 'npm-12.2.1.tgz');
const folder = path.join(website, '.tooling', 'npm');
function check(condition) { if (!condition) throw new Error('Pinned npm tooling integrity check failed. Use a clean source copy.'); }
function noLinks(file) {
  for (let current = file; ; current = path.dirname(current)) {
    check(!fs.lstatSync(current).isSymbolicLink());
    if (path.dirname(current) === current) break;
  }
}
noLinks(archive); noLinks(folder);
const packed = fs.readFileSync(archive);
check('sha512-' + crypto.createHash('sha512').update(packed).digest('base64') === expected);
const tar = zlib.gunzipSync(packed, { maxOutputLength: 32 * 1024 * 1024 });
const wanted = new Map();
const text = bytes => bytes.toString('utf8').replace(/\0.*$/s, '');
for (let cursor = 0; cursor + 512 <= tar.length;) {
  const header = tar.subarray(cursor, cursor + 512);
  if (header.every(value => value === 0)) break;
  const number = bytes => {
    const value = text(bytes).trim();
    check(/^[0-7]+$/.test(value));
    return Number.parseInt(value, 8);
  };
  const checksum = number(header.subarray(148, 156));
  check(header.reduce((sum, byte, index) => sum + (index >= 148 && index < 156 ? 32 : byte), 0) === checksum);
  const size = number(header.subarray(124, 136));
  const type = String.fromCharCode(header[156]);
  const prefix = text(header.subarray(345, 500));
  const name = (prefix ? prefix + '/' : '') + text(header.subarray(0, 100));
  check(type === '0' && name.startsWith('package/') && !name.includes('\\') && !name.includes(':'));
  const relative = name.slice(8);
  check(relative && relative.split('/').every(part => part && part !== '.' && part !== '..'));
  check(cursor + 512 + size <= tar.length);
  check(!wanted.has(relative.toLowerCase()));
  const installed = path.join(folder, relative);
  noLinks(installed);
  check(fs.statSync(installed).isFile());
  const original = tar.subarray(cursor + 512, cursor + 512 + size);
  check(crypto.createHash('sha256').update(fs.readFileSync(installed)).digest('hex') === crypto.createHash('sha256').update(original).digest('hex'));
  wanted.set(relative.toLowerCase(), true);
  cursor += 512 + Math.ceil(size / 512) * 512;
}
let observed = 0;
function walk(directory, prefix = '') {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    check(!entry.isSymbolicLink());
    const relative = prefix ? prefix + '/' + entry.name : entry.name;
    if (entry.isDirectory()) walk(path.join(directory, entry.name), relative);
    else { check(entry.isFile() && wanted.has(relative.toLowerCase())); observed += 1; }
  }
}
walk(folder);
check(wanted.size === 1942 && observed === wanted.size);
console.log(JSON.stringify({ npm: '12.2.1', archive_integrity_verified: true, installed_files_verified: observed }));
