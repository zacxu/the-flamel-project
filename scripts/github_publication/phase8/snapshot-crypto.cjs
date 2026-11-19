// Version 1 encodes six fixed files in order. The envelope carries no pathnames.
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const magic = Buffer.from('FLAMELS1');
const nonceSize = 12;
const tagSize = 16;
const layout = [
  ['snapshot.json', 2_000_000],
  ['restored-package.json', 4_000_000],
  ['predecessor.zip', 110_000_000],
  ['rollback/.htaccess', 100_000],
  ['rollback/index.html', 1_000_000],
  ['rollback/research/manifest.json', 10_000_000],
];
const maxSize = layout.reduce((sum, [, limit]) => sum + 4 + limit, magic.length + nonceSize + tagSize);

function associatedData(source, run, attempt) {
  assert.match(source, /^[a-f0-9]{40}$/);
  assert.match(run, /^[1-9][0-9]{0,19}$/);
  assert.match(attempt, /^[1-9][0-9]{0,5}$/);
  return Buffer.from(JSON.stringify(['FLAMELS1', '1452978137', source, run, attempt]));
}

function filesBelow(root, prefix = '') {
  assert(fs.lstatSync(root).isDirectory(), 'Expected an ordinary snapshot directory');
  return fs.readdirSync(root, {withFileTypes: true}).flatMap(item => {
    const name = prefix + item.name;
    if (item.isDirectory()) {
      assert(layout.some(([wanted]) => wanted.startsWith(name + '/')), 'Unexpected snapshot directory');
      return filesBelow(path.join(root, item.name), name + '/');
    }
    assert(item.isFile(), 'Expected ordinary snapshot files');
    return name;
  });
}

function readBounded(filename, limit) {
  const info = fs.lstatSync(filename);
  assert(info.isFile() && info.size > 0 && info.size <= limit, 'Invalid snapshot file size or type');
  const data = fs.readFileSync(filename);
  assert.equal(data.length, info.size, 'Snapshot file changed during capture');
  return data;
}

function seal(directory, envelope, key, context) {
  assert.deepEqual(filesBelow(directory).sort(), layout.map(([name]) => name).sort(),
                   'Snapshot contains unexpected or missing paths');
  const nonce = crypto.randomBytes(nonceSize);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
  cipher.setAAD(context);
  const encrypted = [];
  for (const [name, limit] of layout) {
    const data = readBounded(path.join(directory, name), limit);
    const size = Buffer.alloc(4);
    size.writeUInt32BE(data.length);
    encrypted.push(cipher.update(size), cipher.update(data));
  }
  encrypted.push(cipher.final());
  fs.writeFileSync(envelope, Buffer.concat([magic, nonce, cipher.getAuthTag(), ...encrypted]),
                   {flag: 'wx', mode: 0o600});
}

function open(directory, envelope, key, context) {
  const input = readBounded(envelope, maxSize);
  const start = magic.length + nonceSize;
  assert(input.subarray(0, magic.length).equals(magic) && input.length > start + tagSize, 'Invalid envelope');
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, input.subarray(magic.length, start));
  decipher.setAAD(context);
  decipher.setAuthTag(input.subarray(start, start + tagSize));
  const plain = Buffer.concat([decipher.update(input.subarray(start + tagSize)), decipher.final()]);
  let offset = 0;
  const members = layout.map(([name, limit]) => {
    const size = plain.readUInt32BE(offset);
    offset += 4;
    assert(size > 0 && size <= limit && offset + size <= plain.length, 'Invalid authenticated member');
    const member = [name, plain.subarray(offset, offset + size)];
    offset += size;
    return member;
  });
  assert.equal(offset, plain.length, 'Unexpected data in snapshot');
  // Finish authentication and validate every member before creating any output.
  fs.mkdirSync(directory, {mode: 0o700});
  for (const [name, bytes] of members) {
    const destination = path.join(directory, name);
    fs.mkdirSync(path.dirname(destination), {recursive: true, mode: 0o700});
    fs.writeFileSync(destination, bytes, {flag: 'wx', mode: 0o600});
  }
}

function main() {
  const [command, directory, envelope, source, run, attempt] = process.argv.slice(2);
  assert(process.argv.length === 8 && ['seal', 'open'].includes(command),
         'Usage: node snapshot-crypto.cjs seal|open STATE-DIRECTORY ENVELOPE SOURCE-SHA RUN-ID ATTEMPT');
  const encoded = process.env.FLAMEL_ROLLBACK_KEY;
  if (typeof encoded !== 'string' || !/^[A-Za-z0-9+/]{43}=$/.test(encoded))
    throw new Error('Configure FLAMEL_ROLLBACK_KEY as 32 random bytes encoded in standard base64');
  const key = Buffer.from(encoded, 'base64');
  if (key.toString('base64') !== encoded) throw new Error('Invalid rollback key encoding');
  const context = associatedData(source, run, attempt);
  (command === 'seal' ? seal : open)(directory, envelope, key, context);
  console.log(command === 'seal' ? 'Encrypted six verified snapshot files' : 'Authenticated and restored six snapshot files');
}

if (require.main === module) {
  try { main(); }
  catch (error) {
    // Assertion details or low-level filesystem errors can contain host metadata.
    console.error('Snapshot encryption or authenticated recovery failed. Check the key, run identity and file set.');
    process.exitCode = 1;
  }
}
