#!/bin/bash
# Called from daily.py after the Samsung destination is verified and pinned as cwd.
set -euo pipefail
umask 077
sd=/dev/disk/by-id/mmc-SD64G_0xdae65fc2
identity=/etc/hanzhub-backup/age-identity
parent=hub2/images
reserve=$((25 * 1024**3))

[[ -b "$sd" && -b "$sd-part1" && -b "$sd-part2" ]]
# Abort on live root, mounted partitions, or a card still writable by the kernel.
if [[ $(blockdev --getro "$sd") != 1 ]] ||
   lsblk -nrpo MOUNTPOINTS "$sd" | grep -q '[^[:space:]]'; then
    echo 'Weekly IMG blocked: use a separate recovery OS and an unmounted read-only HUB2 SD.' >&2
    exit 75
fi
for disk in "$sd" "$sd-part1" "$sd-part2"; do
    node=$(basename "$(realpath "$disk")")
    [[ -z $(ls -A "/sys/class/block/$node/holders") ]]
done
source_bytes=$(blockdev --getsize64 "$sd")
available=$(df -B1 --output=avail . | tail -1)
(( available >= source_bytes + reserve )) || { echo 'Insufficient SSD capacity' >&2; exit 1; }
sfdisk --verify "$sd" >&2
fsck.fat -n "$sd-part1" >&2
e2fsck -fn "$sd-part2" >&2

probe=$(mktemp -d /run/hanzhub-image-check.XXXXXX)
clean_probe() {
    if mountpoint -q "$probe/boot"; then umount "$probe/boot"; fi
    if mountpoint -q "$probe/root"; then umount "$probe/root"; fi
    rmdir "$probe/boot" "$probe/root" "$probe"
}
trap clean_probe EXIT
mkdir "$probe/boot" "$probe/root"
mount -o ro "$sd-part1" "$probe/boot"
mount -o ro,noload "$sd-part2" "$probe/root"
test -s "$probe/boot/config.txt"
test -s "$probe/boot/cmdline.txt"
test -s "$probe/root/etc/fstab"
find "$probe/boot" -maxdepth 1 -name 'kernel*.img' -size +0c | grep -q .
root_partuuid=$(blkid -s PARTUUID -o value "$sd-part2")
grep -Fq "root=PARTUUID=$root_partuuid" "$probe/boot/cmdline.txt"
clean_probe
trap - EXIT

[[ ! -L "$parent" ]]
mkdir -p "$parent"
test "$(stat -c %d "$parent")" = "$(stat -c %d .)"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
partial="$parent/$stamp.partial"
complete="$parent/$stamp"
mkdir "$partial"
test ! -e "$complete"
recipient=$(age-keygen -y "$identity")
dd if="$sd" bs=8M iflag=fullblock status=none | age -r "$recipient" -o "$partial/hub2.img.age"
raw_hash=$(sha256sum "$sd" | cut -d' ' -f1)
verified_hash=$(age -d -i "$identity" "$partial/hub2.img.age" | sha256sum | cut -d' ' -f1)
test "$raw_hash" = "$verified_hash"
size=$(stat -c %s "$partial/hub2.img.age")
printf '%s  hub2.img\n' "$raw_hash" > "$partial/IMG.sha256"
(cd "$partial" && sha256sum hub2.img.age > SHA256SUMS && sha256sum --check SHA256SUMS >&2)
printf '{"bytes":%s,"raw_bytes":%s,"filesystem_verified":true,"boot_files_verified":true,"sha256_verified":true}\n' \
    "$size" "$source_bytes" > "$partial/verified.json"
sync -f "$partial"
mv -T "$partial" "$complete"
sync -f "$parent"
count=0
while IFS= read -r previous; do
    [[ -s "$parent/$previous/verified.json" && -s "$parent/$previous/SHA256SUMS" ]] || continue
    ((++count))
    if (( count > 2 )); then
        printf 'Weekly retention candidate (approval required): %s/%s\n' "$parent" "$previous" >&2
    fi
done < <(find "$parent" -mindepth 1 -maxdepth 1 -type d -name '????????T??????Z' -printf '%f\n' | sort -r)
cat "$complete/verified.json"
