"""Only artifacts signed by this local store are deserialized. No upload API.

The store/key are trusted local application state, like the Python source. Do not
replace either with downloaded files. SHA-256 and HMAC are verified before joblib.
"""
import hashlib
import hmac
import io
import json
from pathlib import Path
import secrets
import re

import joblib


class LocalArtifactStore:
    def __init__(self,root):
        self.root = Path(root).resolve()

    def _path(self,name):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',name):
            raise ValueError('Invalid local artifact name')
        return self.root/(name+'.joblib')

    def save(self,bundle,name):
        from .training import TrainingBundle
        if not isinstance(bundle,TrainingBundle):
            raise ValueError('Only locally trained telemetry bundles can be saved')
        self.root.mkdir(parents=True,exist_ok=True)
        key_path = self.root/'.local-signing-key'
        if not key_path.exists():
            with key_path.open('xb') as stream:
                stream.write(secrets.token_bytes(32))
        stream = io.BytesIO()
        joblib.dump(bundle,stream,compress=3)
        body = stream.getvalue()
        path = self._path(name)
        path.write_bytes(body)
        metadata = {'sha256':hashlib.sha256(body).hexdigest(),
            'signature':hmac.new(key_path.read_bytes(),body,hashlib.sha256).hexdigest(),
            'corpus_id':bundle.corpus_id,'producer':'Motorsport Telemetry Analyzer 0.6 local training'}
        path.with_suffix('.json').write_text(json.dumps(metadata,indent=2))
        return path

    def load(self,name):
        path = self._path(name)
        key_path = self.root/'.local-signing-key'
        if not key_path.exists() or not path.with_suffix('.json').exists():
            raise ValueError('Unknown artifact: local provenance is absent')
        body = path.read_bytes()
        metadata = json.loads(path.with_suffix('.json').read_text())
        digest = hashlib.sha256(body).hexdigest()
        signature = hmac.new(key_path.read_bytes(),body,hashlib.sha256).hexdigest()
        if digest!=metadata.get('sha256') or not hmac.compare_digest(signature,metadata.get('signature','')):
            raise ValueError('Untrusted or modified model artifact')
        return joblib.load(io.BytesIO(body))
