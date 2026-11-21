#!/usr/bin/env python3
"""Import a plain export-local.py bundle; never start services or import SQL automatically."""
import argparse
from datetime import datetime, timezone
import grp
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import shutil
import subprocess
import tarfile


def unpack(archive, stage):
    # Defer symlinks so archived links cannot redirect extraction outside staging.
    with tarfile.open(archive, 'r:gz') as tar:
        links = []
        for member in tar:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts:
                raise ValueError('Unsafe archive path: ' + member.name)
            if member.issym():
                links.append(member)
            else:
                tar.extract(member, stage, filter='data')
                if os.geteuid() == 0 and not member.isdev():
                    os.chown(stage / member.name, member.uid, member.gid, follow_symlinks=False)
        for member in links:
            target = stage / member.name
            if any(p.is_symlink() for p in target.parents if p != stage.parent):
                raise ValueError('Symlink parent in archive: ' + member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                raise ValueError('Duplicate archive link: ' + member.name)
            target.symlink_to(member.linkname)


def merge(source, destination, rollback, uid=None, gid=None):
    """Copy a tree without following destination links, saving overwritten files."""
    if not source.exists() and not source.is_symlink():
        return
    for parent in destination.parents:
        if parent.is_symlink():
            raise ValueError('Destination contains a symlink: ' + str(parent))
    if source.is_dir() and not source.is_symlink():
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            raise ValueError('Directory collision: ' + str(destination))
        existed = destination.exists()
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        for item in source.iterdir():
            merge(item, destination / item.name, rollback, uid, gid)
        if not existed or destination.name == '.ssh':
            shutil.copystat(source, destination, follow_symlinks=False)
        if uid is not None:
            os.chown(destination, uid, gid)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            old = rollback / str(destination).lstrip('/')
            old.parent.mkdir(parents=True, exist_ok=True)
            if old.exists() or old.is_symlink():
                raise ValueError('Duplicate rollback path: ' + str(old))
            shutil.move(str(destination), old)
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, destination)
        st = source.lstat()
        os.chown(destination, st.st_uid if uid is None else uid,
                 st.st_gid if gid is None else gid, follow_symlinks=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path, help='Directory containing files.tar.gz and SHA256SUMS')
    parser.add_argument('--apply', action='store_true', help='Install selected files and recreate users on new OS')
    parser.add_argument('--user', action='append', help='Only these users; default: all backed-up human users')
    parser.add_argument('--root-ssh', action='store_true', help='Also restore root .ssh')
    parser.add_argument('--docker-images', action='store_true', help='Load saved Docker images')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run with sudo')
    os.umask(0o077)
    bundle = args.bundle.resolve(strict=True)
    archive = bundle / 'files.tar.gz'
    lines = (bundle / 'SHA256SUMS').read_text().splitlines()
    expected = [line.split()[0] for line in lines
                if len(line.split()) == 2 and line.split()[1] == 'files.tar.gz']
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if expected != [actual]:
        parser.error('Archive checksum mismatch')
    work = Path('/opt/hanzhub') / ('import-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work.mkdir(parents=True, mode=0o700)
    stage = work / 'staging'
    stage.mkdir(mode=0o700)
    unpack(archive, stage)
    print('Archive verified and unpacked:', stage, flush=True)
    if not args.apply:
        print('No system files changed. Add --apply on the NEW OS to install files.')
        return
    metadata = json.loads((stage / 'export-metadata/accounts.json').read_text())
    users = [u for u in metadata['users'] if 1000 <= u['uid'] < 65534
             and (args.user is None or u['name'] in args.user)]
    if args.user and set(args.user) != {u['name'] for u in users}:
        parser.error('Requested user missing from backed-up human accounts')
    # Check every identity before creating users or copying application files.
    for user in users:
        if not Path(user['home']).is_absolute() or user['home'] in ('/', '/root'):
            parser.error('Invalid user home')
        try:
            current = pwd.getpwnam(user['name'])
            if (current.pw_uid, current.pw_gid, current.pw_dir) != (user['uid'], user['gid'], user['home']):
                parser.error('UID/GID/home conflict for ' + user['name'])
        except KeyError:
            try:
                pwd.getpwuid(user['uid'])
            except KeyError:
                pass
            else:
                parser.error('UID already occupied for ' + user['name'])
    rollback = work / 'previous-files'
    rollback.mkdir(mode=0o700)
    for user in users:
        try:
            group = grp.getgrgid(user['gid'])
        except KeyError:
            original = next(g for g in metadata['groups'] if g['gid'] == user['gid'])
            subprocess.run(['groupadd', '-g', str(user['gid']), original['name']], check=True)
        try:
            pwd.getpwnam(user['name'])
        except KeyError:
            subprocess.run(['useradd', '-M', '-u', str(user['uid']), '-g', str(user['gid']),
                            '-d', user['home'], '-s', user['shell'], user['name']], check=True)
        merge(stage / user['home'].lstrip('/'), Path(user['home']), rollback, user['uid'], user['gid'])
        # Restore membership only in groups already present on this OS.
        memberships = []
        for group in metadata['groups']:
            if user['name'] in group['members']:
                try:
                    grp.getgrnam(group['name'])
                    memberships.append(group['name'])
                except KeyError:
                    pass
        if memberships:
            subprocess.run(['usermod', '-aG', ','.join(memberships), user['name']], check=True)
    for relative in ('opt', 'usr/local', 'etc/hanzhub', 'var/lib/hanzhub'):
        merge(stage / relative, Path('/') / relative, rollback)
    if args.root_ssh:
        merge(stage / 'root/.ssh', Path('/root/.ssh'), rollback, 0, 0)
    if args.docker_images:
        image = stage / 'export-metadata/docker-images.tar'
        if image.exists():
            subprocess.run(['docker', 'load', '-i', str(image)], check=True)
    (work / 'NEXT-STEPS.txt').write_text(
        'Files installed; services have NOT been started.\n'
        'Review staging/etc/systemd, staging/etc/ssh and other config before installing.\n'
        'Account passwords and server host keys were not changed; originals remain in staging/etc.\n'
        'Review remaining staging/var/lib data, Docker mounts and SQL dumps in export-metadata.\n'
        'Install required packages, rebuild incompatible venvs, import DB dumps and deploy service units.\n'
        'User/group creation is not undone by restoring previous-files.\n')
    print('Files imported. Previous versions:', rollback)
    print('Remaining configuration and database steps:', work / 'NEXT-STEPS.txt')


if __name__ == '__main__':
    main()
