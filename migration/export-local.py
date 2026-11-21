#!/usr/bin/env python3
"""Local HUB export. Does not stop services, restore files or change mounts."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import grp
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile


def sqlite_copy(source, target):
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True,
                                timeout=30)) as src:
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RuntimeError('SQLite integrity check failed')


def user_directories(accounts):
    """Include custom homes and SSH symlink targets without reading key contents."""
    paths = set()
    for account in accounts:
        if account.pw_uid != 0 and not 1000 <= account.pw_uid < 65534:
            continue
        home = Path(account.pw_dir)
        if not home.is_absolute() or home == Path('/') or not home.is_dir():
            continue
        paths.update((home, home.resolve()))
        ssh = home / '.ssh'
        if ssh.is_dir():
            paths.add(ssh.resolve())
            for item in ssh.iterdir():
                if item.is_symlink() and item.exists():
                    paths.add(item.resolve())
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=Path('/mnt/hanzhub-migration'))
    parser.add_argument('--uuid', required=True, help='Expected destination filesystem UUID')
    encryption = parser.add_mutually_exclusive_group()
    encryption.add_argument('--plain', dest='plain', action='store_true', default=True,
                            help='Unencrypted private archive (default)')
    encryption.add_argument('--encrypt', dest='plain', action='store_false',
                            help='Optionally encrypt with a GPG password')
    parser.add_argument('--extra', type=Path, action='append', default=[], help='Additional application/data directory')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run with sudo for protected application files and databases')
    os.umask(0o077)
    mount = args.destination.resolve(strict=True)
    info = json.loads(subprocess.check_output([
        'findmnt', '--json', '--mountpoint', str(mount), '-o', 'UUID,OPTIONS,TARGET']))['filesystems'][0]
    if info['uuid'] != args.uuid or 'rw' not in info['options'].split(','):
        parser.error('Destination UUID mismatch or mount is not writable; nothing changed')
    if not args.plain and not shutil.which('gpg'):
        parser.error('GnuPG required; or explicitly choose --plain for a private unencrypted backup')
    output = mount / ('hanzhub-local-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    output.mkdir(mode=0o700)
    report = {'started': datetime.now(timezone.utc).isoformat(), 'errors': [],
              'notes': ['Live files may change. No cross-service transaction snapshot.',
                        'Application restore has not been tested. Original paths are preserved.',
                        'New installations belong under /opt; restore selectively, never overwrite /etc wholesale.'],
              'sqlite': [], 'dumps': [], 'excluded': [], 'roots': []}

    def run(command, filename, timeout=300):
        path = output / filename
        try:
            with path.open('wb') as stream:
                result = subprocess.run(command, stdout=stream, stderr=subprocess.PIPE, timeout=timeout)
            if result.returncode:
                raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])
            return path
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            report['errors'].append({'operation': filename, 'error': str(exc)})
            return None

    for filename, command in {
        'disks.txt': ['lsblk', '-o', 'NAME,PATH,MODEL,SERIAL,WWN,SIZE,FSTYPE,UUID,RO,MOUNTPOINTS'],
        'mounts.txt': ['findmnt'], 'os.txt': ['uname', '-a'],
        'packages.txt': ['dpkg-query', '-W'],
        'services.txt': ['systemctl', 'list-units', '--all', '--no-pager'],
        'units.txt': ['systemctl', 'list-unit-files', '--no-pager'],
        'timers.txt': ['systemctl', 'list-timers', '--all', '--no-pager'],
        'ports.txt': ['ss', '-lntup'], 'gpio.txt': ['gpioinfo'],
        'usb.txt': ['lsusb'],
    }.items():
        run(command, filename)

    # Never archive raw database-server storage. Use native dumps instead.
    excluded = [mount, Path('/var/lib/docker'), Path('/var/lib/containers'),
                Path('/var/lib/postgresql'), Path('/var/lib/mysql'),
                Path('/var/lib/influxdb'), Path('/var/lib/influxdb2'),
                Path('/var/lib/redis'), Path('/var/lib/mongodb')]
    roots = [Path(p) for p in ('/opt', '/etc', '/home', '/root', '/usr/local',
                               '/var/lib', '/var/spool/cron', '/boot/firmware')]
    accounts = pwd.getpwall()
    roots += sorted(user_directories(accounts))
    # Password hashes remain in archived /etc/shadow, never in console output.
    (output / 'accounts.json').write_text(json.dumps({
        'users': [dict(name=a.pw_name, uid=a.pw_uid, gid=a.pw_gid,
                       home=a.pw_dir, shell=a.pw_shell) for a in accounts],
        'groups': [dict(name=g.gr_name, gid=g.gr_gid, members=g.gr_mem)
                   for g in grp.getgrall()],
        'restore_note': 'Recreate selected users with original UID/GID; do not overwrite new OS account files wholesale.',
        'ssh': 'User .ssh directories and /etc/ssh included with modes and numeric ownership.',
    }, indent=2))
    roots += args.extra
    containers = []
    if shutil.which('docker'):
        ids = run(['docker', 'ps', '-aq'], 'container-ids.txt')
        if ids and ids.read_text().strip():
            inspected = run(['docker', 'inspect', *ids.read_text().split()], 'docker-inspect.json')
            if inspected:
                containers = json.loads(inspected.read_text())
        images = sorted({c['Image'] for c in containers})
        if images:
            run(['docker', 'image', 'save', '-o', str(output / 'docker-images.tar'), *images],
                'docker-save.log', timeout=None)
        for container in containers:
            name = container['Name'].lstrip('/')
            image = container['Config']['Image'].lower()
            mounts = [Path(m['Source']) for m in container.get('Mounts', [])
                      if m.get('Source') and m.get('Type') in ('bind', 'volume')]
            engine = next((e for e in ('postgres', 'mariadb', 'mysql', 'influxdb', 'redis', 'mongo')
                           if e in image), None)
            if engine:
                excluded.extend(mounts)
                command = None
                if engine == 'postgres':
                    command = ['sh', '-c', 'exec pg_dumpall -U "${POSTGRES_USER:-postgres}"']
                elif engine in ('mysql', 'mariadb'):
                    command = ['sh', '-c', 'export MYSQL_PWD="${MYSQL_ROOT_PASSWORD:-${MARIADB_ROOT_PASSWORD:-}}"; '
                               'exec "$(command -v mariadb-dump || command -v mysqldump)" '
                               '-uroot --all-databases --single-transaction --routines --events --triggers']
                if command:
                    dump = run(['docker', 'exec', name, *command], name + '.sql', timeout=None)
                    if dump:
                        report['dumps'].append(dump.name)
                else:
                    report['errors'].append({'operation': name, 'error': engine +
                        ': native backup required; raw live storage deliberately excluded'})
            else:
                roots.extend(mounts)
                report['notes'].append(name + ': file copy of mounts; application consistency unverified')
    for engine, directory, command in (
        ('postgresql', '/var/lib/postgresql', ['runuser', '-u', 'postgres', '--', 'pg_dumpall']),
        ('mysql', '/var/lib/mysql', ['mysqldump', '--all-databases', '--single-transaction',
                                  '--routines', '--events', '--triggers']),
    ):
        if Path(directory).exists():
            dump = run(command, 'host-' + engine + '.sql', timeout=None)
            if dump:
                report['dumps'].append(dump.name)
    for engine in ('influxdb', 'influxdb2', 'redis', 'mongodb'):
        if Path('/var/lib', engine).exists():
            report['errors'].append({'operation': engine, 'error': 'Host native backup required'})

    def under(path, parent):
        return path == parent or parent in path.parents

    # Deduplicate directory roots. Do not traverse other filesystems accidentally.
    selected = []
    for root in sorted(set(p.absolute() for p in roots if p.exists()), key=lambda p: len(p.parts)):
        if not any(under(root, parent) for parent in selected):
            selected.append(root)
    report['roots'] = [str(p) for p in selected]
    report['excluded'] = [str(p) for p in excluded]
    print('Export:', output, flush=True)
    archive_path = output / ('files.tar.gz' if args.plain else 'files.tar.gz.gpg')
    cipher = None
    with tempfile.TemporaryDirectory(prefix='.sqlite-', dir=output) as scratch:
        raw = archive_path.open('wb')
        try:
            if not args.plain:
                print('GPG will ask for an archive password; keep it for import.', flush=True)
                cipher = subprocess.Popen(['gpg', '--symmetric', '--cipher-algo', 'AES256',
                                           '--output', '-'], stdin=subprocess.PIPE, stdout=raw)
            with tarfile.open(fileobj=cipher.stdin if cipher else raw, mode='w|gz',
                              dereference=False) as archive:
                def add(path, device):
                    if any(under(path, p) for p in excluded
                           if not (p == Path('/var/lib/docker') and
                                   under(root, p) and root != p)):
                        return
                    try:
                        st = path.lstat()
                        if st.st_dev != device:
                            report['notes'].append('Skipped nested mount: ' + str(path))
                            return
                        if path.is_symlink():
                            archive.add(path, arcname=str(path).lstrip('/'), recursive=False)
                        elif path.is_dir():
                            archive.add(path, arcname=str(path).lstrip('/'), recursive=False)
                            for child in sorted(path.iterdir()):
                                add(child, device)
                        elif path.is_file():
                            if path.name.endswith(('-wal', '-shm', '-journal')):
                                report['notes'].append('SQLite sidecar excluded: ' + str(path))
                                return
                            with path.open('rb') as stream:
                                sqlite = stream.read(16) == b'SQLite format 3\x00'
                            if sqlite:
                                snapshot = Path(scratch) / 'snapshot.sqlite'
                                sqlite_copy(path, snapshot)
                                meta = archive.gettarinfo(str(path), arcname=str(path).lstrip('/'))
                                meta.size = snapshot.stat().st_size
                                with snapshot.open('rb') as stream:
                                    archive.addfile(meta, stream)
                                snapshot.unlink()
                                report['sqlite'].append(str(path))
                            else:
                                archive.add(path, arcname=str(path).lstrip('/'), recursive=False)
                    except (OSError, sqlite3.Error, RuntimeError) as exc:
                        report['errors'].append({'operation': str(path), 'error': str(exc)})
                for root in selected:
                    add(root, root.lstat().st_dev)
                # Native dumps and private inventory are included in the encrypted payload.
                for path in sorted(output.iterdir()):
                    if path.is_file() and path != archive_path:
                        archive.add(path, arcname='export-metadata/' + path.name)
                report['finished'] = datetime.now(timezone.utc).isoformat()
                data = json.dumps(report, indent=2).encode()
                meta = tarfile.TarInfo('export-metadata/report.json')
                meta.mode, meta.size = 0o600, len(data)
                archive.addfile(meta, io.BytesIO(data))
        finally:
            if cipher:
                cipher.stdin.close()
                code = cipher.wait()
            else:
                code = 0
            raw.close()
        if code:
            raise RuntimeError('GPG failed; archive is incomplete. Private intermediates retained for diagnosis.')
    # Remove only intermediates generated by this run after the payload is closed.
    for path in output.iterdir():
        if path != archive_path and path.is_file():
            path.unlink()
    with archive_path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    (output / 'SHA256SUMS').write_text(digest + '  ' + archive_path.name + '\n')
    (output / 'STATUS.txt').write_text(
        'Export completed; application restore untested.\n'
        f"Issues requiring review: {len(report['errors'])}. See export-metadata/report.json inside archive.\n")
    importer = Path(__file__).with_name('import-local.py')
    if importer.is_file():
        shutil.copy2(importer, output / 'import-local.py')
    print(f"Saved {archive_path}; issues: {len(report['errors'])}; restore untested.")
    return 2 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
