"""Explicit, bounded acquisition of pinned human Barcelona MoTeC exports.

No pickle, policy weights or repository checkout is downloaded. The manifest is
created before payload acquisition; .part files and a durable byte ledger support
resuming. Normal application startup never imports or calls this command.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import time
from urllib.parse import quote

import requests

ROOT=Path(__file__).resolve().parents[1]
REPO='dasgringuen/assettoCorsaGym'
REVISION='ad1df12c49cce10f159ba31967744750bb9edd8b'
CATALOGUE_REVISION='9e79864e4c5cf9971dc9cc260d20113b54198d9d'
PREFIX='data_sets/ks_barcelona-layout_gp/dallara_f317'
CATALOGUE_URL=f'https://raw.githubusercontent.com/dasGringuen/assetto_corsa_gym/{CATALOGUE_REVISION}/data/paths.yml'
MANIFEST=ROOT/'docs/BARCELONA_MANIFEST_V07.json'
RAW=ROOT/'data/raw/acgym_barcelona_dallara'
BUDGET=750_000_000


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    for attempt in range(6):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt==5:raise
            time.sleep(.03*2**attempt)  # Windows indexer/antivirus may briefly hold JSON files.


def human_recordings(text):
    """Read only the authors' bounded inline-record catalogue subset, no YAML eval."""
    track=re.search(r'^ks_barcelona-layout_gp:\s*\n(.*?)(?=^\S|\Z)',text,re.M|re.S)
    car=re.search(r'^  dallara_f317:\s*\n(.*?)(?=^  \w|\Z)',track.group(1) if track else '',re.M|re.S)
    if not car:raise ValueError('Pinned human catalogue lacks selected domain')
    result=[]
    for row in re.findall(r'^\s+-\s+\{([^}]+)\}',car.group(1),re.M):
        fields=dict(re.findall(r'(\w+):\s*([\w-]+)',row))
        identity=fields.get('id','')
        if fields.get('type')=='human' and fields.get('data_type')=='motec' and not re.search(r'SAC|MPC|ACAI|POLICY',identity,re.I):
            if not re.fullmatch(r'\d{8}_[A-Za-z0-9_]+',identity):raise ValueError('Unsupported catalogue identity')
            result.append(identity)
    if not result:raise ValueError('No declared human recordings')
    return result


def tree(session,path):
    url=f'https://huggingface.co/api/datasets/{REPO}/tree/{REVISION}/{quote(path,safe="/")}?limit=1000'
    result=[]
    for _ in range(10):
        response=session.get(url,timeout=45);response.raise_for_status();result.extend(response.json())
        url=response.links.get('next',{}).get('url')
        if not url:return result
        if not url.startswith(f'https://huggingface.co/api/datasets/{REPO}/tree/'):raise ValueError('Unexpected metadata pagination host')
    raise ValueError('Metadata listing exceeds bounded page budget')


def inspect(session=None,manifest_path=MANIFEST):
    session=session or requests.Session()
    response=session.get(CATALOGUE_URL,timeout=45);response.raise_for_status()
    catalogue=response.text
    folders=human_recordings(catalogue)
    response=session.get(f'https://huggingface.co/datasets/{REPO}/raw/{REVISION}/README.md',timeout=45)
    response.raise_for_status()
    if 'cc-by-4.0' not in response.text.lower():raise ValueError('Dataset license needs review')
    present={e['path'].split('/')[-1] for e in tree(session,PREFIX) if e['type']=='directory'}
    files=[]
    for folder in folders:
        if folder not in present:raise ValueError('Catalogue recording absent: '+folder)
        for item in tree(session,PREFIX+'/'+folder+'/laps'):
            path=item['path']
            if item['type']!='file' or not (path.endswith(('.ld','.ldx')) or path.endswith('/laps_info.csv')):continue
            relative=path.removeprefix(PREFIX+'/')
            if len(Path(relative).parts)!=3 or Path(relative).parts[1]!='laps':raise ValueError('Unexpected source organization')
            entry=dict(path=relative,source_path=path,bytes=item['size'],
                url=f'https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/'+quote(path,safe='/'),
                recording_label=folder,driver_label=folder.split('_')[1],source_type='human')
            if item.get('lfs'):entry['sha256']=item['lfs']['oid']
            else:entry['git_blob_oid']=item['oid']
            files.append(entry)
    paths={e['path'] for e in files}
    for entry in files:
        if entry['path'].endswith('.ld') and entry['path']+'x' not in paths:raise ValueError('Unpaired LD recording')
    total=sum(e['bytes'] for e in files)
    if total>BUDGET:raise ValueError(f'Inspected payload {total} exceeds {BUDGET}-byte cap; no acquisition authorized')
    manifest=dict(repo=REPO,revision=REVISION,license='CC-BY-4.0',
        attribution='Remonda et al., A Simulation Benchmark for Autonomous Racing with Large-Scale Human Data, NeurIPS 2024; AssettoCorsaGym / dasGringuen',
        catalogue_url=CATALOGUE_URL,catalogue_sha256=hashlib.sha256(catalogue.encode()).hexdigest(),
        car='dallara_f317',track='ks_barcelona-layout_gp',header_venue='ks_barcelona',
        download_budget_bytes=BUDGET,storage_reserve_bytes=1_500_000_000,
        inspected_payload_bytes=total,human_recordings=folders,
        excluded_types=['pickle','SAC','MPC','policy weights','other car/track','evaluation buffers'],files=files)
    # An existing pinned manifest must not lose locally verified checksums.
    manifest_path=Path(manifest_path)
    if manifest_path.exists():
        previous=json.loads(manifest_path.read_text(encoding='utf-8'))
        if previous['revision']!=REVISION:raise ValueError('Existing manifest revision differs')
        old={e['path']:e for e in previous['files']}
        for entry in files:
            if entry['path'] in old and old[entry['path']].get('sha256'):
                entry.setdefault('sha256',old[entry['path']]['sha256'])
    write_json(manifest_path,manifest)
    return manifest


def destination(root,relative):
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root) or path==root:raise ValueError('Unsafe destination')
    return path


def verify(path,entry):
    if path.stat().st_size!=entry['bytes']:raise ValueError('Source size mismatch: '+entry['path'])
    sha=hashlib.sha256();git=hashlib.sha1(f'blob {entry["bytes"]}\0'.encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):sha.update(chunk);git.update(chunk)
    digest=sha.hexdigest()
    if entry.get('sha256') and digest!=entry['sha256']:raise ValueError('SHA-256 mismatch: '+entry['path'])
    if entry.get('git_blob_oid') and git.hexdigest()!=entry['git_blob_oid']:raise ValueError('Pinned Git object mismatch: '+entry['path'])
    return digest


def download(*,sample=False,manifest_path=MANIFEST,root=RAW,ledger_path=None,session=None):
    manifest_path=Path(manifest_path);root=Path(root)
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['revision']!=REVISION or manifest.get('track')!='ks_barcelona-layout_gp' or manifest.get('car')!='dallara_f317':
        raise ValueError('Unexpected acquisition domain/revision')
    ledger_path=Path(ledger_path or ROOT/'artifacts/v07/acquisition_ledger.json')
    ledger=json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else dict(received_bytes=0,transfers=[])
    root.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(root).free<manifest['storage_reserve_bytes']:raise ValueError('Insufficient disk space: preserve 1.5 GB reserve')
    entries=manifest['files']
    if sample:entries=[e for e in entries if e['recording_label']==manifest['human_recordings'][0]]
    session=session or requests.Session()
    for entry in entries:
        if entry.get('source_type')!='human' or not entry['source_path'].startswith(PREFIX+'/') or not entry['path'].endswith(('.ld','.ldx','/laps_info.csv')):
            raise ValueError('Source outside human MoTeC allowlist')
        path=destination(root,entry['path'])
        if path.exists():entry['sha256']=verify(path,entry);continue
        partial=path.with_name(path.name+'.part');path.parent.mkdir(parents=True,exist_ok=True)
        offset=partial.stat().st_size if partial.exists() else 0
        if offset>entry['bytes']:raise ValueError('Oversized partial file preserved for review')
        if ledger['received_bytes']+entry['bytes']-offset>manifest['download_budget_bytes']:
            raise ValueError('Transfer budget exhausted; partial files retained')
        if offset<entry['bytes']:
            headers={'Range':f'bytes={offset}-'} if offset else {}
            with session.get(entry['url'],headers=headers,stream=True,timeout=(30,90)) as response:
                response.raise_for_status()
                if offset and (response.status_code!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {offset}-')):
                    raise ValueError('Server refused a verified range resume; partial preserved')
                with partial.open('ab' if offset else 'wb') as stream:
                    try:
                        for chunk in response.iter_content(256*1024):
                            if not chunk:continue
                            ledger['received_bytes']+=len(chunk)
                            if ledger['received_bytes']>manifest['download_budget_bytes'] or stream.tell()+len(chunk)>entry['bytes']:
                                raise ValueError('Transfer/source size cap exceeded')
                            stream.write(chunk);stream.flush();write_json(ledger_path,ledger)
                    finally:
                        ledger['transfers'].append(dict(path=entry['path'],partial_bytes=partial.stat().st_size))
                        write_json(ledger_path,ledger)
        entry['sha256']=verify(partial,entry);partial.replace(path)
        write_json(manifest_path,manifest)
        print(entry['path'],entry['bytes'],flush=True)
    write_json(manifest_path,manifest)
    print('Verified selected files; cumulative received bytes:',ledger['received_bytes'],flush=True)
    return ledger


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inspect','sample','all'])
    args=parser.parse_args()
    if args.action=='inspect':
        result=inspect();print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
    else:download(sample=args.action=='sample')
