"""Check the Phase 6 overlay, frozen Phase 5 inputs and exact Git/source bytes.

The complete Phase 5 seal is an immutable baseline. Only explicitly declared
Phase 6 control paths may differ. Current controls are compared against Git;
an optional independently trusted external seal authenticates every byte.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
from pathlib import Path
import subprocess

BASELINE_SHA256 = "4fabbe07897ff83410651d24b43a6916270160ccd122a8e853fde014376396f7"
BASELINE_COMMIT = "f592e0c13888bfc62ff55413c91dc0721b6b35cb"

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

integrity = load("phase6_integrity", "verify_phase3.py")
git_bytes = load("phase6_git_bytes", "verify_git_publication.py")

ROOT_CONTROLS = frozenset({
    ".github/workflows/initial-ci.yml", "GITHUB_CICD_PUBLICATION_PLAN.md",
    "README.md", "INSTALLATION.md", "publication/README.md", "publication/RETRIEVAL.md",
    "publication/backup-paths.json", "publication/generated-control-paths.json",
    "publication/storage-summary.json", "publication/git-files.txt", "publication/git-pathspec.nul",
})
WEBSITE_CONFIGS = frozenset({
    "website/package.json", "website/package-lock.json", "website/tsconfig.json",
    "website/tsconfig.node.json", "website/vite.config.ts",
})
SOURCE_SUFFIXES = frozenset({".ts", ".tsx", ".css", ".svg", ".js", ".mjs", ".py", ".ps1"})

def mutable_baseline_path(name):
    integrity.checked_name(name)
    if name in ROOT_CONTROLS or name in WEBSITE_CONFIGS:
        return True
    if name.startswith(("website/src/", "website/scripts/")) and Path(name).suffix in SOURCE_SUFFIXES:
        return True
    if re.fullmatch(r"research_[A-Za-z0-9_]+\.py", name) or re.fullmatch(r"scripts/phase[A-Za-z0-9_]+\.py", name):
        return True
    return name.startswith("scripts/github_publication/") and Path(name).suffix in {".py", ".ps1"}

def validate_controls(baseline_names, control_document):
    if not isinstance(control_document, dict):
        raise ValueError("Control metadata must be an object")
    controls = set(integrity.checked_names(control_document.get("paths"), "Phase 6 controls", secrets=True))
    if control_document.get("withheld_private_paths", []):
        raise ValueError("Phase 6 cannot remove or withhold a published baseline input")
    denied = {name for name in controls & set(baseline_names) if not mutable_baseline_path(name)}
    if denied:
        raise ValueError("Frozen evidence/configuration cannot be exempted through control metadata: " + sorted(denied)[0])
    return controls

def verify(root, *, index=False, require_clean=False, seal=None, seal_sha256=None):
    root = root.absolute()
    baseline = integrity.checked_file(root, "publication/phase6/baseline-inputs.json")
    if integrity.sha256(baseline) != BASELINE_SHA256:
        raise ValueError("Phase 5 baseline seal changed")
    baseline_names = integrity.records(integrity.load_json(baseline), "Pinned Phase 5 baseline")
    control = integrity.load_json(integrity.checked_file(root, "publication/phase6/control-paths.json"))
    validate_controls(baseline_names, control)
    overlay = integrity.verify(root, seal, seal_sha256, metadata_dir="publication/phase6")
    names = integrity.checked_file(root, "publication/git-files.txt").read_text(encoding="utf-8").splitlines()
    result = git_bytes.verify_git_bytes(root, names, index=index, require_clean=require_clean)
    result.update(publication_phase=6, frozen_baseline_commit=BASELINE_COMMIT,
                  frozen_baseline_sha256=BASELINE_SHA256,
                  baseline_files_verified=overlay["baseline_files_verified"],
                  controls_unsealed=overlay["controls_unsealed"], overlay_mode=overlay["mode"])
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--seal", type=Path)
    parser.add_argument("--seal-sha256")
    args = parser.parse_args()
    try:
        result = verify(args.root, index=args.index, require_clean=args.require_clean,
                        seal=args.seal, seal_sha256=args.seal_sha256)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
