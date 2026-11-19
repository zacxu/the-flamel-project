"""Publish the verified Flamel handoff over explicit FTPS and restore its prior entry."""
import argparse
import ftplib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import ssl
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("phase6_manual_ci", ROOT / "scripts/github_publication/phase6/manual_ci.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
MUTABLE = ("research/manifest.json", ".htaccess", "index.html")
PRIOR_POLICIES = {gate.POLICY, "383707b105ac4286f66595968d735aded9a3e5796f4d98bceac2588d0955d9fc"}
HOST = "ftpupload.net"
SITE = "https://theflamelproject.42web.io/refresh"
LIMIT = 10_000_000


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


class FTPS:
    """Binary transfers, certificate and hostname verification, fixed /htdocs root."""

    def __init__(self):
        gate.require(os.environ.get("INFINITYFREE_FTP_HOST", HOST).lower() == HOST, "Use the provider's TLS hostname ftpupload.net")
        user = os.environ.get("INFINITYFREE_FTP_USERNAME")
        password = os.environ.get("INFINITYFREE_FTP_PASSWORD")
        gate.require(user and password, "Configure InfinityFree FTP username and password")
        self.binding = digest((HOST + "/" + user + "/htdocs").encode())
        self.ftp = ftplib.FTP_TLS(context=ssl.create_default_context(), timeout=35)
        try:
            self.ftp.connect(HOST, 21)
            self.ftp.login(user, password)
            self.ftp.prot_p()
            self.ftp.cwd("/htdocs")
            gate.require(self.ftp.pwd() == "/htdocs", "Unexpected FTP document root")
        except BaseException:
            self.ftp.close()
            raise

    def kind(self, name):
        # 550 can mean permission denied. Accept absence only after a successful parent listing.
        path = PurePosixPath(name)
        directory = "/htdocs"
        for part in path.parts:
            entries = dict(self.ftp.mlsd(directory, facts=["type"]))
            if part not in entries:
                return None
            kind = entries[part].get("type")
            gate.require(kind in {"dir", "file"}, "Unsupported remote object type at " + name)
            directory += "/" + part
            if directory != "/htdocs/" + name:
                gate.require(kind == "dir", "Remote parent is not a directory")
        return kind

    def read(self, name):
        gate.relative(name)
        value = bytearray()

        def append(chunk):
            gate.require(len(value) + len(chunk) <= LIMIT, "Remote file exceeds size bound")
            value.extend(chunk)

        try:
            self.ftp.retrbinary("RETR /htdocs/" + name, append)
        except ftplib.error_perm as exc:
            if str(exc).startswith("550") and self.kind(name) is None:
                return None
            raise
        return bytes(value)

    def replace(self, name, data, before):
        gate.relative(name)
        directory = PurePosixPath(name).parent
        for folder in [*reversed(directory.parents), directory]:
            if folder != PurePosixPath(".") and self.kind(str(folder)) is None:
                self.ftp.mkd("/htdocs/" + str(folder))
        stage = str(directory / ("flamel-upload-" + uuid.uuid4().hex + ".bin"))
        gate.require(self.kind(stage) is None, "Staging name exists")
        try:
            self.ftp.storbinary("STOR /htdocs/" + stage, io.BytesIO(data))
            gate.require(self.read(stage) == data, "Temporary upload failed byte verification")
            gate.require(digest(self.read(name)) == before, "Remote target changed before rename: " + name)
            # RNTO may refuse replacement. Never delete the existing destination as a fallback.
            self.ftp.rename("/htdocs/" + stage, "/htdocs/" + name)
        except Exception:
            # Only this transaction's unique temporary path may be removed.
            try:
                self.ftp.delete("/htdocs/" + stage)
            except ftplib.all_errors:
                pass
            raise
        gate.require(self.read(name) == data, "Readback after rename failed: " + name)

    def close(self):
        self.ftp.close()


def handoff(directory, source):
    verifier = importlib.util.spec_from_file_location("phase8_prepare", Path(__file__).with_name("prepare_deployment.py"))
    prepare = importlib.util.module_from_spec(verifier)
    verifier.loader.exec_module(prepare)
    verified = prepare.verify_handoff(directory, source)
    plan = gate.read(directory / "upload-plan.json")
    gate.require(plan["targetDocumentRoot"] == "/htdocs" and plan["status"] == "verified_for_manual_publication",
                 "Missing verified publication guard stage")
    immutable = gate.inventory(plan["immutableFiles"])
    pointers = gate.inventory(plan["mutableFilesBeforeEntry"])
    gate.require(set(pointers) == {MUTABLE[0]}, "Unrecognized mutable pointer")
    gate.require(all(path.startswith(("assets/", "release-manifests/", "research/releases/", "ui/figures/"))
                     for path in immutable), "Unrecognized immutable path")
    gate.require({**immutable, **pointers} == gate.inventory(plan["filesBeforeEntry"]),
                 "Guard partitions differ from the exact release inventory")
    with zipfile.ZipFile(directory / "payload.zip") as archive:
        files = {name: archive.read(name) for name in immutable}
        files[MUTABLE[0]] = archive.read(MUTABLE[0])
    files[".htaccess"] = (directory / "host/.htaccess").read_bytes()
    files["index.html"] = (directory / "entry-last/index.html").read_bytes()
    return verified, files


def effective(remote, name):
    if name.endswith((".png", ".webp")):
        side = remote.read(name + ".bin")
        if side is not None:
            return side
    return remote.read(name)


def predecessor(remote, saved, manifest_identity=None, capture=None):
    entry = saved["index.html"]
    gate.require(entry and b"The Flamel Project" in entry, "Existing root entry is not the Flamel site")
    gate.require(digest(saved[".htaccess"]) in PRIOR_POLICIES, "Existing root configuration is unrecognized")
    pointer = json.loads(saved[MUTABLE[0]])
    gate.require(pointer.get("studyId") == "flamel-frozen-study-20261022", "Unexpected current research site")
    match = re.search(rb'src=["\']\./(assets/[a-zA-Z0-9_-]+\.js)["\']', entry)
    gate.require(match, "Cannot identify predecessor application script")
    script_name = match[1].decode("ascii")
    script = remote.read(script_name)
    ids = set(re.findall(rb"ui-w6-[a-f0-9]{20}", script or b""))
    gate.require(len(ids) == 1, "Cannot identify predecessor UI")
    build = ids.pop().decode("ascii")
    name = "release-manifests/" + build + ".json"
    raw = remote.read(name)
    gate.require(raw is not None, "Previous release manifest is missing")
    identity = {"ui_build_id": build, "manifest_sha256": digest(raw)}
    if manifest_identity is not None:
        gate.require(identity == manifest_identity, "Previous release manifest has changed")
    manifest = json.loads(raw)
    gate.require(manifest["uiBuildId"] == build and manifest["studyId"] == pointer["studyId"] and
                 manifest["exportManifestSha256"] == digest(saved[MUTABLE[0]]), "Previous manifest and pointers disagree")
    rows = gate.inventory(manifest["files"])
    gate.require({script_name, "index.html", MUTABLE[0]} <= rows.keys(), "Previous manifest is incomplete")
    if capture is not None:
        capture[name] = raw
    for path, row in rows.items():
        data = saved[path] if path in saved else effective(remote, path)
        gate.require(digest(data) == row["sha256"], "Previous release is incomplete at " + path)
        if capture is not None:
            capture[path] = data
    return identity


def immutable_changes(remote, files):
    changes = {}
    for name, data in files.items():
        if name in MUTABLE:
            continue
        prior = effective(remote, name)
        if prior is None:
            # The accepted Apache rewrite serves the exact sidecar at the public image URL.
            # Writing raw images invokes the provider's image conversion on some accounts.
            target = name + ".bin" if name.endswith((".png", ".webp")) else name
            changes[target] = data
        else:
            gate.require(prior == data, "Existing versioned file differs: " + name)
    return changes


def inspect(remote, verified, files, expected, capture=None):
    gate.require(re.fullmatch(r"[a-f0-9]{64}", expected or ""), "Supply the observed live entry SHA-256")
    saved = {name: remote.read(name) for name in MUTABLE}
    gate.require(digest(saved["index.html"]) == expected, "The remote entry differs from the expected live entry")
    gate.require(all(saved.values()), "Existing entry, pointer or configuration is missing")
    previous = predecessor(remote, saved, capture=capture)
    additions = immutable_changes(remote, files)
    return saved, {"site": SITE, "document_root": "/htdocs", "account_binding": remote.binding,
                   "source_commit": verified["source_commit"], "payload_sha256": verified["payload_sha256"],
                   "ui_build_id": verified["ui_build_id"], "predecessor": previous,
                   "previous_sha256": {k: digest(v) for k, v in saved.items()},
                   "incoming_sha256": {k: digest(files[k]) for k in MUTABLE},
                   "new_immutable_files": list(additions),
                   "changed_mutable_files": [k for k in MUTABLE if saved[k] != files[k]]}


def snapshot(remote, verified, files, expected, state):
    captured = {}
    saved, record = inspect(remote, verified, files, expected, capture=captured)
    captured.update(saved)
    public_rows = [{"path": name, "bytes": len(data), "sha256": digest(data)}
                   for name, data in sorted(captured.items()) if name != ".htaccess"]
    gate.write_new(state / "restored-package.json", {
        "uiBuildId": record["predecessor"]["ui_build_id"], "fileCount": len(public_rows), "files": public_rows})
    package = state / "predecessor.zip"
    with zipfile.ZipFile(package, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(captured.items()):
            archive.writestr(name, data)
    record["predecessor_zip_sha256"] = digest(package.read_bytes())
    backup = state / "rollback"
    backup.mkdir()
    for path, data in saved.items():
        target = backup / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as fp:
            fp.write(data)
    gate.write_new(state / "snapshot.json", record)
    return record


def restore_inputs(remote, verified, files, state):
    record = gate.read(state / "snapshot.json")
    gate.require((record["site"], record["document_root"], record["account_binding"]) ==
                 (SITE, "/htdocs", remote.binding), "Rollback belongs to a different account or site")
    gate.require(record["source_commit"] == verified["source_commit"] and record["payload_sha256"] == verified["payload_sha256"],
                 "Rollback belongs to a different release")
    saved = {k: gate.regular(state / "rollback" / k).read_bytes() for k in MUTABLE}
    gate.require({k: digest(v) for k, v in saved.items()} == record["previous_sha256"] and
                 {k: digest(files[k]) for k in MUTABLE} == record["incoming_sha256"], "Rollback inventory mismatch")
    archive_path = gate.regular(state / "predecessor.zip")
    gate.require(archive_path.stat().st_size < 110_000_000 and digest(archive_path.read_bytes()) ==
                 record["predecessor_zip_sha256"], "Predecessor package digest mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        gate.require(len(entries) <= 4100 and sum(r.file_size for r in entries) <= 110_000_000,
                     "Invalid predecessor package size")
        old = {gate.relative(r.filename): archive.read(r) for r in entries}
    captured = {}
    predecessor(RehearsalHost(old), saved, record["predecessor"], capture=captured)
    gate.require({**captured, **saved} == old, "Unverified bytes in predecessor package")
    return record, saved, old


def apply(remote, verified, files, state, rollback=False, expected=None):
    record, saved, old = restore_inputs(remote, verified, files, state)
    actual = {k: remote.read(k) for k in MUTABLE}
    if not rollback:
        gate.require(expected == record["previous_sha256"]["index.html"], "Live entry pin differs from saved snapshot")
    for k in MUTABLE:
        gate.require(actual[k] in (saved[k], files[k]), "Remote mutable file diverged: " + k)
    if not rollback:
        predecessor(remote, saved, record["predecessor"])
    writes = []
    for name, data in immutable_changes(remote, old if rollback else files).items():
        remote.replace(name, data, None)
        writes.append(name)
    desired = saved if rollback else files
    for name in MUTABLE:
        current = remote.read(name)
        gate.require(current == actual[name], "Remote file changed during publication: " + name)
        if current != desired[name]:
            remote.replace(name, desired[name], digest(current))
            writes.append(name)
    return {"operation": "rollback" if rollback else "deploy", "source_commit": verified["source_commit"],
            "ui_build_id": record["predecessor"]["ui_build_id"] if rollback else record["ui_build_id"],
            "written_paths": writes, "changed_files": len(writes), "entry_sha256": digest(desired["index.html"]),
            "status": "VERIFIED_FTPS_READBACK" if writes else "ALREADY_MATCHES"}


class RehearsalHost:
    """In-memory document root for the same snapshot, apply and restore operations."""
    binding = "local-rehearsal"

    def __init__(self, files):
        self.files = dict(files)

    def read(self, name):
        return self.files.get(name)

    def replace(self, name, data, before):
        gate.require(digest(self.read(name)) == before, "Concurrent rehearsal edit")
        self.files[name] = data


def rehearse(verified, files, state, previous_zip):
    if previous_zip:
        # This optional input is a trusted retained historical production ZIP.
        with zipfile.ZipFile(previous_zip) as archive:
            gate.require(sum(r.file_size for r in archive.infolist()) < 100_000_000, "Predecessor too large")
            prior = {gate.relative(r.filename): archive.read(r) for r in archive.infolist()}
        prior[".htaccess"] = files[".htaccess"]
        label = "retained historical package"
    else:
        # Make a tiny, internally consistent preceding release. All incoming bytes are real.
        old_build = "ui-w6-" + "a" * 20
        js = "assets/index-Previous.js"
        previous_entry = b'<title>The Flamel Project</title><script src="./' + js.encode() + b'"></script>'
        pointer = json.dumps({"studyId": "flamel-frozen-study-20261022", "fixture": True}).encode()
        prior = {js: old_build.encode(), "index.html": previous_entry, MUTABLE[0]: pointer}
        rows = [{"path": k, "sha256": digest(v), "bytes": len(v)} for k, v in prior.items()]
        prior["release-manifests/" + old_build + ".json"] = json.dumps({
            "uiBuildId": old_build, "studyId": "flamel-frozen-study-20261022", "files": rows,
            "exportManifestSha256": digest(pointer)}).encode()
        prior[".htaccess"] = files[".htaccess"]
        label = "synthetic preceding release"
    prior["retained/unrelated.bin"] = b"unrelated predecessor data"
    remote = RehearsalHost(prior)
    expected = digest(prior["index.html"])
    snapshot(remote, verified, files, expected, state)
    deployed = apply(remote, verified, files, state, expected=expected)
    gate.require(all(effective(remote, k) == v for k, v in files.items()), "Incomplete rehearsal publish")
    repeat = apply(remote, verified, files, state, expected=expected)
    gate.require(not repeat["written_paths"], "Repeated deployment did not skip identical bytes")
    restored = apply(remote, verified, files, state, rollback=True)
    gate.require(all(remote.read(k) == v for k, v in prior.items()), "Incomplete rehearsal rollback")
    return {"status": "REHEARSAL_PASSED", "predecessor_kind": label, "verified_incoming_files": len(files),
            "deploy": deployed, "second_deploy": repeat, "rollback": restored,
            "prior_files_verified_after_rollback": len(prior), "live_writes": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "snapshot", "deploy", "rollback", "rehearse"))
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--predecessor-zip", type=Path)
    args = parser.parse_args()
    state = args.state_dir
    state.mkdir(parents=True, exist_ok=True)
    verified, files = handoff(args.package_dir, args.source_commit)
    if args.command == "rehearse":
        result = rehearse(verified, files, state, args.predecessor_zip)
        gate.write_new(state / "rehearsal.json", result)
    else:
        remote = FTPS()
        try:
            expected = os.environ.get("INFINITYFREE_EXPECTED_ENTRY_SHA256")
            if args.command == "snapshot":
                result = snapshot(remote, verified, files, expected, state)
            elif args.command == "inspect":
                _, result = inspect(remote, verified, files, expected)
                gate.write_new(state / "inspect.json", result)
            else:
                result = apply(remote, verified, files, state, args.command == "rollback", expected)
                # Retrying a verified operation may legitimately produce a second no-op receipt.
                path = state / (args.command + ".json")
                if path.exists():
                    path = state / (args.command + "-" + uuid.uuid4().hex + ".json")
                gate.write_new(path, result)
        finally:
            remote.close()
    print(json.dumps({"command": args.command, "status": result.get("status", "VERIFIED"),
                      "changed_files": result.get("changed_files", 0)}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ftplib.Error, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        # FTP servers can echo identifiers in replies. Only local validation messages are safe to print.
        print(str(error) if type(error) is ValueError else "Transport failed: " + type(error).__name__, file=sys.stderr)
        sys.exit(1)
