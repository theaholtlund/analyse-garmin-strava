import base64
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from cloud_sync_state import CloudState
from mowl_sync import Journal


def test_encrypted_state_roundtrip_and_authentication(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    j = Journal(root / 'journal.sqlite3')
    (root / '123').mkdir()
    (root / '123' / 'backup.fit').write_bytes(b'private activity')
    j.reserve('123', '456', root / '123')
    key = base64.b64encode(b'x' * 32).decode()
    state = CloudState(root, 'test/repo', 'unused', key)
    data = state.pack()
    assert b'private activity' not in data
    restored = tmp_path / 'restored'
    CloudState(restored, 'test/repo', 'unused', key).unpack(data)
    assert (restored / '123' / 'backup.fit').read_bytes() == b'private activity'
    assert Journal(restored / 'journal.sqlite3').get('123')[0] == 'uploading'
    corrupted = data[:-1] + bytes([data[-1] ^ 1])
    with pytest.raises(InvalidTag):
        CloudState(tmp_path / 'bad', 'test/repo', 'unused', key).unpack(corrupted)


def test_checkpoint_failure_prevents_reservation_from_returning(tmp_path):
    def fail():
        raise RuntimeError('cloud unavailable')
    journal = Journal(tmp_path / 'journal.sqlite3', checkpoint=fail)
    with pytest.raises(RuntimeError, match='cloud unavailable'):
        journal.reserve('42', '55')
    assert journal.get('42')[0] == 'uploading'
