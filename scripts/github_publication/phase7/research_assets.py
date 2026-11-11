"""Authenticate, retrieve and verify only the permitted frozen research release assets.

Credentials remain with the normal GitHub CLI authentication provider. This
program never reads a token/credential store, embeds a token in a URL, prints
raw authentication responses, or deserializes scientific model contents.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = "zacxu/the-flamel-project"
PHASE4_SELECTOR_SHA256 = "af567654dbd3693221194d168be5c7a402005a9a80a05b6d317346b8f007ed4d"
SPEC = importlib.util.spec_from_file_location("_phase7_public_assets", Path(__file__).resolve().parents[1] / "public_assets.py")
public = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(public)

def require(value, message):
    if not value:
        raise ValueError(message)

def tag_name(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", value), "Use a plain immutable release tag")
    return value

def new_report(path, value):
    path = public.legacy._absolute(path)
    require(not path.exists(), "Report output must be new")
    public.legacy._ensure_directories(path.parent)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

def prepare_selector(root, output, tag):
    root = public.legacy._absolute(root)
    template = root / "publication/phase4/public-assets.json"
    data, digest = public.load_public(template)
    require(digest == PHASE4_SELECTOR_SHA256, "Historical Phase 4 selector changed")
    data = copy.deepcopy(data)
    tag = tag_name(tag)
    data.update(publication_status="published", release_tag=tag,
                repository_visibility="private",
                authentication="Use normal authenticated GitHub CLI release retrieval; tokens are never URL/file fields.",
                phase4_source_manifest_sha256=digest,
                release_transaction="Prospective release-candidate descriptor; actual availability is established by the published GitHub release and independent download receipt.")
    for item in data["archives"]:
        url = "https://github.com/" + REPOSITORY + "/releases/download/" + tag + "/" + item["name"]
        item.update(availability="published", download_url=url, planned_download_url=url)
    new_report(output, data)
    return {"status": "RELEASE_SELECTOR_PREPARED", "tag": tag, "archives": 12,
            "compressed_bytes": sum(row["bytes"] for row in data["archives"]),
            "remote_availability_checked": False}

def validate_release(document, selector, tag):
    tag = tag_name(tag)
    require(isinstance(document, dict) and document.get("tag_name") == tag, "Release tag differs from selector")
    require(document.get("draft") is False, "Only an actually published release can be retrieved")
    require(type(document.get("id")) is int and document["id"] > 0, "Release ID missing")
    require(selector.get("repository") == REPOSITORY and selector.get("publication_status") == "published", "Published exact-repository selector required")
    require(selector.get("release_tag") == tag, "Manifest release tag differs")
    assets = document.get("assets")
    require(isinstance(assets, list), "Release asset metadata missing")
    names = {}
    folded = set()
    private_folded = {n.casefold() for n in public.PRIVATE_ARCHIVES}
    for item in assets:
        require(isinstance(item, dict), "Release asset record must be an object")
        name = public.legacy._safe_relative(item.get("name"))
        require("/" not in name, "Release assets must be flat safe basenames")
        require(name.casefold() not in folded, "Duplicate or case-colliding release asset")
        require(name.casefold() not in private_folded and not name.lower().endswith(".upf"), "Private pseudopotential asset present in release")
        folded.add(name.casefold())
        names[name] = item
    results = []
    for expected in selector["archives"]:
        name = expected["name"]
        require(name in names, "Required research/notice asset missing: " + name)
        found = names[name]
        expected_url = "https://github.com/" + REPOSITORY + "/releases/download/" + tag + "/" + name
        require(expected.get("download_url") == expected_url and found.get("browser_download_url") == expected_url, "Release asset URL is not the expected stable URL")
        require(found.get("state") == "uploaded", "Release asset upload is incomplete")
        require(type(found.get("id")) is int and found["id"] > 0, "Asset ID missing")
        require(type(found.get("size")) is int and found["size"] == expected["bytes"], "Release asset size differs")
        digest = found.get("digest")
        require(digest is None or digest == "sha256:" + expected["sha256"], "GitHub asset digest differs")
        results.append({"name": name, "id": found["id"], "bytes": expected["bytes"],
                        "sha256": expected["sha256"], "github_digest_checked": digest is not None})
    require(len(results) == 12, "Exactly eleven permitted archives and one notice archive are required")
    return {"status": "RELEASE_METADATA_VERIFIED", "repository": REPOSITORY, "tag": tag,
            "release_id": document["id"], "prerelease": document.get("prerelease"),
            "target_commitish": document.get("target_commitish"),
            "archives": results, "private_archives_included": 0,
            "scope": "Research/notice subset; the complete release inventory is verified separately.",
            "downloaded_bytes_verified": False}

def cli_environment():
    environment = dict(os.environ)
    for name in list(environment):
        if name.upper() == "GH_DEBUG" or name.upper().startswith(("GIT_TRACE", "GCM_TRACE")) or name.upper() == "GIT_CURL_VERBOSE":
            environment.pop(name)
    environment.update(GH_PROMPT_DISABLED="1", GIT_TERMINAL_PROMPT="0")
    return environment

def gh_json(executable, endpoint):
    run = subprocess.run([str(executable), "api", "--method", "GET", endpoint],
                         capture_output=True, env=cli_environment())
    require(run.returncode == 0, "Authenticated GitHub metadata request failed; configure normal gh authentication for this repository")
    try:
        return json.loads(run.stdout, object_pairs_hook=public.unique_object)
    except (ValueError, UnicodeError):
        raise ValueError("GitHub metadata was not valid JSON") from None

def resolve_tag(executable, tag):
    endpoint = "repos/" + REPOSITORY + "/git/ref/tags/" + tag_name(tag)
    record = gh_json(executable, endpoint).get("object", {})
    for _ in range(4):
        require(isinstance(record.get("sha"), str) and re.fullmatch(r"[a-f0-9]{40}", record["sha"]), "Tag Git object identity missing")
        if record.get("type") == "commit":
            return record["sha"]
        require(record.get("type") == "tag", "Tag does not identify a commit/tag object")
        record = gh_json(executable, "repos/" + REPOSITORY + "/git/tags/" + record["sha"]).get("object", {})
    raise ValueError("Excessive annotated tag nesting")

def download(manifest, destination, executable, source_commit=None):
    data, manifest_digest = public.load_public(manifest)
    tag = tag_name(data.get("release_tag"))
    metadata = gh_json(executable, "repos/" + REPOSITORY + "/releases/tags/" + tag)
    release = validate_release(metadata, data, tag)
    actual_commit = resolve_tag(executable, tag)
    if source_commit is not None:
        require(bool(re.fullmatch(r"[a-f0-9]{40}", source_commit)) and actual_commit == source_commit, "Release tag differs from the selected immutable source commit")
    destination = public.legacy._absolute(destination)
    require(destination != Path(destination.anchor), "Filesystem roots are not download destinations")
    require(not destination.resolve().is_relative_to(ROOT), "Download outside the source checkout")
    public.legacy._check_directory_ancestors(destination, allow_missing=True)
    expected = {r["name"]: r for r in data["archives"]}
    if destination.exists():
        require(destination.is_dir(), "Download destination must be a directory")
        for path in destination.iterdir():
            require(path.name in expected, "Unlisted existing download file")
            public.legacy._regular_file(path)
            row = expected[path.name]
            require(path.stat().st_size == row["bytes"] and public.sha256(path) == row["sha256"], "Existing download differs; no overwrite is permitted")
    public.legacy._ensure_directories(destination)
    fetched = []
    for row in data["archives"]:
        path = destination / row["name"]
        reused = path.exists()
        if not reused:
            run = subprocess.run([str(executable), "release", "download", tag, "--repo", REPOSITORY,
                                  "--pattern", row["name"], "--dir", str(destination)],
                                 capture_output=True, env=cli_environment())
            require(run.returncode == 0, "Authenticated release download failed for " + row["name"] + "; existing verified assets can be reused")
        public.legacy._regular_file(path)
        require(path.stat().st_size == row["bytes"] and public.sha256(path) == row["sha256"], "Downloaded asset differs from pinned bytes")
        fetched.append({"name": row["name"], "network_fetches": 0 if reused else 1, "bytes": row["bytes"], "sha256": row["sha256"]})
    public.legacy._check_directory_ancestors(destination)
    require({p.name for p in destination.iterdir()} == set(expected), "Unexpected file appeared in download directory")
    result = public.verify(manifest, destination, destination, "all")
    return {"status": "AUTHENTICATED_RELEASE_DOWNLOADED_VERIFIED", "repository": REPOSITORY,
            "tag": tag, "source_commit": actual_commit, "manifest_sha256": manifest_digest,
            "release": release, "downloads": fetched,
            "network_fetches": sum(r["network_fetches"] for r in fetched), "verification": result,
            "authentication": "Normal GitHub CLI provider; no credential value is read, logged, stored or embedded in a URL."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    command = subs.add_parser("prepare-manifest")
    command.add_argument("--root", type=Path, default=ROOT)
    command.add_argument("--tag", required=True)
    command.add_argument("--output", type=Path, required=True)
    command = subs.add_parser("verify-release-json")
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--metadata", type=Path, required=True)
    command.add_argument("--report", type=Path, required=True)
    command = subs.add_parser("download")
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--destination", type=Path, required=True)
    command.add_argument("--gh-exe", default="gh")
    command.add_argument("--source-commit")
    command.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare-manifest":
            result = prepare_selector(args.root, args.output, args.tag)
        elif args.command == "verify-release-json":
            require(not args.report.absolute().resolve().is_relative_to(ROOT), "Audit reports must be outside the source checkout")
            data, _ = public.load_public(args.manifest)
            metadata, _ = public.read_json(args.metadata)
            result = validate_release(metadata, data, data.get("release_tag"))
            new_report(args.report, result)
        else:
            require(not args.report.absolute().resolve().is_relative_to(ROOT), "Audit reports must be outside the source checkout")
            result = download(args.manifest, args.destination, args.gh_exe, args.source_commit)
            new_report(args.report, result)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, public.ArtifactError) as error:
        print("Research release gate rejected: " + str(error), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
