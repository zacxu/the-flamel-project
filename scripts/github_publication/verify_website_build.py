"""Compare a clean website build with the pinned Phase 4 production-byte proof."""
import argparse
import hashlib
import json
from pathlib import Path

PROOF_SHA256 = "5463d492e1b96bf3b4841fdb2396e1d376174806fc566cb25eac2e9bf432a415"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        root = args.root
        proof = root / "reports/github-publication-phase4/website/fresh-build-byte-comparison.json"
        if digest(proof) != PROOF_SHA256:
            raise ValueError("Pinned build proof changed")
        rows = json.loads(proof.read_text(encoding="utf-8"))["files"]
        expected = {row["path"]: row for row in rows}
        dist = root / "website/dist"
        actual = {path.relative_to(dist).as_posix(): path for path in dist.rglob("*") if path.is_file()}
        if set(actual) != set(expected):
            raise ValueError("Build file set differs from the recorded plain build")
        for name, row in expected.items():
            path = actual[name]
            if path.is_symlink() or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
                raise ValueError("Build bytes differ: " + name)
        print(json.dumps({"passed": True, "build_files_verified": len(rows), "frozen_build_bytes_match": True}))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
