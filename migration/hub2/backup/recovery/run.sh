#!/bin/bash
set -euo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
sd=/dev/disk/by-id/mmc-SD64G_0xdae65fc2
uuid=20fe1490-9a5e-dd01-00ce-14909a5edd01
ssd=/dev/disk/by-uuid/$uuid
root=/run/hub2-source
destination=/run/hub2-samsung
mkdir -p "$root" "$destination"
for ((i=0; i<45; i++)); do
    if [[ -b "$sd-part2" && -b "$ssd" ]]; then break; fi
    sleep 1
done
[[ -b "$sd" && -b "$sd-part1" && -b "$sd-part2" && -b "$ssd" ]]
if lsblk -nrpo MOUNTPOINTS "$sd" | grep -q '[^[:space:]]'; then exit 1; fi
for dev in "$sd" "$sd-part1" "$sd-part2"; do blockdev --setro "$dev"; done
[[ $(blkid -s UUID -o value "$ssd") == "$uuid" ]]
[[ $(blkid -s TYPE -o value "$ssd") == ext4 ]]
[[ $(lsblk -nro PKNAME "$ssd") != "$(basename "$(realpath "$sd")")" ]]
trap 'cd /; if mountpoint -q "$root"; then umount "$root"; fi; if mountpoint -q "$destination"; then umount "$destination"; fi; rm -f /run/hub2-age-identity' EXIT
mount -t ext4 -o rw,nosuid,nodev "$ssd" "$destination"
cd "$destination"
[[ ! -L hub2 ]]
mkdir -p hub2
exec 9> .hub2-backup.lock
flock -n 9
write_state() {
    local phase=$1 error=$2
    if [[ "$phase" == ok ]]; then
        local manifest
        manifest=$(cat /run/hub2-img-result)
        printf '{"state":"ok","completed":%s,%s\n' "$(date +%s)" "${manifest#\{}"
    else
        printf '{"state":"%s","completed":%s,"error":"%s"}\n' "$phase" "$(date +%s)" "$error"
    fi > hub2/recovery-status.tmp
    sync -f hub2/recovery-status.tmp
    mv -T hub2/recovery-status.tmp hub2/recovery-status.json
    sync -f hub2
}
write_state running incomplete_recovery
fail() { write_state failed recovery_export_failed; }
trap fail ERR
mount -t ext4 -o ro,noload "$sd-part2" "$root"
install -m 600 "$root/etc/hanzhub-backup/age-identity" /run/hub2-age-identity
umount "$root"
modprobe fuse
HUB2_IMAGE_IDENTITY=/run/hub2-age-identity timeout -k 60s 3h bash /hub2-recovery/weekly.sh > /run/hub2-img-result
write_state ok none
