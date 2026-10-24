"""Shared offline corpus selection and persistent, explicitly trained bundles."""
from pathlib import Path
import os
import pandas as pd

import streamlit as st

from motorsport.ml.dataset import from_sessions,independent_subset,eligibility
from motorsport.ml.features import snapshots
from motorsport.ml.baselines import reference_history
from motorsport.ml.training import chronological_split
from motorsport_ui import telemetry

ROOT=Path(__file__).resolve().parents[1]


def corpus_catalog():
    if not archive_mode():return {'barcelona':'Barcelona GP / Dallara F317 · human telemetry v0.7.1'}
    catalog={}
    if (ROOT/'data/raw/acgym_monza_dallara').exists():
        catalog['acgym']='ACGym · human Monza / Dallara · verified independent subset'
    for key,label in telemetry.source_catalog().items():
        catalog[key]=label
    return catalog


def signature(key):
    if key=='barcelona':
        paths=sorted((ROOT/'data/raw/acgym_barcelona_dallara').rglob('*'))+[ROOT/'docs/BARCELONA_MANIFEST_V07.json',ROOT/'docs/BARCELONA_PROTOCOL_V071.json']
        return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths if p.is_file())
    if key=='acgym':
        paths=sorted((ROOT/'data/raw/acgym_monza_dallara').rglob('*'))+[ROOT/'docs/ACGYM_MANIFEST_V06.json']
        return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths if p.is_file())
    return telemetry.source_signature(key)


@st.cache_data(show_spinner=False,max_entries=3)
def load_corpus(key,source_signature):
    if key=='barcelona':return load_barcelona(source_signature)[0]
    if key=='acgym':
        from motorsport.ingestion.acgym_importer import load_acgym_sessions
        sessions,rejected=load_acgym_sessions(ROOT/'data/raw/acgym_monza_dallara',ROOT/'docs/ACGYM_MANIFEST_V06.json')
        corpus=from_sessions(sessions,'ACGym human Monza / Dallara F317')
        corpus.exclusions.extend(rejected)
        return independent_subset(corpus)
    return from_sessions([telemetry.get_source(key)],telemetry.source_catalog().get(key,key))


def archive_mode():
    return bool(st.session_state.get('ml_archive_mode',False)) or os.environ.get('MOTORSPORT_ML_ARCHIVE')=='1'


def barcelona_active():
    return not archive_mode()


@st.cache_data(show_spinner=False,max_entries=2)
def load_barcelona(source_signature):
    from motorsport.ml.barcelona_recovery import load_corpus as load
    return load(ROOT/'data/raw/acgym_barcelona_dallara',ROOT/'docs/BARCELONA_MANIFEST_V07.json')


def select_corpus(page):
    if archive_mode():st.info('Archivio storico v0.6 · corpus separati dalla dimostrazione Barcelona.')
    catalog=corpus_catalog()
    if not catalog:
        st.info('Nessun dataset locale. Aggiungi file nel Data Explorer; nessun download automatico.')
        st.stop()
    keys=list(catalog)
    active=st.session_state.get('ml_active_dataset',keys[0])
    with st.sidebar:
        key=st.selectbox('Dataset ML',keys,index=keys.index(active) if active in keys else 0,
                         format_func=catalog.get,key=f'{page}_dataset')
    st.session_state['ml_active_dataset']=key
    if key=='barcelona':
        st.caption('Dominio ML attivo: Barcelona GP / Dallara F317 · nessun dato Monza o GT7 nel corpus.')
        if not (ROOT/'docs/BARCELONA_MANIFEST_V07.json').exists() or not any((ROOT/'data/raw/acgym_barcelona_dallara').rglob('*.ld')):
            st.info('Dataset Barcelona non installato. Acquisizione separata dall’avvio; nessun download automatico.')
            st.code('python -m scripts.download_barcelona inspect\npython -m scripts.download_barcelona sample\npython -m scripts.download_barcelona all\npython -m scripts.run_barcelona_v071',language='powershell')
            st.stop()
    try:
        # Uploaded sessions are browser-session state, not a global shared cache.
        with st.spinner('Verifica corpus locale…'):
            if key=='barcelona':
                corpus,audit=load_barcelona(signature(key));st.session_state['barcelona_audit']=audit
            else:
                corpus=(from_sessions([telemetry.get_source(key)],catalog[key]) if key.startswith('upload:')
                        else load_corpus(key,signature(key)))
    except (ValueError,OSError) as exc:
        st.error(f'Corpus non disponibile: {exc}')
        st.stop()
    return corpus


def show_eligibility(corpus):
    if barcelona_active():
        from motorsport.ml.barcelona_recovery import data_gate
        gate=data_gate(corpus,st.session_state.get('barcelona_audit'))
    else:gate=eligibility(corpus)
    a,b,c,d=st.columns(4)
    a.metric('Giri validati',gate['validated_laps'])
    b.metric('Blocchi di recording' if barcelona_active() else 'Sessioni fisiche',gate['physical_sessions'])
    c.metric('Codici fonte (anche incerti)' if barcelona_active() else 'Piloti identificati',gate['drivers'])
    d.metric('Copertura minima segnali chiave',f"{gate['min_core_coverage']:.1%}")
    if gate['eligible']:
        st.success('Idoneità tecnica ML verificata: split per recording disponibile.' if barcelona_active()
                   else 'Idoneità tecnica ML verificata: split per sessione disponibile.')
    else:
        st.warning('Training robusto disabilitato: '+'; '.join(gate['reasons']))
    if not barcelona_active():
        st.caption('Le soglie di idoneità sono requisiti minimi di progetto; non dimostrano generalizzazione. '
                   'Le sessioni ACGym derivano da cartelle e date coerenti, con identità anonime dichiarate dalla fonte.')
    if barcelona_active():
        audit=st.session_state.get('barcelona_audit',{})
        st.caption(f"Audit Barcelona: {audit.get('validated_complete_laps',0)} giri completi verificati; {len(corpus.laps)} utilizzabili. "
                   f"Recuperati {audit.get('recovered_metadata_laps',0)} giri esclusi per metadati e {audit.get('additional_recovered_laps',0)} per arrotondamento. "
                   'Holdout retrospettivo per blocchi di recording; identità e collegamenti incerti restano dichiarati. '
                   'Non dimostra generalizzazione a sessioni o piloti mai osservati.')
        if gate['eligible']:
            st.write('Blocchi per partizione:',gate['group_counts'])
            st.write('Giri per partizione:',gate['lap_counts'])
        else:
            st.info('Corpus tecnicamente non utilizzabile: controlla le motivazioni dell’audit.')
        with st.expander('Audit dei recording Barcelona e metadati incerti'):
            st.dataframe(pd.DataFrame(audit.get('records',[])),width='stretch')
    return gate


@st.cache_data(show_spinner=False,max_entries=3)
def snapshot_table(corpus):
    return snapshots(corpus)


def get_bundle(corpus):
    bundle=st.session_state.get('ml_bundles',{}).get(corpus.identity)
    if barcelona_active():
        from motorsport.ml.barcelona_recovery import verify_compatibility,data_gate
        from motorsport.ml.barcelona_experiment_v071 import load_bundle
        if bundle is None and data_gate(corpus,st.session_state.get('barcelona_audit'))['eligible']:
            directory=ROOT/'artifacts/barcelona_v071/models'
            if (directory/('barcelona-v071-'+corpus.identity[:16]+'.joblib')).exists():
                try:bundle=load_bundle(corpus,directory)
                except (ValueError,OSError) as exc:st.error('Modello Barcelona incompatibile/non verificato: '+str(exc));return None
        if bundle is not None:
            try:verify_compatibility(bundle,corpus)
            except ValueError as exc:st.error('Modello incompatibile: '+str(exc));return None
            if not data_gate(corpus,st.session_state.get('barcelona_audit'))['eligible']:
                st.error('Modello non utilizzabile: il corpus Barcelona presenta difetti tecnici.');return None
    return bundle


def display_table(frame):
    """Mixed-type ordering tuples are metadata, rendered as text for Arrow."""
    result=frame.copy()
    for column in ('start_order','domain'):
        if column in result:
            result[column]=result[column].map(str)
    return result


def baseline_history(corpus,bundle):
    if bundle is not None:
        return bundle.history
    if barcelona_active():return []  # References come from the explicitly fitted TRAIN population.
    try:
        split=chronological_split(corpus,experimental=not eligibility(corpus)['eligible'])
    except ValueError:
        return []
    return reference_history(corpus,set(split.loc[split.partition=='train','lap_uid']))
