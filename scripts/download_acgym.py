"""Explicit bounded acquisition of pinned human MoTeC exports; no pickle/code.

Manifest sizes must be obtained before acquisition. Existing verified files are
reused. A persistent byte ledger also counts failed transfers, not just files.
"""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'docs/ACGYM_MANIFEST_V06.json'


def download():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    root = ROOT/'data/raw/acgym_monza_dallara'
    ledger_path = ROOT/'artifacts/acgym_download_ledger.json'
    ledger_path.parent.mkdir(exist_ok=True)
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
        'received_bytes': sum(e['bytes'] for e in manifest['files'] if (root/e['path']).exists()), 'transfers': []}
    for entry in manifest['files']:
        path = (root/entry['path']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Unsafe destination')
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != entry.get('sha256'):
                raise ValueError(f'Existing file preserved; hash mismatch: {path}')
            continue
        if ledger['received_bytes']+entry['bytes'] > manifest['download_budget_bytes']:
            raise ValueError('Download budget exhausted')
        body = bytearray()
        try:
            with urllib.request.urlopen(entry['url'], timeout=60) as response:
                while True:
                    chunk = response.read(min(1024*1024, entry['bytes']+1-len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body)>entry['bytes']:
                        raise ValueError('Source exceeded inspected size')
            digest = hashlib.sha256(body).hexdigest()
            if len(body)!=entry['bytes']:
                raise ValueError('Truncated source')
            if entry.get('sha256') and digest!=entry['sha256']:
                raise ValueError('SHA-256 mismatch')
            if entry.get('git_blob_oid'):
                git_hash = hashlib.sha1(f'blob {len(body)}\0'.encode()+body).hexdigest()
                if git_hash!=entry['git_blob_oid']:
                    raise ValueError('Pinned Git blob mismatch')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            entry['sha256'] = digest
            MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
            print(entry['path'],len(body),flush=True)
        finally:
            ledger['received_bytes'] += len(body)
            ledger['transfers'].append({'path':entry['path'],'received_bytes':len(body)})
            ledger_path.write_text(json.dumps(ledger,indent=2))
    print('All bounded files verified; total received bytes:',ledger['received_bytes'])


if __name__=='__main__':
    download()
