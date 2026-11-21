#!/usr/bin/env python3
"""Plan and stage explicit file selections from the legacy local tar.gz."""
import argparse
from collections import defaultdict
from contextlib import ExitStack
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
from tempfile import TemporaryDirectory

from bundle import APP, SECTIONS, require

SECTIONS = {key: SECTIONS[key] for key in ("runtime", "config", "data")}
BLOCKED = {"operations-broker", "hanzhub-operations-broker", "ili9486", "lcd35"}
CHUNK = 1024 * 1024
MIN_RESERVE = 2 * 1024**3
METADATA = ("repo", "revision", "dependencies", "services", "ports", "routes",
            "gpio", "apis", "mounts", "health", "backup", "rollback")


def relative(name):
    require(isinstance(name, str) and not name.startswith("/")
            and all(part != ".." for part in name.split("/"))
            and all(ord(char) >= 32 and ord(char) != 127 for char in name),
            "Invalid relative path")
    path = PurePosixPath(name)
    require(path.parts, "Empty relative path")
    return path


def load_plan(path):
    plan = json.loads(path.read_text())
    require(isinstance(plan, dict) and plan, "Expected an app manifest object")
    destinations = set()
    for app, manifest in plan.items():
        require(APP.fullmatch(app) and app not in BLOCKED, f"Invalid app ID: {app}")
        require(all(key in manifest for key in METADATA), f"Incomplete manifest: {app}")
        require(isinstance(manifest["files"], list) and manifest["files"],
                f"No files selected: {app}")
        for entry in manifest["files"]:
            relative(entry["source"])
            section = entry["section"]
            require(section in SECTIONS, f"Unknown section: {section}")
            target = (app, section, relative(entry["name"]))
            require(target not in destinations, f"Duplicate destination: {target}")
            destinations.add(target)
    for app, section, path in destinations:
        require(not any((app, section, parent) in destinations for parent in path.parents),
                f"File/directory conflict: {app}/{path}")
    return plan


def scan(source, wanted=None):
    found = {}
    with tarfile.open(fileobj=source, mode="r|gz", stream=True) as archive:
        for member in archive:
            if wanted is None:
                print(json.dumps({"path": member.name, "bytes": member.size,
                                  "regular": member.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                                  and member.sparse is None}, ensure_ascii=True))
                continue
            name = PurePosixPath(member.name)
            if name not in wanted:
                continue
            relative(member.name)
            require(name not in found, f"Duplicate source: {name}")
            require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                    and member.sparse is None and member.size >= 0,
                    f"Expected a plain regular file: {name}")
            found[name] = member.size
            if wanted[name]:
                wanted[name](archive, member)
    if wanted is not None:
        require(found.keys() == wanted.keys(),
                f"Missing sources: {sorted(str(path) for path in wanted.keys() - found.keys())}")
    return found


def capacity(path, reserve, blocks=0, nodes=0):
    fs = os.statvfs(path)
    require(fs.f_bavail * fs.f_frsize >= reserve + blocks,
            f"Insufficient free space with reserve: {path}")
    require(fs.f_files == 0 or fs.f_favail >= nodes + 1024,
            f"Insufficient free inodes with reserve: {path}")
    return fs.f_frsize


def prepare_targets(root, app, entries, sizes, reserve):
    volumes = {}
    targets = {}
    directories = defaultdict(set)
    for entry in entries:
        section = entry["section"]
        parent = root / SECTIONS[section]
        for directory in (*reversed(parent.parents), parent):
            info = directory.lstat()
            ancestor = directory in root.parents
            require(stat.S_ISDIR(info.st_mode)
                    and (ancestor or info.st_uid in (0, os.geteuid()))
                    and (not info.st_mode & 0o022 or (ancestor and info.st_mode & stat.S_ISVTX)),
                    f"Unsafe target parent: {directory}")
        target = parent / app
        require(not os.path.lexists(target), f"Destination already exists: {target}")
        targets[section] = target
        device = parent.stat().st_dev
        volume = volumes.setdefault(device, [parent, 0, 0])
        block = os.statvfs(parent).f_frsize
        size = sizes[relative(entry["source"])]
        volume[1] += ((size + block - 1) // block) * block + block
        volume[2] += 1
        for path in relative(entry["name"]).parents:
            directories[device].add((section, path))
    for device, (parent, blocks, nodes) in volumes.items():
        directory_count = len(directories[device])
        capacity(parent, reserve, blocks + directory_count * os.statvfs(parent).f_frsize,
                 nodes + directory_count)
    return targets


def publish(source, target):
    # Linux RENAME_NOREPLACE prevents overwriting a concurrent install.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.renameat2(-100, os.fsencode(source), -100, os.fsencode(target), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(target))


def install(source, app, entries, sizes, root, reserve, before):
    targets = prepare_targets(root, app, entries, sizes, reserve)
    with ExitStack() as stack:
        stages = {section: Path(stack.enter_context(TemporaryDirectory(
            prefix=f".{app}-restore-", dir=target.parent)))
            for section, target in targets.items()}
        writers = defaultdict(list)
        for entry in entries:
            stage = stages[entry["section"]]
            path = stage / relative(entry["name"])
            writers[relative(entry["source"])].append((stage, path))

        def copy(archive, member):
            name = relative(member.name)
            require(member.size == sizes[name], f"Source size changed: {name}")
            with ExitStack() as handles:
                outputs = []
                for stage, path in writers[name]:
                    capacity(stage, reserve, CHUNK, len(path.relative_to(stage).parts))
                    path.parent.mkdir(parents=True, exist_ok=True)
                    output = handles.enter_context(path.open("xb"))
                    outputs.append((path, output))
                with archive.extractfile(member) as payload:
                    while chunk := payload.read(CHUNK):
                        for path, output in outputs:
                            capacity(path.parent, reserve, len(chunk))
                            output.write(chunk)
                for path, output in outputs:
                    os.fchmod(output.fileno(), 0o700 if member.mode & 0o100 else 0o600)
                    output.flush()
                    os.fsync(output.fileno())

        require(stamp(source) == before, "Archive changed before extraction")
        scan(source, dict.fromkeys(writers, copy))
        require(stamp(source) == before, "Archive changed during extraction")
        installed = []
        try:
            for section, target in targets.items():
                publish(stages[section], target)
                installed.append((target, stages[section]))
        except BaseException:
            for target, stage in reversed(installed):
                publish(target, stage)
            raise


def stamp(source):
    info = os.fstat(source.fileno())
    return info.st_size, info.st_mtime_ns, info.st_ctime_ns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inventory")
    for command in ("plan", "install"):
        options = commands.add_parser(command)
        options.add_argument("manifest", type=Path)
        if command == "install":
            options.add_argument("--app", required=True)
            options.add_argument("--sha256", required=True, help="trusted archive SHA-256")
            options.add_argument("--root", type=Path, default=Path("/"))
            options.add_argument("--reserve-bytes", type=int, default=MIN_RESERVE)
    args = parser.parse_args()
    os.umask(0o077)
    with args.archive.open("rb") as source:
        require(stat.S_ISREG(os.fstat(source.fileno()).st_mode), "Expected a regular archive")
        if args.command == "inventory":
            scan(source)
            return
        plan = load_plan(args.manifest)
        before = stamp(source)
        if args.command == "install":
            require(args.app in plan, "Application missing from manifest")
            require(args.reserve_bytes >= MIN_RESERVE, "Minimum reserve is 2 GiB")
            require(re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256)
                    and hashlib.file_digest(source, "sha256").hexdigest() == args.sha256.lower(),
                    "Archive SHA-256 mismatch")
            source.seek(0)
            plan = {args.app: plan[args.app]}
        wanted = {relative(entry["source"]): None for app in plan.values()
                  for entry in app["files"]}
        sizes = scan(source, wanted)
        require(stamp(source) == before, "Archive changed during verification")
        for app, manifest in plan.items():
            sections = defaultdict(int)
            for entry in manifest["files"]:
                sections[entry["section"]] += sizes[relative(entry["source"])]
            print(json.dumps({"app": app, "bytes": sum(sections.values()),
                              "sections": sections, "dependencies": manifest["dependencies"]}))
        if args.command == "install":
            source.seek(0)
            root = args.root.absolute()
            require(root.resolve(strict=True) == root, "Target root must be canonical")
            if root != Path("/"):
                require(root.stat().st_uid == os.geteuid() and root.stat().st_mode & 0o077 == 0,
                        "Test root must be private and owned by the caller")
            else:
                require(os.geteuid() == 0, "Host installation requires root")
            install(source, args.app, plan[args.app]["files"], sizes, root, args.reserve_bytes, before)
            print(f"Files installed: {args.app}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, EOFError, tarfile.TarError) as error:
        raise SystemExit(f"Restore stopped: {error}") from None
