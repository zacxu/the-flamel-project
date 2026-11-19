"""Verify the current deployment controls against Git and the sealed Phase 7 source."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_phase7 as previous

BASELINE = "29d692871540aa9d802a384f958e45ef20c5ea916b2b11bba1b2b622536904a7"


def verify(root, index, require_clean, seal, seal_sha256):
    integrity = previous.integrity
    baseline = integrity.checked_file(root, "publication/phase8/baseline-inputs.json")
    if integrity.sha256(baseline) != BASELINE:
        raise ValueError("Phase 7 baseline digest mismatch")
    names = integrity.records(integrity.load_json(baseline), "Phase 7 baseline")
    metadata = integrity.load_json(integrity.checked_file(root, "publication/phase8/control-paths.json"))
    previous.validate_controls(names, metadata)
    overlay = integrity.verify(root, seal, seal_sha256, metadata_dir="publication/phase8")
    selected = integrity.checked_file(root, "publication/git-files.txt").read_text(encoding="utf-8").splitlines()
    result = previous.git_bytes.verify_git_bytes(root, selected, index=index, require_clean=require_clean)
    result.update(publication_phase=8, baseline_sha256=BASELINE, overlay_mode=overlay["mode"],
                  baseline_files_verified=overlay["baseline_files_verified"], controls_unsealed=overlay["controls_unsealed"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--seal", type=Path)
    parser.add_argument("--seal-sha256")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.root.absolute(), args.index, args.require_clean, args.seal, args.seal_sha256), indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
