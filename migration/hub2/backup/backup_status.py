"""Read only the fixed, sanitized status contract for the dashboard."""
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path("/var/lib/hanzhub-backup-status")
DISK = "/mnt/hanzhub-backup"
UUID = "20fe1490-9a5e-dd01-00ce-14909a5edd01"
MIN_FREE = 25 * 1024**3


def backup_status():
    now = int(time.time())

    def summary(kind, max_age):
        try:
            with (ROOT / (kind + ".json")).open() as stream:
                data = json.loads(stream.read(4096))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        last = data.get("last_success")
        last = last if type(last) is int and 0 < last <= now else None
        state = data.get("state")
        if state == "ok" and (last is None or now - last > max_age):
            state = "stale"
        if state == "running" and now - (data.get("started") or 0) > 8 * 3600:
            state = "stale"
        result = dict(state=state if state in ("ok", "stale", "running", "failed") else "unknown",
                      last_success=last, size_bytes=data.get("bytes"), stored_bytes=data.get("stored_bytes"))
        result.update({key: data.get(key) is True for key in
                      ("integrity_verified", "filesystem_verified", "boot_files_verified",
                       "sha256_verified", "physical_boot_tested", "restore_tested")})
        result["integrity_checked"] = data.get("integrity_checked")
        if state == "failed":
            result["detail"] = ("Vyžaduje odpojenou systémovou SD"
                                if data.get("error") == "offline_source_required"
                                else "Záloha selhala, podrobnosti v systémovém žurnálu")
        return result

    try:
        output = subprocess.run(("findmnt", "--task", "1", "-n", "-o", "MAJ:MIN,FSTYPE,OPTIONS",
                                 "--mountpoint", DISK), check=True, capture_output=True,
                                text=True, timeout=2).stdout.split()
        if len(output) != 3 or output[1] != "ext4" or "rw" not in output[2].split(","):
            raise ValueError("Incorrect backup disk")
        identity = Path("/run/udev/data/b" + output[0]).read_text().splitlines()
        if "E:ID_FS_UUID=" + UUID not in identity:
            raise ValueError("Incorrect backup disk")
        free = shutil.disk_usage(DISK).free
        storage = dict(state="ok" if free >= MIN_FREE else "low", free_bytes=free)
    except (OSError, ValueError, subprocess.SubprocessError):
        storage = dict(state="failed", free_bytes=None)
    return dict(daily=summary("daily", 2 * 86400), weekly=summary("weekly", 10 * 86400),
                storage=storage)
