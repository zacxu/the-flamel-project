"""Scan an explicit publication allowlist; never print matched secret values."""
import argparse, hashlib, json, pathlib, shutil, stat, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def checked_name(name, basename=False):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("Unsafe path")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts) or name.startswith("/"):
        raise ValueError("Unsafe path")
    if basename and len(parts) != 1:
        raise ValueError("Archive must have one basename")
    return name

def no_reparse(path):
    for entry in (path, *path.parents):
        info = entry.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse point rejected")
    return path

def checked_file(base, name):
    checked_name(name)
    path = no_reparse(base / name)
    if not stat.S_ISREG(path.lstat().st_mode) or not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("Regular contained file required")
    return path

def scan(root, executable, work_parent, archive_dir=None):
    paths = root.joinpath("publication/git-files.txt").read_text(encoding="utf-8-sig").splitlines()
    if len(set(p.casefold() for p in paths)) != len(paths):
        raise ValueError("Duplicate/colliding allowlist paths")
    exceptions = json.loads(root.joinpath("publication/phase3/secret-review-exceptions.json").read_text())["findings"]
    for item in exceptions:
        checked_file(root, item["path"])
    with tempfile.TemporaryDirectory(prefix="flamel-secret-scan-", dir=work_parent) as tmp:
        scope = pathlib.Path(tmp)
        for rel in paths:
            source = checked_file(root, rel)
            target = scope / "git" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        archives = []
        if archive_dir:
            manifest = json.loads(root.joinpath("publication/artifacts.json").read_text())
            seen = set()
            for record in manifest["archives"]:
                name = checked_name(record["name"], basename=True)
                if name.casefold() in seen:
                    raise ValueError("Duplicate archive name")
                seen.add(name.casefold())
                source = checked_file(archive_dir, name)
                if source.stat().st_size != record["bytes"] or digest(source) != record["sha256"]:
                    raise ValueError("Archive does not match the frozen manifest")
                target = scope / "archives" / source.name
                target.parent.mkdir(exist_ok=True)
                shutil.copyfile(source, target)
                archives.append(record["name"])
        private_report = scope / "report-private.json"
        empty_ignore = scope / "empty-ignore"
        empty_ignore.write_text("")
        result = subprocess.run([
            str(executable), "dir", str(scope), "--config", str(root / ".gitleaks.toml"),
            "--ignore-gitleaks-allow", "--gitleaks-ignore-path", str(empty_ignore),
            "--redact=100", "--no-banner", "--no-color", "--max-archive-depth=5",
            "--max-decode-depth=5", "--report-format=json", "--report-path", str(private_report),
        ], capture_output=True)
        if result.returncode not in (0, 1) or not private_report.exists():
            raise RuntimeError("Scanner failed; no clearance produced")
        raw = json.loads(private_report.read_text(encoding="utf-8-sig"))
        reviewed = 0
        safe = []
        prefix = (scope / "git").as_posix() + "/"
        for finding in raw:
            name = finding["File"].replace("\\", "/")
            rel = name[len(prefix):] if name.startswith(prefix) else name
            # Binding to the whole file plus exact location prevents future broad suppression.
            accepted = any(
                rel == item["path"] and finding["RuleID"] == item["rule_id"]
                and finding["StartLine"] == item["start_line"] and finding["EndLine"] == item["end_line"]
                and digest(root / rel) == item["file_sha256"] for item in exceptions
            )
            reviewed += accepted
            safe.append({"path": rel, "rule": finding["RuleID"], "start_line": finding["StartLine"],
                         "reviewed_historical_worker_uuid": accepted})
        return {"scope_git_files": len(paths), "scope_archives": archives, "raw_findings": len(raw),
                "reviewed_worker_uuid_findings": reviewed, "unresolved_findings": len(raw) - reviewed,
                "result": "PASS" if len(raw) == reviewed else "REVIEW_REQUIRED", "findings": safe,
                "limits": "Pattern-based byte/text/archive scan; no OCR, pickle execution or guarantee of unknown-secret detection."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--gitleaks", type=pathlib.Path, required=True)
    parser.add_argument("--work-dir", type=pathlib.Path, required=True, help="Existing private scratch directory outside the project")
    parser.add_argument("--archive-dir", type=pathlib.Path, help="Optional exact 14 local Phase 2 archives")
    parser.add_argument("--report", type=pathlib.Path, help="Safe metadata-only JSON output, outside scanned scope")
    args = parser.parse_args()
    try:
        root = no_reparse(args.root.absolute()).resolve()
        work = no_reparse(args.work_dir.absolute()).resolve()
        archive_dir = no_reparse(args.archive_dir.absolute()).resolve() if args.archive_dir else None
        if args.report:
            report = args.report.absolute()
            no_reparse(report.parent)
            if report.exists() or report.resolve().is_relative_to(root) or (
                archive_dir and report.resolve().is_relative_to(archive_dir)
            ):
                raise ValueError("Report must be a new private output outside project/archive inputs")
        if work.is_relative_to(root) or not work.is_dir():
            raise ValueError("Use an existing private scratch directory outside the project")
        summary = scan(root, args.gitleaks.resolve(), work, archive_dir)
        if args.report:
            args.report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in summary.items() if k != "findings"}))
        return 0 if summary["result"] == "PASS" else 1
    except Exception as error:
        # Exception type only: input paths/third-party exception text can contain secrets.
        print(json.dumps({"result": "ERROR", "exception_type": type(error).__name__}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
