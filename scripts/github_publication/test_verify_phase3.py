"""Focused read-only publication-integrity regressions using disposable data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import os
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location('phase3_verifier', Path(__file__).with_name('verify_phase3.py'))
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)
VENDOR = b'*.png\njob*\n*.out\n__pycache__/\ndata/\nexperimental/\n*.ipynb\n*.egg-info/\nbuild/\n!imgs/*.png\n.vscode/'

PUBLIC_NPMRC = b'save-exact=true\nengine-strict=true\nfund=false\nupdate-notifier=false\ncache=.cache/npm\n'

def entry(root, path):
    data = (root / path).read_bytes()
    return {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def put(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value)

def putjson(root, path, value):
    put(root, path, (json.dumps(value, indent=2) + '\n').encode())

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='flamel-verifier-case-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'project'
        self.root.mkdir()
        put(self.root, v.VENDOR_IGNORE, VENDOR)
        for index, name in enumerate(sorted(v.EXPECTED_EXCEPTIONS)):
            put(self.root, name, b'original-' + str(index).encode())
        put(self.root, 'source.txt', b'line1\r\nline2\nlast')
        put(self.root, 'evidence.bin', b'\x00\xff\r\n\x80binary')
        put(self.root, 'private-original.txt', b'original withheld evidence')
        put(self.root, '.gitignore', b'original policy\n')
        put(self.root, v.PUBLIC_NPMRC_PATH, PUBLIC_NPMRC)
        baseline_names = sorted(v.EXPECTED_EXCEPTIONS | {v.VENDOR_IGNORE, 'source.txt', 'evidence.bin', 'private-original.txt', '.gitignore', v.PUBLIC_NPMRC_PATH})
        baseline = [entry(self.root, name) for name in baseline_names]
        putjson(self.root, 'publication/git-input-files.json', baseline)
        putjson(self.root, 'publication/phase3/baseline-inputs.json', {'files': baseline})
        put(self.root, '.gitignore', b'reviewed current policy\n')
        put(self.root, '.gitattributes', b'* -text\n')
        put(self.root, 'new-control.txt', b'new metadata\n')
        controls = ['.gitignore', '.gitattributes', 'new-control.txt', 'publication/git-files.txt',
            'publication/git-pathspec.nul', 'publication/git-input-files.json',
            'publication/phase3/baseline-inputs.json', 'publication/phase3/control-paths.json',
            'publication/phase3/upstream-ignore-exceptions.json',
            'publication/phase3/upstream-ignore-force-paths.txt',
            'publication/phase3/upstream-ignore-force-pathspec.nul']
        putjson(self.root, 'publication/phase3/control-paths.json', {'paths': controls,
            'modified_frozen_input_paths': ['.gitignore'], 'withheld_private_paths': ['private-original.txt']})
        exceptions = [entry(self.root, name) for name in sorted(v.EXPECTED_EXCEPTIONS)]
        putjson(self.root, 'publication/phase3/upstream-ignore-exceptions.json', {'files': exceptions,
            'unchanged_nested_ignore_sha256': v.VENDOR_IGNORE_SHA256,
            'source_manifest_sha256': v.sha256(self.root/'publication/git-input-files.json')})
        put(self.root, 'publication/phase3/upstream-ignore-force-paths.txt', ('\n'.join(sorted(v.EXPECTED_EXCEPTIONS))+'\n').encode())
        put(self.root, 'publication/phase3/upstream-ignore-force-pathspec.nul', b''.join(b':(literal)'+p.encode()+b'\0' for p in sorted(v.EXPECTED_EXCEPTIONS)))
        self.selected = sorted((set(baseline_names) - {'private-original.txt'}) | set(controls))
        self.write_selection(self.selected)
        self.seal = self.base / 'external-seal.json'
        self.seal.write_text(json.dumps({'files': [entry(self.root, name) for name in self.selected]}))
        self.seal_digest = v.sha256(self.seal)

    def write_selection(self, names):
        put(self.root, 'publication/git-files.txt', ('\n'.join(names)+'\n').encode())
        put(self.root, 'publication/git-pathspec.nul', b''.join(b':(literal)'+p.encode()+b'\0' for p in names))

    def rejects(self, phrase, **kwargs):
        with self.assertRaisesRegex(v.VerificationError, phrase):
            v.verify(self.root, **kwargs)
        self.assertFalse((self.root / '.git').exists())

    def test_positive_mixed_and_binary_bytes_external_seal(self):
        before = {p: (self.root/p).read_bytes() for p in self.selected}
        result = v.verify(self.root, self.seal, self.seal_digest)
        self.assertTrue(result['passed'])
        self.assertFalse(result['controls_unsealed'])
        self.assertTrue(result['trusted_seal_digest_supplied'])
        self.assertEqual(before, {p: (self.root/p).read_bytes() for p in self.selected})
        self.assertFalse((self.root/'.git').exists())

    def test_default_explicitly_reports_controls_unsealed(self):
        result = v.verify(self.root)
        self.assertTrue(result['controls_unsealed'])
        self.assertEqual(result['mode'], 'baseline-only-unsealed-controls')

    def test_baseline_tamper_rejected(self):
        put(self.root, 'evidence.bin', b'changed')
        self.rejects('Byte integrity mismatch')

    def test_control_tamper_requires_external_seal(self):
        put(self.root, 'new-control.txt', b'tampered control')
        self.assertTrue(v.verify(self.root)['controls_unsealed'])
        self.rejects('Byte integrity mismatch', seal=self.seal, seal_sha256=self.seal_digest)

    def test_traversal_rejected(self):
        self.write_selection(self.selected + ['../outside.txt'])
        self.rejects('Unsafe relative path')

    def test_duplicate_allowlist_rejected(self):
        self.write_selection(self.selected + [self.selected[0]])
        self.rejects('duplicate or case-colliding')

    def test_case_collision_rejected(self):
        self.write_selection(self.selected + ['SOURCE.TXT'])
        self.rejects('duplicate or case-colliding')

    def test_missing_selected_file_rejected(self):
        (self.root/'source.txt').unlink()
        self.rejects('Missing selected/metadata')

    def test_unexpected_allowlist_entry_rejected(self):
        put(self.root, 'unexpected.py', b'print(1)\n')
        self.write_selection(self.selected+['unexpected.py'])
        self.rejects('differs from baseline plus declared controls')

    def test_wrong_trusted_seal_hash_rejected(self):
        self.rejects('trusted digest', seal=self.seal, seal_sha256='0'*64)

    def test_incomplete_external_seal_rejected(self):
        document = json.loads(self.seal.read_text())
        document['files'].pop()
        self.seal.write_text(json.dumps(document))
        self.rejects('External complete seal differs', seal=self.seal)

    def test_duplicate_external_seal_entry_rejected(self):
        document = json.loads(self.seal.read_text())
        document['files'].append(document['files'][0])
        self.seal.write_text(json.dumps(document))
        self.rejects('duplicate or case-colliding', seal=self.seal)

    def test_pathspec_tamper_rejected(self):
        put(self.root, 'publication/git-pathspec.nul', b':(literal)source.txt\0')
        self.rejects('Literal NUL pathspec')

    def test_new_secret_path_rejected_before_allowlist_comparison(self):
        put(self.root, 'nested/.env', b'fixture only')
        self.write_selection(self.selected+['nested/.env'])
        self.rejects('Secret-like selected path')

    def test_secret_example_paths_permitted(self):
        self.assertFalse(v.is_secret_path('nested/.env.example'))
        self.assertFalse(v.is_secret_path('nested/.env.template'))
        self.assertFalse(v.is_secret_path('.npmrc.example'))
        self.assertTrue(v.is_secret_path('nested/private.key'))

    def test_public_npmrc_changed_bytes_rejected(self):
        put(self.root, v.PUBLIC_NPMRC_PATH, PUBLIC_NPMRC+b'\nchanged-public-config=true\n')
        self.rejects('Public npmrc differs from exact reviewed bytes')

    def test_other_npmrc_paths_are_secret_like(self):
        put(self.root, '.npmrc', PUBLIC_NPMRC)
        self.write_selection(self.selected+['.npmrc'])
        self.rejects('Secret-like selected path')

    def test_withheld_original_not_modified(self):
        put(self.root, 'private-original.txt', b'changed original')
        self.rejects('Byte integrity mismatch')

    def test_withheld_original_may_be_absent_in_clone(self):
        (self.root/'private-original.txt').unlink()
        self.assertEqual(v.verify(self.root)['withheld_originals_absent'], 1)

    def test_force_exception_cannot_expand(self):
        path=self.root/'publication/phase3/upstream-ignore-exceptions.json'
        document=json.loads(path.read_text())
        document['files'][0]['path']='vendor/CrystalFormer/mcp/.env'
        path.write_text(json.dumps(document))
        self.rejects('exactly the eight reviewed originals')

    def test_frozen_vendor_ignore_must_remain_identical(self):
        put(self.root, v.VENDOR_IGNORE, VENDOR+b'\nnew rule\n')
        self.rejects('Byte integrity mismatch|Original upstream')

    def test_large_selected_file_rejected(self):
        with (self.root/'source.txt').open('wb') as handle:
            handle.truncate(v.MAX_GIT_BYTES+1)
        self.rejects('exceeds 50 MiB')

    def test_symlink_file_rejected_when_os_supports_creation(self):
        target=self.base/'outside.bin';target.write_bytes(b'outside')
        (self.root/'source.txt').unlink()
        try:
            (self.root/'source.txt').symlink_to(target)
        except OSError:
            self.skipTest('OS does not permit creating test symlinks')
        self.rejects('Symlink or reparse')

    def test_reparse_ancestor_rejected_even_if_resolving_inside_root(self):
        original=os.lstat
        ancestor=self.root/'vendor'/'CrystalFormer'
        def altered(path,*args,**kwargs):
            result=original(path,*args,**kwargs)
            if Path(path)==ancestor:
                return SimpleNamespace(st_mode=result.st_mode,st_file_attributes=0x400)
            return result
        with mock.patch.object(v.os,'lstat',side_effect=altered):
            self.rejects('Symlink or reparse')

    def test_duplicate_json_keys_rejected(self):
        put(self.root,'publication/phase3/control-paths.json',b'{"paths":[],"paths":[]}')
        self.rejects('Duplicate JSON object key')

if __name__ == '__main__':
    unittest.main(verbosity=2)
