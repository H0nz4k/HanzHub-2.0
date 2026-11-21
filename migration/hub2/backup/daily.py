#!/usr/bin/python3
"""Encrypted daily application backup with database-native snapshots."""
from contextlib import closing, contextmanager
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

SSD = Path("/mnt/hanzhub-backup")
UUID = "20fe1490-9a5e-dd01-00ce-14909a5edd01"
STATUS = Path("/var/lib/hanzhub-backup-status")
STAGE = Path("/run/hanzhub-backup/staging")
REPO = "hub2/restic"
MIN_FREE = 25 * 1024**3
PASSWORD = "/etc/hanzhub-backup/restic-password"
ROOTS = ("/opt", "/etc", "/var/lib/hanzhub", "/boot/firmware", "/var/lib/dpkg")
VOLUMES = ("stack_grafana_data", "stack_influxdb_config")
IMAGE = "influxdb"
SQLITE_HEADER = b"SQLite format 3\0"


def run(*args, **options):
    return subprocess.run(args, check=True, text=True, **options)


def status(name, **updates):
    path = STATUS / (name + ".json")
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        data = {}
    data.update(updates)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data) + "\n")
    temp.chmod(0o644)
    temp.replace(path)


def storage():
    result = subprocess.run(("findmnt", "-n", "-o", "UUID,FSTYPE,OPTIONS",
                             "--mountpoint", "."), capture_output=True, text=True)
    columns = result.stdout.split()
    if (len(columns) != 3 or columns[:2] != [UUID, "ext4"]
            or "rw" not in columns[2].split(",")):
        status("storage", state="failed", free_bytes=None)
        raise ValueError("Expected writable Samsung SSD mount")
    free = shutil.disk_usage(".").free
    status("storage", state="low" if free < MIN_FREE else "ok", free_bytes=free)
    if free < MIN_FREE:
        raise ValueError("Insufficient SSD space")
    return free


def restic(*args, **options):
    return run("restic", "-r", REPO, "--password-file", PASSWORD, *args, **options)


def sqlite_copies(roots):
    excluded = []
    for root in roots:
        for directory, _, names in os.walk(root, followlinks=False):
            for name in names:
                source = Path(directory, name)
                if source.is_symlink() or not source.is_file():
                    continue
                try:
                    with source.open("rb") as stream:
                        if stream.read(len(SQLITE_HEADER)) != SQLITE_HEADER:
                            continue
                except FileNotFoundError:
                    continue
                if shutil.disk_usage(".").free - source.stat().st_size < MIN_FREE:
                    raise ValueError("Insufficient SSD space for SQLite working copy")
                target = STAGE / "sqlite" / str(source).lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=20)) as db:
                    with closing(sqlite3.connect(target)) as copy:
                        db.backup(copy, pages=256, sleep=0.1)
                        if copy.execute("PRAGMA quick_check").fetchone() != ("ok",):
                            raise ValueError("SQLite backup integrity check failed")
                stat = source.stat()
                os.chown(target, stat.st_uid, stat.st_gid)
                target.chmod(stat.st_mode & 0o7777)
                for suffix in ("", "-wal", "-shm", "-journal"):
                    excluded.append(str(source) + suffix)
    return excluded


def influx_backup():
    target = STAGE / "influxdb"
    target.mkdir(mode=0o700)
    image = run("docker", "inspect", "--format", "{{.Image}}", IMAGE,
                capture_output=True).stdout.strip()
    run("docker", "run", "--rm", "--pull=never", "--network=container:influxdb",
        "--mount", f"type=bind,src={target},dst=/backup",
        "--mount", "type=bind,src=/opt/meteo3/secrets/influx_token,dst=/run/token,readonly",
        "--entrypoint", "/bin/sh", image, "-ec",
        'export INFLUX_TOKEN="$(cat /run/token)"; exec influx backup /backup')
    if not list(target.glob("*.manifest")):
        raise ValueError("InfluxDB did not produce its backup manifest")


@contextmanager
def encrypted_scratch():
    parent = Path("hub2")
    parent.mkdir(mode=0o700, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=".scratch-", dir=parent))
    STAGE.mkdir(mode=0o700)
    process = None
    try:
        run("gocryptfs", "-q", "-init", "-passfile", PASSWORD, str(scratch))
        process = subprocess.Popen(("gocryptfs", "-q", "-fg", "-passfile", PASSWORD,
                                    str(scratch), str(STAGE)))
        for _ in range(100):
            if STAGE.is_mount():
                break
            if process.poll() is not None:
                raise ValueError("Encrypted scratch mount failed")
            time.sleep(0.1)
        else:
            raise ValueError("Encrypted scratch mount timed out")
        yield
    finally:
        if STAGE.is_mount():
            run("fusermount3", "-u", str(STAGE))
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        shutil.rmtree(scratch)


def repository_bytes():
    if not Path(REPO).is_dir():
        return 0
    return int(run("du", "-s", "-B1", REPO, capture_output=True).stdout.split()[0])


def backup(paths, exclude):
    command = ("restic", "-r", REPO, "--password-file", PASSWORD, "backup", "--json",
               "--one-file-system", "--host", "HUB2", "--tag", "hub2-daily",
               "--exclude-file", str(exclude), *paths)
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as process:
        while True:
            try:
                output, _ = process.communicate(timeout=5)
                break
            except subprocess.TimeoutExpired:
                if shutil.disk_usage(".").free < MIN_FREE:
                    process.terminate()
                    process.communicate(timeout=30)
                    raise ValueError("SSD reserve reached during Restic backup")
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
    return next(row for line in output.splitlines()
                if (row := json.loads(line)).get("message_type") == "summary")


def daily():
    repository = Path(REPO)
    if repository.is_symlink() or (repository.exists() and repository.stat().st_dev != Path(".").stat().st_dev):
        raise ValueError("Unexpected Restic repository path")
    volumes = tuple(run("docker", "volume", "inspect", "-f", "{{.Mountpoint}}", name,
                        capture_output=True).stdout.strip() for name in VOLUMES)
    if any(not Path(path).is_dir() or not path.startswith("/var/lib/docker/volumes/")
           for path in volumes):
        raise ValueError("Missing Docker persistent volume")
    excluded = sqlite_copies(("/opt", "/var/lib/hanzhub", *volumes))
    influx_backup()
    # These are sidecars of databases that might be created during the run.
    patterns = [*excluded, "*-wal", "*-shm", "*-journal"]
    exclude = STAGE.parent / "exclude.txt"
    exclude.write_text("\n".join(patterns) + "\n")
    before = repository_bytes()
    if not Path(REPO, "config").is_file():
        restic("init")
    summary = backup((*ROOTS, *volumes, str(STAGE)), exclude)
    restic("check", "--read-data")
    storage()
    # A policy preview is deliberately non-destructive.
    restic("forget", "--dry-run", "--keep-within", "14d", "--keep-last", "1",
           "--tag", "hub2-daily")
    return dict(snapshot=summary["snapshot_id"], last_success=int(time.time()),
           bytes=summary["total_bytes_processed"], stored_bytes=max(0, repository_bytes()-before),
           integrity_verified=True, integrity_checked=int(time.time()), error=None)


def main():
    action = sys.argv[1]
    if action == "alert":
        unit = sys.argv[2]
        kind = "daily" if unit == "hanzhub-backup-daily.service" else "weekly"
        status(kind, state="failed", failed=int(time.time()))
        print(f"Backup failure: {unit}; see journal for the failing unit", file=sys.stderr)
        return
    status(action, state="running", started=int(time.time()), error=None)
    try:
        os.chdir(SSD)
        storage()
        parent = Path("hub2")
        if parent.is_symlink() or (parent.exists() and parent.stat().st_dev != Path(".").stat().st_dev):
            raise ValueError("Unexpected backup directory")
        fd = os.open(".hub2-backup.lock", os.O_NOFOLLOW | os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if action == "daily":
                with encrypted_scratch():
                    summary = daily()
                status("daily", state="ok", restore_tested=False, **summary)
                print("Verified Restic snapshot", summary["snapshot"], "logical bytes", summary["bytes"])
                return
            result = subprocess.run(("/bin/bash", "/opt/hanzhub/backup/weekly.sh"),
                                    text=True, stdout=subprocess.PIPE)
            if result.returncode == 75:
                status("weekly", error="offline_source_required")
            result.check_returncode()
            status("weekly", state="ok", last_success=int(time.time()),
                   **json.loads(result.stdout), error=None)
    except (OSError, ValueError, subprocess.CalledProcessError, sqlite3.Error) as error:
        code = ("offline_source_required" if (action == "weekly"
                and getattr(error, "returncode", None) == 75) else type(error).__name__)
        status(action, state="failed", error=code, failed=int(time.time()))
        raise


if __name__ == "__main__":
    main()
