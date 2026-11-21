#!/bin/bash
# Called from daily.py after the Samsung destination is verified and pinned as cwd.
set -euo pipefail
umask 077
sd=/dev/disk/by-id/mmc-SD64G_0xdae65fc2
identity=${HUB2_IMAGE_IDENTITY:-/etc/hanzhub-backup/age-identity}
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
(( available >= 2 * source_bytes + reserve + 4 * 1024**3 )) || {
    echo 'Insufficient SSD capacity for image and isolated restore' >&2
    exit 1
}
package=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
bash "$package/verify-image.sh" "$sd" "$sd-part1" "$sd-part2"

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
# Materialize the decrypted image only on a short-lived encrypted filesystem.
# The read-only loop device verifies the actual restored partition contents.
work=$(mktemp -d /run/hub2-img-restore.XXXXXX)
loop=
worker=
cleanup_restore() {
    if [[ -n "$loop" ]]; then losetup -d "$loop"; fi
    if mountpoint -q "$work/plain"; then fusermount3 -u "$work/plain"; fi
    if [[ -n "$worker" ]]; then
        kill "$worker" 2>/dev/null || true
        wait "$worker" || true
    fi
    rm -r -- "$work"
    if [[ -d "$partial/restore.encrypted" ]]; then rm -r -- "$partial/restore.encrypted"; fi
}
trap cleanup_restore EXIT
mkdir "$work/plain" "$partial/restore.encrypted"
head -c 48 /dev/urandom | base64 > "$work/pass"
gocryptfs -q -init -passfile "$work/pass" "$partial/restore.encrypted"
gocryptfs -q -fg -passfile "$work/pass" "$partial/restore.encrypted" "$work/plain" &
worker=$!
for ((i=0; i<20; i++)); do
    if mountpoint -q "$work/plain"; then break; fi
    kill -0 "$worker"
    sleep 1
done
mountpoint -q "$work/plain"
age -d -i "$identity" "$partial/hub2.img.age" |
    dd of="$work/plain/hub2.img" bs=8M iflag=fullblock conv=sparse status=none
test "$(stat -c %s "$work/plain/hub2.img")" -eq "$source_bytes"
verified_hash=$(sha256sum "$work/plain/hub2.img" | cut -d' ' -f1)
test "$raw_hash" = "$verified_hash"
loop=$(losetup --find --show --read-only --partscan "$work/plain/hub2.img")
for ((i=0; i<20; i++)); do
    if [[ -b "${loop}p1" && -b "${loop}p2" ]]; then break; fi
    sleep 1
done
bash "$package/verify-image.sh" "$loop" "${loop}p1" "${loop}p2"
cleanup_restore
trap - EXIT
size=$(stat -c %s "$partial/hub2.img.age")
printf '%s  hub2.img\n' "$raw_hash" > "$partial/IMG.sha256"
(cd "$partial" && sha256sum hub2.img.age > SHA256SUMS && sha256sum --check SHA256SUMS >&2)
printf '{"generation":"%s","bytes":%s,"raw_bytes":%s,"filesystem_verified":true,"boot_files_verified":true,"sha256_verified":true,"restore_tested":true}\n' \
    "$stamp" "$size" "$source_bytes" > "$partial/verified.json"
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
