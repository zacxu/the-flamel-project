"""Install the exact reviewed actionlint binary outside the checkout and lint workflows."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request
import zipfile

VERSION = "1.7.12"
ASSETS = {
    "Windows": ("windows_amd64.zip", "6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9", "actionlint.exe"),
    "Linux": ("linux_amd64.tar.gz", "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8", "actionlint"),
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--tool-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    destination = args.tool_root.absolute()
    if destination.exists() or destination.resolve().is_relative_to(root):
        parser.error("tool-root must be a new directory outside the checkout")
    if platform.machine().lower() not in ("amd64", "x86_64") or platform.system() not in ASSETS:
        parser.error("reviewed binary is available for Windows/Linux x64 only")
    archive_name, digest, executable = ASSETS[platform.system()]
    filename = "actionlint_" + VERSION + "_" + archive_name
    url = "https://github.com/rhysd/actionlint/releases/download/v" + VERSION + "/" + filename
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("actionlint archive differs from the official pinned release digest")
    destination.mkdir(parents=True, exist_ok=False)
    archive_path = destination / filename
    archive_path.write_bytes(data)
    if filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            executable_bytes = archive.read(executable)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            member = archive.getmember(executable)
            if not member.isfile():
                raise ValueError("Nonregular actionlint executable")
            executable_bytes = archive.extractfile(member).read()
    tool = destination / executable
    tool.write_bytes(executable_bytes)
    if os.name != "nt":
        tool.chmod(0o755)
    receipt = {"version": VERSION, "url": url, "archive_sha256": digest,
               "binary_sha256": hashlib.sha256(executable_bytes).hexdigest(),
               "tool_destination": str(tool)}
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    workflows = sorted((root / ".github/workflows").glob("*.yml"))
    if not workflows:
        raise ValueError("No workflows selected")
    result = subprocess.run([str(tool), "-shellcheck=", "-pyflakes=", *map(str, workflows)], cwd=root)
    if result.returncode:
        return result.returncode
    print(json.dumps({"passed": True, "workflow_files": len(workflows), **receipt}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
