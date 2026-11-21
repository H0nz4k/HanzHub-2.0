#!/usr/bin/env python3
"""Exercise selective restoration without touching the host destinations."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory

os.umask(0o077)
tool = Path(__file__).with_name("selective-restore.py")
with TemporaryDirectory() as workspace:
    root = Path(workspace)
    archive = root / "files.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, payload in (("./studio/flame.png", b"image"),
                              ("studio/settings", b"config"),
                              ("studio/project", b"project"),
                              ("etc/ssh/sshd_config", b"old ssh")):
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            tar.addfile(member, io.BytesIO(payload))
        link = tarfile.TarInfo("studio/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/shadow"
        tar.addfile(link)

    manifest = root / "manifest.json"
    studio = dict.fromkeys(("repo", "revision", "dependencies", "services", "ports",
                            "routes", "gpio", "apis", "mounts", "health", "backup",
                            "rollback"), [])
    studio["files"] = [
        {"source": "studio/flame.png", "section": "runtime", "name": "assets/flame.png"},
        {"source": "studio/settings", "section": "config", "name": "settings"},
        {"source": "studio/project", "section": "data", "name": "project"},
    ]

    def save():
        manifest.write_text(json.dumps({"henk-studio": studio}))

    def run(*args, ok=True):
        result = subprocess.run([sys.executable, "-B", tool, archive, *args],
                                capture_output=True, text=True)
        assert (result.returncode == 0) == ok, result.stderr
        return result

    save()
    assert len(run("inventory").stdout.splitlines()) == 5
    assert json.loads(run("plan", manifest).stdout)["bytes"] == 18
    for path in ("opt", "etc/hanzhub", "var/lib/hanzhub"):
        (root / path).mkdir(parents=True)
    install = ("install", manifest, "--app", "henk-studio", "--root", root)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    run(*install, "--sha256", "0" * 64, ok=False)
    run(*install, "--sha256", checksum, "--reserve-bytes", str(2**60), ok=False)
    assert not list(root.glob("**/.henk-studio-restore-*"))
    assert not (root / "opt/henk-studio").exists()
    run(*install, "--sha256", checksum)
    assert (root / "opt/henk-studio/assets/flame.png").read_bytes() == b"image"
    assert (root / "etc/hanzhub/henk-studio/settings").read_bytes() == b"config"
    assert (root / "var/lib/hanzhub/henk-studio/project").read_bytes() == b"project"
    assert not (root / "etc/ssh").exists()
    run(*install, "--sha256", checksum, ok=False)
    studio["files"][0]["source"] = "studio/link"
    save()
    run("plan", manifest, ok=False)
    studio["files"][0]["name"] = "../escape"
    save()
    run("plan", manifest, ok=False)
print("Selective restore test passed")
