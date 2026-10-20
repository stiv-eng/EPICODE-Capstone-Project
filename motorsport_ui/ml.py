"""Shared offline corpus selection and persistent, explicitly trained bundles."""
from pathlib import Path

import streamlit as st

from motorsport.ml.dataset import from_sessions,independent_subset,eligibility
from motorsport.ml.features import snapshots
from motorsport.ml.baselines import reference_history
from motorsport.ml.training import chronological_split
from motorsport_ui import telemetry

ROOT=Path(__file__).resolve().parents[1]


def corpus_catalog():
    catalog={}
    if (ROOT/'data/raw/acgym_monza_dallara').exists():
        catalog['acgym']='ACGym · human Monza / Dallara · verified independent subset'
    for key,label in telemetry.source_catalog().items():
        catalog[key]=label
    return catalog


def signature(key):
    if key=='acgym':
        paths=sorted((ROOT/'data/raw/acgym_monza_dallara').rglob('*'))+[ROOT/'docs/ACGYM_MANIFEST_V06.json']
        return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths if p.is_file())
    return telemetry.source_signature(key)


@st.cache_data(show_spinner=False,max_entries=3)
def load_corpus(key,source_signature):
    if key=='acgym':
        from motorsport.ingestion.acgym_importer import load_acgym_sessions
        sessions,rejected=load_acgym_sessions(ROOT/'data/raw/acgym_monza_dallara',ROOT/'docs/ACGYM_MANIFEST_V06.json')
        corpus=from_sessions(sessions,'ACGym human Monza / Dallara F317')
        corpus.exclusions.extend(rejected)
        return independent_subset(corpus)
    return from_sessions([telemetry.get_source(key)],telemetry.source_catalog().get(key,key))


def select_corpus(page):
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
    try:
        # Uploaded sessions are browser-session state, not a global shared cache.
        with st.spinner('Verifica corpus locale…'):
            corpus=(from_sessions([telemetry.get_source(key)],catalog[key]) if key.startswith('upload:')
                    else load_corpus(key,signature(key)))
    except (ValueError,OSError) as exc:
        st.error(f'Corpus non disponibile: {exc}')
        st.stop()
    return corpus


def show_eligibility(corpus):
    gate=eligibility(corpus)
    a,b,c,d=st.columns(4)
    a.metric('Giri validati',gate['validated_laps'])
    b.metric('Sessioni fisiche',gate['physical_sessions'])
    c.metric('Piloti identificati',gate['drivers'])
    d.metric('Copertura minima segnali chiave',f"{gate['min_core_coverage']:.1%}")
    if gate['eligible']:
        st.success('Idoneità tecnica ML verificata: split per sessione disponibile.')
    else:
        st.warning('Training robusto disabilitato: '+'; '.join(gate['reasons']))
    st.caption('Le soglie di idoneità sono requisiti minimi di progetto; non dimostrano generalizzazione. '
               'Le sessioni ACGym derivano da cartelle e date coerenti, con identità anonime dichiarate dalla fonte.')
    return gate


@st.cache_data(show_spinner=False,max_entries=3)
def snapshot_table(corpus):
    return snapshots(corpus)


def get_bundle(corpus):
    return st.session_state.get('ml_bundles',{}).get(corpus.identity)


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
    try:
        split=chronological_split(corpus,experimental=not eligibility(corpus)['eligible'])
    except ValueError:
        return []
    return reference_history(corpus,set(split.loc[split.partition=='train','lap_uid']))
