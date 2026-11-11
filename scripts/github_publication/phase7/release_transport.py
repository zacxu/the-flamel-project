"""Scoped GitHub Release transport using normal gh authentication; never reads credentials.

The repository remains private. The helper never clobbers assets, edits tags,
logs authentication values, or makes an incomplete release public.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

REPOSITORY = "zacxu/the-flamel-project"
MAX_EXTRA = 100 * 1024 * 1024
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,180}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
COMMIT = re.compile(r"[a-f0-9]{40}\Z")
TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-.][A-Za-z0-9.-]+)?\Z")
SELECTOR_SHA256 = "af567654dbd3693221194d168be5c7a402005a9a80a05b6d317346b8f007ed4d"
SELECTION_SHA256 = "55302f3aa35af7947ac78c4780c57ab3d336a4a1a9b49b222efcf4453669703d"

def require(value, message):
    if not value:
        raise ValueError(message)

def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()

def unique(items):
    out = {}
    for key, value in items:
        require(key not in out, "Duplicate JSON key")
        out[key] = value
    return out

def document(path):
    return json.loads(regular(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique)

def regular(path):
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        if parent.exists() or parent.is_symlink():
            info = parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                    "Linked/reparse path rejected")
    require(path.is_file(), "Expected a regular file")
    return path

def new_output(path, root):
    path = Path(path).absolute()
    require(not path.exists() and not path.is_symlink(), "Output must be new")
    require(not path.resolve().is_relative_to(Path(root).resolve()), "Output must be outside source checkout")
    for parent in path.parents:
        if parent.exists():
            info = parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                    "Linked output parent rejected")
    return path

def policy(root):
    selector = regular(Path(root) / "publication/phase4/public-assets.json")
    selection = regular(Path(root) / "publication/phase3/release-selection.json")
    require(digest(selector) == SELECTOR_SHA256 and digest(selection) == SELECTION_SHA256,
            "Historical release policy changed")
    required = {row["name"]: row for row in document(selector)["archives"]}
    private = {row["name"]: row for row in document(selection)["archives"]
               if row["publication_disposition"] == "private-only"}
    require(len(required) == 12 and len(private) == 3, "Unexpected reviewed archive scope")
    return required, private

def expected_names(tag, required):
    require(isinstance(tag, str) and TAG.fullmatch(tag), "Expected a semantic release tag")
    return set(required) | {
        "flamel-website-" + tag + ".zip", "flamel-predecessor-" + tag + ".zip",
        "flamel-validation-" + tag + ".zip", "flamel-release-" + tag + ".json", "SHA256SUMS",
    }

def validate_inventory(value, required, private, *, upload=False):
    require(isinstance(value, dict) and value.get("repository") == REPOSITORY, "Wrong release repository")
    tag, source = value.get("tag"), value.get("source_commit")
    require(isinstance(source, str) and COMMIT.fullmatch(source), "Use a full immutable source commit")
    expected = expected_names(tag, required)
    rows = value.get("assets")
    require(isinstance(rows, list) and len(rows) == len(expected), "Release must have exactly 17 reviewed assets")
    result, folded = {}, set()
    private_digests = {r["sha256"] for r in private.values()}
    for row in rows:
        require(isinstance(row, dict), "Asset row must be an object")
        name, size, hashed = row.get("name"), row.get("bytes"), row.get("sha256")
        require(isinstance(name, str) and NAME.fullmatch(name), "Unsafe asset filename")
        require(name in expected and name.casefold() not in folded, "Unexpected/duplicate release asset")
        folded.add(name.casefold())
        require(type(size) is int and 0 <= size <= (1024 ** 3 if name in required else MAX_EXTRA),
                "Invalid or excessive asset size")
        require(isinstance(hashed, str) and SHA.fullmatch(hashed), "Invalid asset SHA-256")
        require(name not in private and hashed not in private_digests, "Private UPF archive cannot be released or renamed")
        if name in required:
            require(size == required[name]["bytes"] and hashed == required[name]["sha256"],
                    "Required research/notice archive differs from the reviewed bytes")
        if upload:
            require(isinstance(row.get("local_path"), str) and Path(row["local_path"]).is_absolute(), "Asset local path must be absolute")
            local = regular(row["local_path"])
            require(local.is_absolute() and "#" not in str(local) and local.name == name,
                    "Asset local path/name mismatch")
            require(local.stat().st_size == size and digest(local) == hashed, "Local asset bytes differ from inventory")
        result[name] = dict(row)
    require(set(result) == expected, "Incomplete reviewed release asset set")
    return {"repository": REPOSITORY, "tag": tag, "source_commit": source, "assets": result}

def remote_assets(assets, expected, *, complete):
    require(isinstance(assets, list), "Invalid release asset response")
    found, folded = {}, set()
    for row in assets:
        name = row.get("name")
        require(isinstance(name, str) and name in expected and name.casefold() not in folded,
                "Unexpected or duplicate remote asset")
        folded.add(name.casefold())
        wanted = expected[name]
        require(row.get("state") == "uploaded" and row.get("size") == wanted["bytes"] and
                row.get("digest") == "sha256:" + wanted["sha256"], "Remote asset size/digest/state mismatch")
        require(type(row.get("id")) is int and row["id"] > 0, "Invalid remote asset ID")
        found[name] = {k: row.get(k) for k in ("id", "name", "size", "digest", "state")}
    require(not complete or set(found) == set(expected), "Remote release is incomplete")
    return found

class GitHub:
    def __init__(self, executable):
        self.executable = str(regular(executable))
        self.environment = {k: v for k, v in os.environ.items()
            if not (k.upper().startswith(("GIT_TRACE", "GCM_TRACE", "GH_TRACE")) or
                    k.upper() in {"GIT_CURL_VERBOSE", "GH_DEBUG", "GH_LOG_FILE"})}
        self.environment.update(GH_HOST="github.com", GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1",
                                GH_NO_EXTENSION_UPDATE_NOTIFIER="1", NO_COLOR="1")
    def command(self, *arguments, missing=False):
        p = subprocess.run([self.executable, *arguments], capture_output=True,
                           env=self.environment, timeout=7200)
        if p.returncode:
            if missing:
                try:
                    failure = json.loads(p.stdout)
                    if failure.get("status") == "404" or failure.get("message") == "Not Found":
                        return None
                except (ValueError, AttributeError):
                    pass
                if b"HTTP 404" in p.stderr:
                    return None
            raise RuntimeError("GitHub CLI operation failed; authentication output is suppressed")
        return p.stdout
    def api(self, path, missing=False):
        require(path.startswith("repos/" + REPOSITORY + "/") or path == "repos/" + REPOSITORY,
                "API request outside the intended repository")
        raw = self.command("api", path, missing=missing)
        return None if raw is None else json.loads(raw, object_pairs_hook=unique)
    def repository(self, write=False):
        repo = self.api("repos/" + REPOSITORY)
        require(repo.get("full_name") == REPOSITORY and repo.get("private") is True,
                "Repository identity/privacy changed")
        if write:
            require(repo.get("permissions", {}).get("push") is True, "Repository write scope was not confirmed")
    def tag(self, tag, source):
        require(TAG.fullmatch(tag) and COMMIT.fullmatch(source), "Unsafe release identity")
        ref = self.api("repos/" + REPOSITORY + "/git/ref/tags/" + tag)
        obj = ref.get("object", {})
        for _ in range(4):
            if obj.get("type") == "commit":
                require(obj.get("sha") == source, "Remote tag does not identify the selected commit")
                return source
            require(obj.get("type") == "tag" and COMMIT.fullmatch(obj.get("sha", "")), "Invalid remote tag target")
            obj = self.api("repos/" + REPOSITORY + "/git/tags/" + obj["sha"]).get("object", {})
        raise ValueError("Excessive tag indirection")
    def release(self, tag, missing=False):
        require(TAG.fullmatch(tag), "Unsafe release tag")
        # The by-tag endpoint can omit drafts even for a writer. Search only the
        # bounded same-repository release listing before deciding a tag is absent.
        result = self.api("repos/" + REPOSITORY + "/releases/tags/" + tag, missing=True)
        if result is None:
            releases = self.api("repos/" + REPOSITORY + "/releases?per_page=100")
            require(isinstance(releases, list) and len(releases) <= 100 and
                    all(isinstance(row, dict) for row in releases), "Invalid bounded release listing")
            matches = [row for row in releases if row.get("tag_name") == tag]
            require(len(matches) <= 1, "Ambiguous draft tag in release listing")
            if matches:
                result = matches[0]
                require(result.get("draft") is True, "Fallback must identify an unpublished draft")
            elif not missing:
                raise ValueError("Release tag was not found")
        if result is not None:
            require(result.get("tag_name") == tag and type(result.get("id")) is int and result["id"] > 0,
                    "Release identity mismatch")
            require(result.get("url") == "https://api.github.com/repos/" + REPOSITORY + "/releases/" + str(result["id"]),
                    "Release response is outside the intended repository")
            require(isinstance(result.get("assets"), list) and len(result["assets"]) < 100,
                    "Release exceeds bounded API asset inventory")
        return result

def release_result(release, inventory):
    assets = remote_assets(release["assets"], inventory["assets"], complete=True)
    return {"status": "DRAFT_VERIFIED" if release["draft"] else "PUBLISHED_VERIFIED",
            "repository": REPOSITORY, "tag": inventory["tag"], "source_commit": inventory["source_commit"],
            "release_id": release["id"], "release_url": "https://github.com/" + REPOSITORY + "/releases/tag/" + inventory["tag"],
            "draft": release["draft"], "immutable_api_flag": release.get("immutable", False),
            "assets": [assets[name] for name in sorted(assets)], "hosting_deployed": False}

def upload_draft(gh, inventory, notes, title):
    gh.repository(write=True)
    gh.tag(inventory["tag"], inventory["source_commit"])
    release = gh.release(inventory["tag"], missing=True)
    if release is None:
        gh.command("release", "create", inventory["tag"], "--repo", REPOSITORY, "--draft", "--verify-tag",
                   "--target", inventory["source_commit"], "--title", title, "--notes-file", str(regular(notes)))
        release = gh.release(inventory["tag"])
    require(release.get("draft") is True, "Existing published release cannot be uploaded to or modified")
    existing = remote_assets(release["assets"], inventory["assets"], complete=False)
    for name, row in inventory["assets"].items():
        if name in existing:
            print(json.dumps({"progress": "REUSED_MATCHING_DRAFT_ASSET", "name": name}), flush=True)
            continue
        gh.command("release", "upload", inventory["tag"], str(regular(row["local_path"])), "--repo", REPOSITORY)
        release = gh.release(inventory["tag"])
        existing = remote_assets(release["assets"], inventory["assets"], complete=False)
        require(name in existing, "Uploaded asset was not confirmed by GitHub")
        print(json.dumps({"progress": "UPLOADED_VERIFIED_ASSET", "name": name,
                          "bytes": row["bytes"], "assets_verified": len(existing)}), flush=True)
    return release_result(gh.release(inventory["tag"]), inventory)

def publish(gh, inventory):
    gh.repository(write=True)
    gh.tag(inventory["tag"], inventory["source_commit"])
    release = gh.release(inventory["tag"])
    release_result(release, inventory)
    if release["draft"]:
        gh.command("release", "edit", inventory["tag"], "--repo", REPOSITORY, "--draft=false", "--latest")
    result = release_result(gh.release(inventory["tag"]), inventory)
    require(result["draft"] is False, "Release did not become published")
    return result

def download_assets(gh, inventory, destination):
    destination.mkdir(parents=True, exist_ok=False)
    verified = []
    for name, row in inventory["assets"].items():
        with tempfile.TemporaryDirectory(prefix="flamel-release-", dir=destination.parent) as scratch:
            gh.command("release", "download", inventory["tag"], "--repo", REPOSITORY,
                       "--pattern", name, "--dir", scratch)
            source = regular(Path(scratch) / name)
            require(source.stat().st_size == row["bytes"] and digest(source) == row["sha256"],
                    "Downloaded asset differs from release record")
            os.link(source, destination / name)
        verified.append({"name": name, "bytes": row["bytes"], "sha256": row["sha256"]})
        print(json.dumps({"progress": "DOWNLOADED_VERIFIED_ASSET", "name": name,
                          "assets_verified": len(verified)}), flush=True)
    return {"status": "DOWNLOADED_VERIFIED", "repository": REPOSITORY, "tag": inventory["tag"],
            "source_commit": inventory["source_commit"], "destination": str(destination),
            "assets": verified, "bytes": sum(r["bytes"] for r in verified), "hosting_deployed": False}

def checksum_rows(data):
    lines = data.decode("ascii").splitlines()
    result = {}
    for line in lines:
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9][A-Za-z0-9._-]{0,180})", line)
        require(match is not None and match[2] not in result, "Malformed/duplicate checksum entry")
        result[match[2]] = match[1]
    return result

def bootstrap(gh, tag, root, destination, source_commit=None):
    required, private = policy(root)
    names = expected_names(tag, required)
    gh.repository()
    release = gh.release(tag)
    require(release.get("draft") is False, "Fresh retrieval requires a published release")
    asset_rows = release.get("assets")
    require(isinstance(asset_rows, list) and {r.get("name") for r in asset_rows} == names and len(asset_rows) == len(names),
            "Published release does not contain exactly the declared assets")
    by_name = {r["name"]: r for r in asset_rows}
    record_name = "flamel-release-" + tag + ".json"
    with tempfile.TemporaryDirectory(prefix="flamel-bootstrap-", dir=destination.parent) as temp:
        temp = Path(temp)
        for name in [record_name, "SHA256SUMS"]:
            row = by_name[name]
            require(row.get("state") == "uploaded" and type(row.get("size")) is int and 0 < row["size"] <= 1024 * 1024,
                    "Release metadata exceeds bound")
            gh.command("release", "download", tag, "--repo", REPOSITORY, "--pattern", name, "--dir", str(temp))
            p = regular(temp / name)
            require(p.stat().st_size == row["size"] and row.get("digest") == "sha256:" + digest(p),
                    "Release metadata API digest mismatch")
        record = document(temp / record_name)
        require(record.get("repository") == REPOSITORY and record.get("tag") == tag and
                COMMIT.fullmatch(record.get("source_commit", "")), "Canonical release identity mismatch")
        if source_commit is not None:
            require(record["source_commit"] == source_commit, "Canonical release source differs from expected commit")
        gh.tag(tag, record["source_commit"])
        payloads = record.get("assets")
        require(isinstance(payloads, list) and len(payloads) == len(names) - 2, "Canonical record needs fifteen payloads")
        metadata = [{"name": name, "bytes": (temp / name).stat().st_size, "sha256": digest(temp / name)}
                    for name in [record_name, "SHA256SUMS"]]
        inventory = validate_inventory({"repository": REPOSITORY, "tag": tag, "source_commit": record["source_commit"],
                                        "assets": payloads + metadata}, required, private)
        expected_sums = {r["name"]: r["sha256"] for r in payloads}
        expected_sums[record_name] = digest(temp / record_name)
        require(checksum_rows((temp / "SHA256SUMS").read_bytes()) == expected_sums,
                "Checksum sidecar does not bind all payloads and the canonical record")
        remote_assets(asset_rows, inventory["assets"], complete=True)
    return download_assets(gh, inventory, destination)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gh", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ["preflight", "upload-draft", "publish", "download"]:
        p = subs.add_parser(command)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--receipt", type=Path)
        if command == "upload-draft":
            p.add_argument("--notes-file", type=Path, required=True)
            p.add_argument("--title", default="The Flamel Project v0.1.0")
        if command == "download":
            p.add_argument("--destination", type=Path, required=True)
    p = subs.add_parser("bootstrap")
    p.add_argument("--tag", required=True)
    p.add_argument("--source-commit")
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    try:
        if args.receipt:
            new_output(args.receipt, args.root)
        gh = GitHub(args.gh)
        if args.command == "bootstrap":
            destination = new_output(args.destination, args.root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            result = bootstrap(gh, args.tag, args.root, destination, args.source_commit)
        else:
            required, private = policy(args.root)
            inventory = validate_inventory(document(args.manifest), required, private,
                                           upload=args.command in {"preflight", "upload-draft"})
            if args.command == "preflight":
                result = {"status": "PREFLIGHT_PASS", "tag": inventory["tag"],
                          "source_commit": inventory["source_commit"], "assets": len(inventory["assets"]),
                          "bytes": sum(r["bytes"] for r in inventory["assets"].values())}
            elif args.command == "upload-draft":
                result = upload_draft(gh, inventory, args.notes_file, args.title)
            elif args.command == "publish":
                result = publish(gh, inventory)
            else:
                gh.repository()
                gh.tag(inventory["tag"], inventory["source_commit"])
                release = gh.release(inventory["tag"])
                require(release.get("draft") is False, "Download requires a published release")
                release_result(release, inventory)
                destination = new_output(args.destination, args.root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                result = download_assets(gh, inventory, destination)
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            with args.receipt.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2)
                stream.write("\n")
        print(json.dumps(result), flush=True)
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.TimeoutExpired):
        print("Release transport rejected the operation; raw authentication/process output is suppressed.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
