"""Small offline check: archive extraction, overwrite backup and traversal rejection."""
import importlib.util
import io
import os
from pathlib import Path
import tarfile
import tempfile

spec = importlib.util.spec_from_file_location('import_local', Path(__file__).with_name('import-local.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    archive = base / 'files.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        member = tarfile.TarInfo('home/fixture/.ssh/id_ed25519')
        member.mode, member.size = 0o600, 7
        tar.addfile(member, io.BytesIO(b'fixture'))
        link = tarfile.TarInfo('opt/app/current')
        link.type, link.linkname = tarfile.SYMTYPE, '/opt/app/release'
        tar.addfile(link)
    stage = base / 'stage'
    stage.mkdir()
    module.unpack(archive, stage)
    assert (stage / 'home/fixture/.ssh/id_ed25519').read_bytes() == b'fixture'
    assert os.readlink(stage / 'opt/app/current') == '/opt/app/release'
    destination = base / 'target'
    destination.mkdir()
    (destination / 'id_ed25519').write_text('previous')
    rollback = base / 'previous'
    module.merge(stage / 'home/fixture/.ssh', destination, rollback)
    assert (destination / 'id_ed25519').read_bytes() == b'fixture'
    assert (destination / 'id_ed25519').stat().st_mode & 0o777 == 0o600
    assert (rollback / str(destination / 'id_ed25519').lstrip('/')).read_text() == 'previous'
    with tarfile.open(archive, 'w:gz') as tar:
        member = tarfile.TarInfo('../escape')
        tar.addfile(member)
    try:
        module.unpack(archive, stage)
    except ValueError:
        pass
    else:
        raise AssertionError('Traversal accepted')
print('Import: extraction, SSH permissions, previous-file backup and traversal rejection OK')
