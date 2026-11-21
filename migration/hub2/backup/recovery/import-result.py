"""Import status from the verified SSD after returning to the normal OS."""
import json
import os
from pathlib import Path
import re
import time

from daily import SSD, STATUS, status, storage

os.chdir(SSD)
storage()
source = Path("hub2/recovery-status.json")
if not source.is_file():
    raise SystemExit(0)
with source.open() as stream:
    result = json.loads(stream.read(4096))
stamp = result.get("completed")
if type(stamp) is not int or not 1577836800 <= stamp <= time.time() + 300:
    raise ValueError("Invalid recovery timestamp")
try:
    previous = json.loads((STATUS / "weekly.json").read_text())
except FileNotFoundError:
    previous = {}
if stamp <= previous.get("recovery_completed", 0):
    raise SystemExit(0)
if result.get("state") == "ok":
    flags = ("filesystem_verified", "boot_files_verified", "sha256_verified", "restore_tested")
    if not all(result.get(key) is True for key in flags):
        raise ValueError("Missing recovery verification")
    generation = result.get("generation")
    if not isinstance(generation, str) or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", generation):
        raise ValueError("Invalid recovery generation")
    folder = Path("hub2/images") / generation
    size = result.get("bytes")
    if type(size) is not int or size <= 0:
        raise ValueError("Invalid recovery image size")
    image = folder / "hub2.img.age"
    if image.is_symlink() or image.stat().st_size != size:
        raise ValueError("The verified recovery image is missing or has changed size")
    if not all((folder / name).is_file() for name in ("IMG.sha256", "SHA256SUMS", "verified.json")):
        raise ValueError("Missing recovery checksums")
    status("weekly", state="ok", last_success=stamp, recovery_completed=stamp, bytes=size,
           error=None, **{key: True for key in flags})
else:
    status("weekly", state="failed", recovery_completed=stamp, error="recovery_export_failed")
