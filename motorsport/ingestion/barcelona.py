"""Barcelona analysis adapter: pinned recordings and witnessed lap timing.

The inclusive timing settings are the verified v0.7.1 data contract. Metadata
uncertainty is descriptive; no prediction corpus, features or models are built.
"""
import hashlib
import json
from pathlib import Path

from .acgym_importer import load_acgym_recording

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT/'data/raw/acgym_barcelona_dallara'
MANIFEST = ROOT/'docs/BARCELONA_MANIFEST_V07.json'


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def manifest_entry_path(root, entry):
    root = Path(root).resolve()
    path = (root/entry['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Unsafe Barcelona manifest path')
    return path


def load_barcelona_recording(relative, root=RAW, manifest_path=MANIFEST):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if (manifest.get('track'), manifest.get('car')) != ('ks_barcelona-layout_gp', 'dallara_f317'):
        raise ValueError('Barcelona car/track domain required')
    entries = {entry['path']:entry for entry in manifest['files']}
    if relative not in entries or not relative.endswith('.ld'):
        raise ValueError('Unknown Barcelona recording')
    entry = {**entries[relative], 'driver_label':entries[relative].get('driver_label') or 'unknown'}
    if entry.get('source_type') != 'human':
        raise ValueError('Nonhuman Barcelona source rejected')
    for name in (relative, relative+'x'):
        evidence = entries.get(name)
        if evidence is None:
            raise ValueError('Unpaired Barcelona manifest recording')
        path = manifest_entry_path(root, evidence)
        if not evidence.get('sha256') or file_sha(path) != evidence['sha256']:
            raise ValueError('Barcelona source integrity mismatch: '+name)
    config = {**manifest, 'target_rounding_s':.001, 'optional_feature_channels':True, 'allow_unknown_date':True}
    return load_acgym_recording(manifest_entry_path(root, entry), entry, config, analysis_only=True)
