#!/bin/sh
set -eu
umask 077
cd "$(dirname "$0")"
scratch=$(mktemp -d)
export GNUPGHOME="$scratch/gpg" TMPDIR="$scratch"
trap 'rm -r -- "$scratch"' EXIT
if [ "${1:-}" = --without-gpg-agent ]; then
    # Exercise archive and SQLite behavior in sandboxes that block Unix sockets.
    mkdir "$scratch/bin"
    cat > "$scratch/bin/gpg" <<'EOF'
#!/bin/sh
set -eu
case "$*" in
    *--encrypt) cat > "$7" ;;
    *--decrypt*) cat "$3" ;;
    *) exit 2 ;;
esac
EOF
    chmod +x "$scratch/bin/gpg"
    export PATH="$scratch/bin:$PATH"
    TEST_FPR=0000000000000000000000000000000000000000
    printf '%s\n' 'Fixture only: GPG substituted, encryption untested.'
else
    mkdir "$GNUPGHOME"
    gpg --batch --pinentry-mode loopback --passphrase '' --quick-generate-key 'Fixture only' default default 1d
    TEST_FPR=$(gpg --batch --with-colons --list-keys | awk -F: '$1=="fpr" {print $10; exit}')
fi
export TEST_FPR
python3 -B - <<'PY'
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import bundle

scratch = Path(os.environ["TMPDIR"])
target = scratch / "export"
target.mkdir()
source = scratch / "live.sqlite"
with closing(sqlite3.connect(source)) as db:
    db.execute("pragma journal_mode=wal")
    db.execute("create table example (value)")
    db.execute("insert into example values ('committed in WAL')")
    db.commit()
    assert source.with_name(source.name + "-wal").stat().st_size > 0
    plan = scratch / "plan.json"
    plan.write_text(json.dumps({"fixture": {"files": [{
        "section": "data", "name": "fixture.sqlite", "source": str(source), "method": "sqlite"
    }]}}))
    args = SimpleNamespace(plan=plan, mount=target, uuid="fixture", recipient=os.environ["TEST_FPR"])
    for options, expected in [("ro", False), ("rw", True)]:
        with patch.object(bundle.os.path, "ismount", return_value=True), patch.object(
            bundle.subprocess, "check_output", return_value=json.dumps({
                "filesystems": [{"uuid": "fixture", "options": options}]
            }).encode()
        ):
            try:
                bundle.backup(args)
            except ValueError:
                assert not expected
            else:
                assert expected
    (exported,) = target.iterdir()
    subprocess.run(["./verify.sh", str(exported)], check=True)
    assert subprocess.check_output(["./restore.sh", str(exported), "--list"]).strip() == b"fixture"
    stage = scratch / "stage"
    stage.mkdir(mode=0o700)
    subprocess.run(["./restore.sh", str(exported), "--app", "fixture", "--parent", str(stage)], check=True)
    with closing(sqlite3.connect(stage / "staged/var/lib/hanzhub/fixture/fixture.sqlite")) as recovered:
        assert recovered.execute("select value from example").fetchone() == ("committed in WAL",)
    subprocess.run(["./rollback.sh", str(stage)], check=True)
    assert not (stage / "staged").exists()
    assert (stage / "rolled-back/var/lib/hanzhub/fixture/fixture.sqlite").is_file()
    with (exported / "bundle.tar.gz.gpg").open("ab") as corrupt:
        corrupt.write(b"tampered")
    assert subprocess.run(["./verify.sh", str(exported)]).returncode != 0
print("Fixture archive, verify, selective restore, rollback and corruption rejection OK")
PY
