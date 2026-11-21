#!/bin/sh
# Output is private operational inventory. The caller chooses where to store it.
set -u
failed=0
capture() {
    printf '\n[%s]\n' "$1"
    shift
    if "$@"; then
        printf 'status=ok\n'
    else
        printf 'status=unavailable\n'
        failed=1
    fi
}
capture time date -u -Iseconds
capture host uname -a
capture os cat /etc/os-release
capture disks lsblk -o NAME,PATH,MODEL,SERIAL,WWN,SIZE,TRAN,FSTYPE,UUID,RO,MOUNTPOINTS
capture mounts findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS
capture services systemctl list-units --all --type=service --no-pager
capture installed systemctl list-unit-files --no-pager
capture timers systemctl list-timers --all --no-pager
capture user-services systemctl --user list-units --all --no-pager
capture docker docker ps -a --no-trunc
capture compose docker compose ls --all
capture images docker image ls --digests
capture volumes docker volume ls
capture docker-mounts sh -c '
    ids=$(docker ps -aq) || exit
    [ -z "$ids" ] || docker inspect --format "{{.Name}} {{.Image}} {{json .Mounts}} {{json .NetworkSettings.Ports}}" $ids
'
capture listeners sh -c 'output=$(ss -H -lntupx) && [ -n "$output" ] && printf "%s\n" "$output"'
capture gpio sh -c 'output=$(gpioinfo) && [ -n "$output" ] && printf "%s\n" "$output"'
capture pinmux pinctrl get
capture usb lsusb
capture hdmi sh -c 'for status in /sys/class/drm/*HDMI*/status; do printf "%s " "$status"; cat "$status" || exit; done'
capture app-dirs find /opt /var/lib -maxdepth 1 -type d
capture candidates find /opt -xdev -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -iname '*compose*.yml' -o -iname '*compose*.yaml' \)
exit "$failed"
