#!/bin/bash
# Verify real data in a disposable local restore directory and Influx instance.
set -euo pipefail
umask 077
ssd=/mnt/hanzhub-backup
uuid=20fe1490-9a5e-dd01-00ce-14909a5edd01
test "$(findmnt -n -o UUID --mountpoint "$ssd")" = "$uuid"
cd "$ssd"
snapshot=${1:?Usage: restore-check.sh SNAPSHOT_ID}
[[ "$snapshot" =~ ^[a-f0-9]{8,64}$ ]]
work=$(mktemp -d /run/hub2-restore.XXXXXX)
name="hub2-restore-${work##*.}"
cleanup() {
    if [[ ${created:-no} == yes ]]; then docker rm -f "$name" >/dev/null; fi
    rm -r -- "$work"
}
trap cleanup EXIT
restic -r hub2/restic --password-file /etc/hanzhub-backup/restic-password     restore "$snapshot" --verify --target "$work"     --include /run/hanzhub-backup/staging/sqlite/var/lib/hanzhub/coinlist/kartoteka.sqlite     --include /run/hanzhub-backup/staging/sqlite/var/lib/docker/volumes/stack_grafana_data/_data/grafana.db     --include /run/hanzhub-backup/staging/influxdb

staged="$work/run/hanzhub-backup/staging"
python3 - "$staged/sqlite" <<'PY'
import sqlite3
import sys
from pathlib import Path

root = Path(sys.argv[1])
for app, path in (
    ("CoinList", "var/lib/hanzhub/coinlist/kartoteka.sqlite"),
    ("Grafana", "var/lib/docker/volumes/stack_grafana_data/_data/grafana.db"),
):
    with sqlite3.connect((root / path).as_uri() + "?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",), app
        tables, = db.execute("select count(*) from sqlite_master where type='table'").fetchone()
        assert tables > 0, app
        print(f"{app}: {tables} restored tables; integrity ok")
PY

image=$(docker inspect --format '{{.Image}}' influxdb)
docker run -d --name "$name" --network none --pull=never     --tmpfs /var/lib/influxdb2 --tmpfs /etc/influxdb2     --mount "type=bind,src=$staged/influxdb,dst=/backup,readonly"     --entrypoint /usr/local/bin/influxd "$image" >/dev/null
created=yes
for _ in {1..30}; do
    if docker exec "$name" influx ping >/dev/null 2>&1; then break; fi
    sleep 1
done
docker exec "$name" influx ping >/dev/null
docker exec "$name" /bin/sh -ec '
  export INFLUX_TOKEN="$(head -c 48 /dev/urandom | base64 | tr -d "\n")"
  influx setup --username restore --password "$(head -c 24 /dev/urandom | base64)" \
      --org restore --bucket initial --token "$INFLUX_TOKEN" --force >/dev/null
  influx restore /backup --org vysilac_v3 --bucket meteo --new-bucket hub2-restore-meteo --new-org restore
  influx bucket list --org restore --name hub2-restore-meteo --json
' | python3 -c 'import json,sys; s=sys.stdin.read(); x=json.loads(s[s.index("["):]); assert any(v["name"]=="hub2-restore-meteo" for v in x); print("InfluxDB: Meteo restored into isolated container")'
python3 - "$snapshot" <<'PY'
import json
import sys
from pathlib import Path
path = Path("/var/lib/hanzhub-backup-status/daily.json")
data = json.loads(path.read_text())
if (data.get("snapshot") or "")[:8] != sys.argv[1][:8] or data.get("state") != "ok":
    raise SystemExit("Restored snapshot is not the latest recorded daily backup")
data["restore_tested"] = True
temp = path.with_suffix(".restore-tmp")
temp.write_text(json.dumps(data) + "\n")
temp.chmod(0o644)
temp.replace(path)
PY
