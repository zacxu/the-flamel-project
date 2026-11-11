"""Verify the current Phase 4 publication overlay; no writes or research execution."""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("flamel_integrity", Path(__file__).with_name("verify_phase3.py"))
integrity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrity)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--seal", type=Path)
    parser.add_argument("--seal-sha256")
    args = parser.parse_args()
    try:
        result = integrity.verify(args.root, args.seal, args.seal_sha256, metadata_dir="publication/phase4")
    except (integrity.VerificationError, OSError, UnicodeError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1
    result["publication_phase"] = 4
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
