"""Encrypted migration bundles and extraction into an isolated root."""

import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tarfile
import tempfile
import time


APP = re.compile(r"[a-z][a-z0-9-]*")
SECTIONS = {"runtime": "opt", "config": "etc/hanzhub", "data": "var/lib/hanzhub",
            "logs": "var/log/hanzhub"}
ENCRYPTED = "bundle.tar.gz.gpg"
PUBLIC = "bundle.tar.gz"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def destination(app, entry):
    section = entry["section"]
    name = entry["name"]
    require(section in SECTIONS and isinstance(name, str)
            and all(part not in {"", ".", ".."} for part in name.split("/")),
            "Invalid payload path")
    return f"{SECTIONS[section]}/{app}/{name}"


def entries(plan):
    require(isinstance(plan, dict) and plan, "Missing applications")
    seen = set()
    for app, manifest in plan.items():
        require(APP.fullmatch(app), "Invalid application ID")
        require(manifest["files"], f"Missing payload for {app}")
        for entry in manifest["files"]:
            name = destination(app, entry)
            require(name not in seen, "Duplicate payload path")
            seen.add(name)
            require(entry["method"] in {"static", "native-export", "sqlite"},
                    "Unknown export method")
            yield app, entry, name


def check_sqlite(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                "SQLite integrity check failed")


@contextmanager
def archive_output(cipher, recipient):
    if recipient == "public":
        with cipher.open("xb") as output:
            yield output
        return
    with subprocess.Popen(
        ["gpg", "--batch", "--trust-model", "always", "--recipient", recipient,
         "--output", str(cipher), "--encrypt"], stdin=subprocess.PIPE,
    ) as gpg:
        try:
            yield gpg.stdin
        finally:
            gpg.stdin.close()
        require(gpg.wait() == 0, "Encryption failed")


def check_mount(mount, uuid):
    mount = mount.resolve(strict=True)
    require(mount != Path("/") and os.path.ismount(mount), "Expected an exact export mount")
    info = json.loads(subprocess.check_output(
        ["findmnt", "--json", "--mountpoint", str(mount), "--output", "UUID,OPTIONS"]
    ))["filesystems"]
    require(len(info) == 1 and info[0]["uuid"] == uuid
            and "rw" in info[0]["options"].split(",") and os.access(mount, os.W_OK),
            "Export mount must be writable and match the verified UUID")
    return mount


def backup(args):
    mount = check_mount(args.mount, args.uuid)
    plan = json.loads(args.plan.read_text())
    payload = list(entries(plan))
    require(args.recipient == "public" or
            re.fullmatch(r"[0-9A-Fa-f]{40}|[0-9A-Fa-f]{64}", args.recipient),
            "Supply a full GPG fingerprint")

    with tempfile.TemporaryDirectory(prefix=".incomplete-", dir=mount) as work:
        folder = Path(work)
        cipher = folder / (PUBLIC if args.recipient == "public" else ENCRYPTED)
        started = utc()
        with archive_output(cipher, args.recipient) as output:
            with tarfile.open(fileobj=output, mode="w|gz") as tar:
                for _, entry, name in payload:
                    source = Path(entry["source"])
                    require(source.is_absolute() and not source.is_symlink() and source.is_file(),
                            "Expected a regular source file")
                    original = source.stat()
                    entry["original"] = {"uid": original.st_uid, "gid": original.st_gid,
                                         "mode": original.st_mode & 0o7777}
                    if entry["method"] == "sqlite":
                        with tempfile.TemporaryDirectory() as scratch:
                            snapshot = Path(scratch) / "snapshot.sqlite"
                            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True,
                                                         timeout=5)) as live:
                                with closing(sqlite3.connect(snapshot)) as copy:
                                    deadline = time.monotonic() + 120

                                    def progress(status, remaining, total):
                                        require(time.monotonic() < deadline, "SQLite backup timed out")

                                    live.backup(copy, pages=256, progress=progress)
                            check_sqlite(snapshot)
                            tar.add(snapshot, arcname=name, recursive=False)
                    else:
                        with source.open("rb") as stream:
                            before = os.fstat(stream.fileno())
                            require(stream.read(16) != b"SQLite format 3\x00"
                                    and not source.name.endswith(("-wal", "-shm", "-journal")),
                                    "Use SQLite online backup for live SQLite files")
                            stream.seek(0)
                            tar.addfile(tar.gettarinfo(fileobj=stream, arcname=name), stream)
                            after = source.stat()
                            require((before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns,
                                     before.st_ctime_ns) ==
                                    (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns,
                                     after.st_ctime_ns), "Source changed during export")
                data = json.dumps({"started": started, "finished": utc(), "apps": plan}).encode()
                header = tarfile.TarInfo("manifest.json")
                header.size = len(data)
                header.mode = 0o600
                tar.addfile(header, io.BytesIO(data))
        (folder / "SHA256SUMS").write_text(f"{digest(cipher)}  {cipher.name}\n")
        target = mount / ("hanzhub-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        require(not target.exists(), "Bundle already exists")
        for name in (cipher.name, "SHA256SUMS"):
            with (folder / name).open("rb") as completed:
                os.fsync(completed.fileno())
        sync_directory(folder)
        # Publish only after both files are complete.
        folder.rename(target)
        sync_directory(mount)
        print(target)


@contextmanager
def archive_input(cipher):
    if cipher.name == PUBLIC:
        with cipher.open("rb") as clear:
            yield clear
        return
    # Authenticate the complete ciphertext before inspecting or extracting the archive.
    with tempfile.TemporaryFile() as clear:
        subprocess.run(["gpg", "--batch", "--decrypt", str(cipher)], stdout=clear, check=True)
        clear.seek(0)
        yield clear


@contextmanager
def unpack(bundle, require_hash_only=False):
    names = {p.name for p in bundle.iterdir()}
    require(names in ({"SHA256SUMS", ENCRYPTED}, {"SHA256SUMS", PUBLIC}),
            "Unexpected bundle contents")
    require(all((bundle / name).is_file() and not (bundle / name).is_symlink() for name in names),
            "Invalid bundle file")
    cipher = bundle / (ENCRYPTED if ENCRYPTED in names else PUBLIC)
    require((bundle / "SHA256SUMS").read_text() == f"{digest(cipher)}  {cipher.name}\n",
            "Checksum mismatch")
    if require_hash_only:
        yield None, None
        return

    with archive_input(cipher) as clear:
        with tarfile.open(fileobj=clear, mode="r:gz") as tar:
            members = tar.getmembers()
            require(all(member.isfile() for member in members), "Unexpected archive entry type")
            names = [member.name for member in members]
            require(len(names) == len(set(names)), "Duplicate archive entry")
            with tar.extractfile("manifest.json") as manifest:
                plan = json.load(manifest)["apps"]
            require(set(names) == {"manifest.json"} | {name for _, _, name in entries(plan)},
                    "Archive and manifest disagree")
            yield tar, plan


def extract(tar, plan, target, selected):
    for app, entry, name in entries(plan):
        if app in selected:
            member = tar.getmember(name)
            tar.extract(member, target, filter="data")
            if entry["method"] == "sqlite":
                check_sqlite(target / name)


def restore(args):
    with unpack(args.bundle) as (tar, plan):
        if args.list:
            print("\n".join(sorted(plan)))
            return
        selected = set(plan) if args.all else {args.app}
        require(selected <= set(plan), "Unknown application")
        require(args.parent is not None, "Supply an empty, dedicated staging parent via --parent")
        parent = args.parent.resolve(strict=True)
        require(parent.is_dir() and not any(parent.iterdir()) and parent.stat().st_uid == os.getuid()
                and parent.stat().st_mode & 0o077 == 0, "Staging parent must be empty and private")
        with tempfile.TemporaryDirectory(prefix=".restoring-", dir=parent) as work:
            root = Path(work)
            extract(tar, plan, root, selected)
            (root / ".hanzhub-staged").write_text("hanzhub-migration-v1\n")
            root.rename(parent / "staged")
        print(parent / "staged")


def rollback(args):
    parent = args.parent.resolve(strict=True)
    root = parent / "staged"
    marker = root / ".hanzhub-staged"
    parked = parent / "rolled-back"
    require(not root.is_symlink() and not marker.is_symlink() and marker.is_file()
            and marker.read_text() == "hanzhub-migration-v1\n"
            and not os.path.lexists(parked) and parent.stat().st_uid == os.getuid()
            and parent.stat().st_mode & 0o077 == 0, "Expected a private staged restore")
    root.rename(parked)
    print(parked)


def verify(args):
    with unpack(args.bundle, args.hash_only) as (tar, plan):
        if not args.hash_only:
            with tempfile.TemporaryDirectory() as work:
                extract(tar, plan, Path(work), set(plan))
    if args.hash_only:
        print("SHA-256 OK")
    else:
        encryption = ", GPG" if (args.bundle / ENCRYPTED).is_file() else ""
        print(f"SHA-256{encryption}, payload and applicable SQLite checks OK")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("backup")
    command.add_argument("mount", type=Path)
    command.add_argument("uuid")
    command.add_argument("recipient")
    command.add_argument("plan", type=Path)
    command = commands.add_parser("verify")
    command.add_argument("bundle", type=Path)
    command.add_argument("--hash-only", action="store_true")
    command = commands.add_parser("restore")
    command.add_argument("bundle", type=Path)
    modes = command.add_mutually_exclusive_group(required=True)
    modes.add_argument("--list", action="store_true")
    modes.add_argument("--app")
    modes.add_argument("--all", action="store_true")
    command.add_argument("--parent", type=Path)
    commands.add_parser("rollback").add_argument("parent", type=Path)
    args = parser.parse_args()
    try:
        {"backup": backup, "verify": verify, "restore": restore, "rollback": rollback}[args.command](args)
    except (ValueError, OSError, KeyError, TypeError, tarfile.TarError, sqlite3.Error,
            subprocess.SubprocessError) as error:
        parser.exit(1, f"{args.command}: {error}\n")


if __name__ == "__main__":
    main()
