#!/bin/bash
# Inspect a read-only block device with a HUB2 boot and root partition.
set -euo pipefail
disk=$1
boot=$2
root=$3
[[ $(blockdev --getro "$disk") == 1 ]]
sfdisk --verify "$disk" >&2
fsck.fat -n "$boot" >&2
e2fsck -fn "$root" >&2

probe=$(mktemp -d /run/hanzhub-image-check.XXXXXX)
cleanup() {
    if mountpoint -q "$probe/boot"; then umount "$probe/boot"; fi
    if mountpoint -q "$probe/root"; then umount "$probe/root"; fi
    rmdir "$probe/boot" "$probe/root" "$probe"
}
trap cleanup EXIT
mkdir "$probe/boot" "$probe/root"
mount -o ro "$boot" "$probe/boot"
mount -o ro,noload "$root" "$probe/root"
test -s "$probe/boot/config.txt"
test -s "$probe/boot/cmdline.txt"
test -s "$probe/root/etc/fstab"
test -s "$probe/root/usr/lib/systemd/systemd"
[[ -n $(find "$probe/boot" -maxdepth 1 -name 'kernel*.img' -size +0c -print -quit) ]]
root_partuuid=$(blkid -s PARTUUID -o value "$root")
grep -Fq "root=PARTUUID=$root_partuuid" "$probe/boot/cmdline.txt"
