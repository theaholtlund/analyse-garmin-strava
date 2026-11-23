"""Encrypted and versioned GitHub state for the MOWL synchronization job."""
import base64
import binascii
import io
import os
from pathlib import Path
import tarfile

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b'MOWLSTATE1'
BRANCH = 'mowl-sync-state'
STATE_PATH = 'encrypted-state.bin'
MAX_BYTES = 30 * 1024 * 1024


class CloudState:
    def __init__(self, root, repo, token, key):
        self.root = Path(root).resolve()
        self.repo = repo
        self.token = token
        try:
            self.key = base64.b64decode(key, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError('Invalid cloud state encryption key') from exc
        if len(self.key) != 32:
            raise ValueError('Cloud state encryption key must be 32 bytes')
        self.sha = None

    def request(self, method, suffix, **kwargs):
        response = requests.request(method, f'https://api.github.com/repos/{self.repo}/{suffix}',
            headers={'Authorization': f'Bearer {self.token}', 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28'}, timeout=45, **kwargs)
        response.raise_for_status()
        return response.json()

    def pack(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as archive:
            journal = self.root / 'journal.sqlite3'
            if not journal.is_file():
                raise RuntimeError('Journal is missing; refusing to checkpoint')
            archive.add(journal, arcname=journal.name)
            for child in self.root.iterdir():
                if child.is_dir() and (child.name.isdigit() or child.name == 'garmin-tokens') and not child.is_symlink():
                    archive.add(child, arcname=child.name, recursive=True,
                                filter=lambda info: info if info.isfile() or info.isdir() else None)
        nonce = os.urandom(12)
        encrypted = MAGIC + nonce + AESGCM(self.key).encrypt(nonce, buf.getvalue(), MAGIC)
        if len(encrypted) > MAX_BYTES:
            raise RuntimeError('Encrypted state exceeds the configured size limit')
        return encrypted

    def unpack(self, data):
        if not data.startswith(MAGIC) or len(data) > MAX_BYTES:
            raise ValueError('Invalid encrypted state')
        nonce = data[len(MAGIC):len(MAGIC)+12]
        raw = AESGCM(self.key).decrypt(nonce, data[len(MAGIC)+12:], MAGIC)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            for item in archive.getmembers():
                parts = Path(item.name).parts
                if not parts or (parts[0] not in ('journal.sqlite3', 'garmin-tokens') and not parts[0].isdigit()) or not (item.isfile() or item.isdir()):
                    raise ValueError('Invalid state archive entry')
                if '..' in parts or item.name.startswith('/'):
                    raise ValueError('Unsafe state archive entry')
            archive.extractall(self.root, filter='data')
        if not (self.root / 'journal.sqlite3').is_file():
            raise ValueError('Restored state has no journal')

    def restore(self):
        payload = self.request('GET', f'contents/{STATE_PATH}', params={'ref': BRANCH})
        if not payload.get('sha'):
            raise RuntimeError('Cloud state missing or invalid; refusing to proceed')
        sha = payload['sha']
        if payload.get('encoding') != 'base64':
            payload = self.request('GET', f'git/blobs/{sha}')
        if payload.get('encoding') != 'base64':
            raise RuntimeError('Cloud state could not be read')
        self.unpack(base64.b64decode(payload['content']))
        self.sha = sha

    def checkpoint(self):
        if not self.sha:
            raise RuntimeError('Cloud state was not restored; refusing to checkpoint')
        payload = self.request('PUT', f'contents/{STATE_PATH}', json={
            'message': 'Update encrypted MOWL sync state', 'branch': BRANCH, 'sha': self.sha,
            'content': base64.b64encode(self.pack()).decode('ascii')})
        self.sha = payload['content']['sha']
