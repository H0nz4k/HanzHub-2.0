#!/bin/bash
set -euo pipefail
umask 077
package=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
expected=20fe1490-9a5e-dd01-00ce-14909a5edd01
[[ "$(findmnt -n -o UUID --mountpoint /mnt/hanzhub-backup)" == "$expected" ]]
for tool in restic gocryptfs fusermount3 age age-keygen docker sfdisk e2fsck fsck.fat; do
    command -v "$tool" >/dev/null
done
install -d -m 755 /opt/hanzhub/backup
install -d -m 700 /etc/hanzhub-backup
python3 - <<'PY'
import os
from pathlib import Path
import secrets

path = Path("/etc/hanzhub-backup/restic-password")
if not path.exists():
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        out.write(secrets.token_urlsafe(48) + "\n")
PY
test -s /etc/hanzhub-backup/age-identity ||
    age-keygen -o /etc/hanzhub-backup/age-identity 2>/dev/null
install -m 644 "$package"/{daily.py,weekly.sh,restore-check.sh} /opt/hanzhub/backup/
install -m 644 "$package"/backup_status.py "$package"/../dashboard-web.py /opt/hanzhub/hub2/
install -m 644 "$package"/*.{mount,service,timer} /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify hanzhub-backup-{daily,weekly}.{service,timer}
systemctl enable --now hanzhub-backup-daily.timer hanzhub-backup-weekly.timer
systemctl restart hanzhub-dashboard2
