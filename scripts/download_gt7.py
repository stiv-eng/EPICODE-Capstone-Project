"""Explicit, hash-verified download of the pinned CC-BY-4.0 GT7 bundle.

Attribution: Ricardo Queiroz, GT7 Telemetry: Porsche 962 C '88 at Trial Mountain
https://huggingface.co/datasets/rpqueiroz/gt7-trial-mountain-962c
The author's license covers their contribution; see data/raw/README.md.
Raw files remain local and excluded from Git. This script is never run by the UI.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def download():
    manifest=json.loads((ROOT/'docs/GT7_MANIFEST_V05.json').read_text(encoding='utf-8'))
    target=(ROOT/'data/raw/gt7_trial_mountain_962c').resolve()
    target.mkdir(parents=True,exist_ok=True)
    for entry in manifest['files']:
        path=(target/entry['path']).resolve()
        if not path.is_relative_to(target):
            raise ValueError('Invalid manifest destination.')
        if path.exists():
            with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if digest!=entry['sha256']:
                raise ValueError(f'Existing source differs; preserved without overwrite: {path}')
            continue
        path.parent.mkdir(parents=True,exist_ok=True)
        request=urllib.request.Request(entry['url'],headers={'User-Agent':'Motorsport-Telemetry-Analyzer/0.5'})
        with urllib.request.urlopen(request,timeout=45) as response:
            body=response.read(entry['bytes']+1)
        if len(body)!=entry['bytes'] or hashlib.sha256(body).hexdigest()!=entry['sha256']:
            raise ValueError(f'Download failed integrity check: {entry["path"]}')
        with tempfile.NamedTemporaryFile(dir=path.parent,delete=False,suffix='.download') as stream:
            stream.write(body)
            temporary=Path(stream.name)
        temporary.rename(path)
        print(entry['path'],len(body),flush=True)
    print('GT7 bundle present and verified; no existing source was overwritten.')


if __name__=='__main__':
    download()
