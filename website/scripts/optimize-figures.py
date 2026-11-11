"""Lossless UI copies of two large frozen PNGs; no research file is written."""
from pathlib import Path
from PIL import Image
import hashlib
import json

w = Path(__file__).resolve().parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = json.loads((w / 'public/research/manifest.json').read_text(encoding='utf-8'))
out = w / 'public/ui/figures'
out.mkdir(parents=True, exist_ok=True)
rows = {}
for logical in ['figures/overview.png', 'figures/uncertainty.png']:
    record = next(e for e in manifest['files'] if e['logicalName'] == logical)
    original = w / 'public/research' / record['path']
    before = original.read_bytes()
    assert sha(before) == record['sha256']
    with Image.open(original) as image:
        # RGB is faithful for these fully opaque scientific plots. Verify the
        # exact decoded RGBA pixels afterwards, including opacity.
        rgba = image.convert('RGBA')
        assert rgba.getextrema()[3] == (255, 255)
        temp = out / (Path(logical).stem + '.pending.webp')
        image.convert('RGB').save(temp, 'WEBP', lossless=True, method=6)
    data = temp.read_bytes()
    with Image.open(temp) as optimized:
        assert optimized.size == rgba.size
        assert rgba.tobytes() == optimized.convert('RGBA').tobytes()
    name = Path(logical).stem + '.' + sha(data)[:16] + '.webp'
    target = out / name
    temp.replace(target)
    assert original.read_bytes() == before
    rows[logical] = {'path': 'ui/figures/' + name, 'sha256': sha(data),
                     'bytes': len(data), 'originalBytes': len(before),
                     'originalSha256': sha(before), 'width': rgba.width,
                     'height': rgba.height, 'pixelIdentical': True}

generated = w / 'src/generated/uiFigures.ts'
generated.parent.mkdir(parents=True, exist_ok=True)
generated.write_text('/** Lossless presentation derivatives; frozen originals remain in the research release. */\n'
                     + 'export const UI_FIGURES: Readonly<Record<string, { path: string; sha256: string; bytes: number; originalBytes: number; originalSha256: string; width: number; height: number; pixelIdentical: boolean }>> = '
                     + json.dumps(rows, indent=2) + ';\n', encoding='utf-8')
report = {'phase': 'W6', 'status': 'passed', 'format': 'lossless WebP',
          'originalFilesUnchanged': True, 'derivatives': rows}
(w / 'reports/W6_IMAGE_OPTIMIZATION.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
