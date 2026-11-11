"""Read-only Phase 3 publication integrity gate. Standard library only.

Default mode checks the frozen baseline and explicitly reports new/modified
controls as unsealed. An external complete seal checks every selected byte;
--seal-sha256 additionally binds that seal to an independently trusted digest.
This program never initializes Git, stages files, writes reports, or edits files.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_GIT_BYTES = 50 * 1024 * 1024
# Frozen public npm configuration contains only noncredential build settings.
PUBLIC_NPMRC_PATH = 'website/.npmrc'
PUBLIC_NPMRC_SHA256 = 'effaf00bcea6979a2f9fc048c561cc7b36664d87276d6b3bfb14ad2f87bee427'
EXPECTED_EXCEPTIONS = frozenset({
    'vendor/CrystalFormer/crystalformer/data/.gitkeep',
    'vendor/CrystalFormer/crystalformer/data/wyckoff_list.csv',
    'vendor/CrystalFormer/crystalformer/data/wyckoff_symbols.csv',
    'vendor/CrystalFormer/data/atoms.json',
    'vendor/CrystalFormer/data/mini.csv',
    'vendor/CrystalFormer/scripts/analysis.ipynb',
    'vendor/CrystalFormer/scripts/inspect_dataset.ipynb',
    'vendor/CrystalFormer/scripts/structure_visualization.ipynb',
})
VENDOR_IGNORE = 'vendor/CrystalFormer/.gitignore'
VENDOR_IGNORE_SHA256 = 'def82801b533ea347b3d2361f684f3561aad1040c9f8bd21c1eb7ef1c40516ec'
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
RESERVED = re.compile(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z', re.I)

class VerificationError(ValueError):
    """A metadata, path-safety, or byte-integrity gate failed."""

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def checked_name(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise VerificationError('Invalid empty or whitespace-bounded relative path')
    if '\\' in value or ':' in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise VerificationError('Unsafe path syntax: ' + value)
    parts = value.split('/')
    if any(x in ('', '.', '..') or x.endswith(('.', ' ')) or RESERVED.fullmatch(x) for x in parts):
        raise VerificationError('Unsafe relative path: ' + value)
    if any(x.casefold() == '.git' for x in parts):
        raise VerificationError('Git metadata cannot be selected: ' + value)
    return value

def is_secret_path(path: str) -> bool:
    for part in path.lower().split('/'):
        if part in ('.env.example', '.env.template', '.npmrc.example'):
            continue
        if part == '.env' or part.startswith('.env.') or part in {
            '.npmrc', '.ssh', '.aws', '.azure', 'id_rsa', 'id_dsa',
            'id_ecdsa', 'id_ed25519', 'credentials.json', 'secrets.json',
            'tokens.json', 'service-account.json',
        } or part.endswith(('.pem', '.key', '.p12', '.pfx')):
            return True
    return False

def checked_names(values: object, label: str, *, secrets: bool = False) -> list[str]:
    if not isinstance(values, list):
        raise VerificationError(label + ' must be an array')
    out, seen = [], {}
    for value in values:
        path = checked_name(value)
        key = path.casefold()
        if key in seen:
            raise VerificationError(label + ' has duplicate or case-colliding paths: ' + path)
        if secrets and is_secret_path(path) and path != PUBLIC_NPMRC_PATH:
            raise VerificationError('Secret-like selected path: ' + path)
        seen[key] = path
        out.append(path)
    return out

def checked_file(root: Path, relative: str, *, optional: bool = False) -> Path | None:
    checked_name(relative)
    current = root
    for index, component in enumerate(relative.split('/')):
        current = current / component
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            if optional:
                return None
            raise VerificationError('Missing selected/metadata file: ' + relative) from None
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise VerificationError('Symlink or reparse path rejected: ' + relative)
        final = index == len(relative.split('/')) - 1
        if not final and not stat.S_ISDIR(info.st_mode):
            raise VerificationError('Non-directory ancestor: ' + relative)
        if final and not stat.S_ISREG(info.st_mode):
            raise VerificationError('Non-regular file rejected: ' + relative)
    if not current.resolve().is_relative_to(root):
        raise VerificationError('Path escapes project root: ' + relative)
    return current

def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError('Duplicate JSON object key: ' + key)
        result[key] = value
    return result

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError('Invalid JSON metadata: ' + path.name) from error

def records(document, label: str) -> dict[str, dict]:
    items = document.get('files') if isinstance(document, dict) else document
    if not isinstance(items, list):
        raise VerificationError(label + ' must contain a files array')
    if any(not isinstance(row, dict) for row in items):
        raise VerificationError(label + ' has non-object file entries')
    names = checked_names([row.get('path') for row in items], label)
    result = {}
    for name, row in zip(names, items):
        size, digest = row.get('bytes'), row.get('sha256')
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise VerificationError(label + ' has invalid byte count: ' + name)
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise VerificationError(label + ' has invalid SHA256: ' + name)
        result[name] = row
    return result

def match_bytes(root: Path, row: dict, *, optional: bool = False) -> bool:
    path = checked_file(root, row['path'], optional=optional)
    if path is None:
        return False
    if path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
        raise VerificationError('Byte integrity mismatch: ' + row['path'])
    return True

def verify(root: Path, seal: Path | None = None, seal_sha256: str | None = None, *, metadata_dir: str = 'publication/phase3') -> dict:
    # Reject root junctions/symlinks before resolving them, not just escapes.
    root = root.absolute()
    for ancestor in (root, *root.parents):
        info = os.lstat(ancestor)
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise VerificationError('Project root or ancestor is a symlink or reparse point')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise VerificationError('Project root must be a directory')
    if seal_sha256 and seal is None:
        raise VerificationError('--seal-sha256 requires --seal')
    listpath = checked_file(root, 'publication/git-files.txt')
    selected = checked_names(listpath.read_text(encoding='utf-8').splitlines(), 'Git allowlist', secrets=True)
    chosen = set(selected)
    if not selected:
        raise VerificationError('Git allowlist is empty')
    pathspec = checked_file(root, 'publication/git-pathspec.nul')
    expected_pathspec = b''.join(b':(literal)' + p.encode('utf-8') + b'\0' for p in selected)
    if pathspec.read_bytes() != expected_pathspec:
        raise VerificationError('Literal NUL pathspec differs from exact ordered Git allowlist')
    baseline_path = checked_file(root, metadata_dir + '/baseline-inputs.json')
    baseline = records(load_json(baseline_path), 'Frozen baseline')
    control_path = checked_file(root, metadata_dir + '/control-paths.json')
    control = load_json(control_path)
    if not isinstance(control, dict):
        raise VerificationError('Control-paths metadata must be an object')
    controls = set(checked_names(control.get('paths'), 'Control paths', secrets=True))
    modified = set(checked_names(control.get('modified_frozen_input_paths', []), 'Modified frozen paths'))
    withheld = set(checked_names(control.get('withheld_private_paths', []), 'Withheld private paths'))
    if not modified <= controls & set(baseline):
        raise VerificationError('Modified frozen paths must be declared baseline controls')
    if withheld & controls or not withheld <= set(baseline):
        raise VerificationError('Withheld paths must be original baseline files outside controls')
    # The declaration must cover every baseline control, so bytes are never skipped implicitly.
    if controls & set(baseline) != modified:
        raise VerificationError('Baseline/control overlap must equal explicit modified frozen paths')
    expected = (set(baseline) - withheld) | controls
    if chosen != expected:
        raise VerificationError('Git allowlist differs from baseline plus declared controls/withholding')
    checked_names(sorted(set(baseline) | controls), 'Combined baseline/control namespace')
    for p in selected:
        actual = checked_file(root, p)
        if p == PUBLIC_NPMRC_PATH and sha256(actual) != PUBLIC_NPMRC_SHA256:
            raise VerificationError('Public npmrc differs from exact reviewed bytes: ' + p)
        if actual.stat().st_size > MAX_GIT_BYTES:
            raise VerificationError('Selected file exceeds 50 MiB policy: ' + p)
    baseline_verified = 0
    for p, row in baseline.items():
        if p not in modified and p not in withheld:
            match_bytes(root, row)
            baseline_verified += 1
    withheld_verified = sum(match_bytes(root, baseline[p], optional=True) for p in withheld)
    exceptions_path = checked_file(root, 'publication/phase3/upstream-ignore-exceptions.json')
    exceptions_doc = load_json(exceptions_path)
    exceptions = records(exceptions_doc, 'Upstream ignore exceptions')
    if set(exceptions) != EXPECTED_EXCEPTIONS or not EXPECTED_EXCEPTIONS <= chosen:
        raise VerificationError('Upstream ignore exceptions must be exactly the eight reviewed originals')
    if not isinstance(exceptions_doc, dict) or exceptions_doc.get('unchanged_nested_ignore_sha256') != VENDOR_IGNORE_SHA256:
        raise VerificationError('Upstream ignore exception metadata has wrong nested ignore digest')
    vendor_ignore = checked_file(root, VENDOR_IGNORE)
    if sha256(vendor_ignore) != VENDOR_IGNORE_SHA256:
        raise VerificationError('Original upstream .gitignore changed')
    source_manifest = checked_file(root, 'publication/git-input-files.json')
    if exceptions_doc.get('source_manifest_sha256') != sha256(source_manifest):
        raise VerificationError('Upstream exception source manifest digest mismatch')
    for p, row in exceptions.items():
        if p not in baseline or any(row[k] != baseline[p][k] for k in ('bytes', 'sha256')):
            raise VerificationError('Upstream exception differs from frozen baseline: ' + p)
        match_bytes(root, row)
    force_paths = checked_file(root, 'publication/phase3/upstream-ignore-force-paths.txt')
    force_names = checked_names(force_paths.read_text(encoding='utf-8').splitlines(), 'Force-path exceptions')
    if set(force_names) != EXPECTED_EXCEPTIONS:
        raise VerificationError('Force-path list differs from reviewed upstream exceptions')
    force_spec = checked_file(root, 'publication/phase3/upstream-ignore-force-pathspec.nul')
    if force_spec.read_bytes() != b''.join(b':(literal)' + p.encode() + b'\0' for p in force_names):
        raise VerificationError('Force-path NUL pathspec differs from exact exception list')
    result = {'passed': True, 'mode': 'baseline-only-unsealed-controls',
        'selected_files': len(selected), 'baseline_files_verified': baseline_verified,
        'declared_controls': len(controls), 'controls_unsealed': True,
        'withheld_originals_present_and_unchanged': withheld_verified,
        'withheld_originals_absent': len(withheld) - withheld_verified,
        'upstream_ignore_exceptions': len(exceptions), 'source_mutations': False,
        'note': 'Default mode does not authenticate new/modified controls; use an external complete seal.'}
    if seal is not None:
        seal_digest = sha256(seal)
        if seal_sha256 and (not DIGEST.fullmatch(seal_sha256) or seal_digest != seal_sha256):
            raise VerificationError('External seal SHA256 differs from trusted digest')
        sealed = records(load_json(seal), 'External complete seal')
        if set(sealed) != chosen:
            raise VerificationError('External complete seal differs from exact selected file set')
        for row in sealed.values():
            match_bytes(root, row)
        result.update(mode='complete-external-seal', controls_unsealed=False,
            seal_sha256=seal_digest, trusted_seal_digest_supplied=seal_sha256 is not None,
            sealed_files_verified=len(sealed), note='Every selected file matches the external seal; authenticity depends on independently trusting its digest.')
    return result

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--seal', type=Path)
    parser.add_argument('--seal-sha256')
    args = parser.parse_args(argv)
    try:
        result = verify(args.root, args.seal, args.seal_sha256)
    except (VerificationError, OSError, UnicodeError) as error:
        print(json.dumps({'passed': False, 'error': str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
