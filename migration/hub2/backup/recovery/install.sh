#!/bin/bash
set -euo pipefail
umask 077
package=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
boot=/boot/firmware
kernel=$(uname -r)
marker='# HanzHub one-shot SD backup'
test "$(findmnt -n -o UUID --mountpoint /mnt/hanzhub-backup)" = 20fe1490-9a5e-dd01-00ce-14909a5edd01
test "$(findmnt -n -o FSTYPE --mountpoint "$boot")" = vfat
cmp -s "$boot/kernel_2712.img" "/boot/vmlinuz-$kernel"
test -s /etc/hanzhub-backup/age-identity
if [[ -e "$boot/autoboot.txt" ]] && grep -Eq '^[[:space:]]*tryboot_a_b[[:space:]]*=[[:space:]]*1' "$boot/autoboot.txt"; then
    echo 'Existing tryboot A/B configuration requires review' >&2
    exit 1
fi
if [[ -e "$boot/tryboot.txt" ]] && [[ "$(head -n1 "$boot/tryboot.txt")" != "$marker" ]]; then
    echo 'An independent tryboot configuration already exists' >&2
    exit 1
fi
work=$(mktemp -d /var/tmp/hub2-recovery.XXXXXX)
trap 'rm -r -- "$work"' EXIT
mkdir -p "$work/conf/hooks" "$work/conf/scripts/init-premount"
cp /etc/initramfs-tools/initramfs.conf "$work/conf/"
printf 'fuse\n' > "$work/conf/modules"
install -m 755 "$package/recovery/boot-hook" "$work/conf/scripts/init-premount/hub2-offline-img"
cat > "$work/conf/hooks/hub2-offline-img" <<'HOOK'
#!/bin/sh
set -eu
if [ "${1:-}" = prereqs ]; then exit 0; fi
. /usr/share/initramfs-tools/hook-functions
for tool in bash age age-keygen gocryptfs fusermount3 losetup blockdev blkid lsblk \
    sfdisk fsck.fat e2fsck mount umount mountpoint find df dd sha256sum stat \
    install sync timeout flock mktemp realpath base64 date; do
    copy_exec "$(command -v "$tool")"
done
mkdir -p "$DESTDIR/hub2-recovery"
for file in weekly.sh verify-image.sh; do
    cp "$HUB2_BACKUP_PACKAGE/$file" "$DESTDIR/hub2-recovery/"
done
cp "$HUB2_BACKUP_PACKAGE/recovery/run.sh" "$DESTDIR/hub2-recovery/run.sh"
HOOK
chmod 755 "$work/conf/hooks/hub2-offline-img"
HUB2_BACKUP_PACKAGE="$package" mkinitramfs -d "$work/conf" -o "$work/recovery.img" "$kernel"
lsinitramfs "$work/recovery.img" > "$work/inventory"
for path in scripts/init-premount/hub2-offline-img hub2-recovery/run.sh \
    hub2-recovery/weekly.sh hub2-recovery/verify-image.sh usr/bin/age usr/bin/gocryptfs; do
    grep -Fxq "$path" "$work/inventory"
done
! grep -Eq 'age-identity|restic-password' "$work/inventory"
printf '%s\n' 'root=/dev/ram0 ro noresume panic=60 console=tty1 hub2.offline-img=1' > "$work/cmdline.txt"
printf '%s\n' "$marker" 'include config.txt' '[all]' 'auto_initramfs=0' \
    'kernel=kernel_2712.img' 'initramfs hub2-recovery.img followkernel' \
    'cmdline=hub2-recovery-cmdline.txt' > "$work/tryboot.txt"
install -m 644 "$work/recovery.img" "$boot/hub2-recovery.img.new"
install -m 644 "$work/cmdline.txt" "$boot/hub2-recovery-cmdline.txt.new"
install -m 644 "$work/tryboot.txt" "$boot/tryboot.txt.new"
for path in hub2-recovery.img hub2-recovery-cmdline.txt tryboot.txt; do
    mv -T "$boot/$path.new" "$boot/$path"
done
sync -f "$boot"
echo 'One-shot recovery files staged. Normal config.txt was preserved.'
