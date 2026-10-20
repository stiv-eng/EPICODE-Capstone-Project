"""Shared local-source selection, UI cache and consistent analytical charts."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from motorsport.pipeline import load_session
from motorsport.processing.schema import SUPPLIED_V04
from motorsport.analytics.channels import signal_unit
from motorsport.analytics.session_metrics import chart_sample
from motorsport.analytics.timebase import numeric, time_support, chart_values

ROOT=Path(__file__).resolve().parents[1]
SUPPLIED_HASH='fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7'


def source_catalog():
    sources={str(p.resolve()):str(p.relative_to(ROOT)) for folder in [ROOT/'data/raw',ROOT/'data/demo']
             for p in sorted(folder.glob('*')) if p.suffix.lower() in {'.csv','.parquet'}}
    bundle=ROOT/'data/raw/gt7_trial_mountain_962c'
    if (bundle/'data/laps/lap_015.parquet').exists():
        sources[str(bundle.resolve())]='GT7 · Trial Mountain · Porsche 962 C'
    for key,session in st.session_state.get('telemetry_registry',{}).items():
        sources.setdefault(key,'Upload / '+session.metadata['filename'])
    return sources


def source_signature(key):
    if key.startswith('upload:'):
        return ()
    path=Path(key)
    if path.is_dir():
        return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in sorted(path.rglob('*.parquet')))
    if path.is_file():
        stat=path.stat()
        return ((key,stat.st_mtime_ns,stat.st_size),)
    return ()


@st.cache_data(show_spinner=False,max_entries=3)
def load_local(key, signature):
    path=Path(key)
    if path.is_dir():
        from motorsport.ingestion.gt7_importer import load_gt7_bundle
        return load_gt7_bundle(path)
    with path.open('rb') as stream:
        audited=hashlib.file_digest(stream,'sha256').hexdigest()==SUPPLIED_HASH
    session=load_session(path,profile=SUPPLIED_V04) if audited else load_session(path)
    if audited:
        session.metadata.update(position_provenance='integrated velocity; drift and accuracy unverified',
                                time_basis='simulator timestamp; repeated values retained')
    return session


def register_session(session,key):
    session.metadata['file_signature']=source_signature(key)
    st.session_state.setdefault('telemetry_registry',{})[key]=session
    st.session_state['telemetry_active_key']=key


def get_source(key):
    registry=st.session_state.get('telemetry_registry',{})
    if key in registry:
        if key.startswith('upload:') or registry[key].metadata.get('file_signature')==source_signature(key):
            return registry[key]
        # File replacement invalidates a Data Explorer registration as well as
        # the normal file cache, rather than keeping stale canonical values.
        registry.pop(key)
    return load_local(key,source_signature(key))


def select_telemetry(page_key='analysis'):
    sources=source_catalog()
    if not sources:
        st.info('Apri Data Explorer e carica un file, oppure inserisci CSV/Parquet in data/raw/.')
        st.stop()
    keys=list(sources)
    active=st.session_state.get('telemetry_active_key',keys[0])
    with st.sidebar:
        key=st.selectbox('Dataset analizzato',keys,index=keys.index(active) if active in keys else 0,
                         format_func=sources.get,key=f'{page_key}_source')
    st.session_state['telemetry_active_key']=key
    try:
        with st.spinner('Lettura e verifica telemetria…'):
            session=get_source(key)
    except Exception as exc:
        st.error(f'Dataset non disponibile: {exc}')
        st.stop()
    st.caption(session.metadata['filename'])
    if session.metadata.get('time_basis'):
        st.caption('Base temporale: '+session.metadata['time_basis'])
    return session


def time_window(frame,key='window'):
    t=numeric(frame,'elapsed_s')
    finite=t[np.isfinite(t)]
    if len(finite)<2 or finite[-1]<=finite[0] or (np.diff(t)<0).any():
        st.info('Intervallo temporale non disponibile: serve un tempo dichiarato non decrescente.')
        return frame
    bounds=st.slider('Intervallo di sessione (s)',float(finite[0]),float(finite[-1]),
                     (float(finite[0]),float(finite[-1])),key=key)
    selected=np.flatnonzero(np.isfinite(t) & (t>=bounds[0]) & (t<=bounds[1]))
    return frame.iloc[selected[0]:selected[-1]+1] if len(selected) else frame.iloc[:0]


def quality_caption(frame):
    q=time_support(frame)
    st.caption(f"Supporto osservato: {q['observed_s']:.3f} s · "
               f"passi temporali ripetuti: {q['duplicate_steps']} · lacune: {q['large_gaps']} "
               f"({q['excluded_gap_s']:.3f} s esclusi). Medie temporali: mantenimento del campione precedente; ultimo campione senza durata aggiunta.")


def signal_chart(frame,channels,session,x_column='elapsed_s',key=None):
    channels=[c for c in channels if c in frame]
    if not channels or frame.empty:
        st.info('Nessun segnale disponibile per questa selezione.')
        return
    sample=chart_sample(frame,channels,max_points=5000)
    x=sample[x_column] if x_column in sample else sample.index
    fig=make_subplots(rows=len(channels),cols=1,shared_xaxes=True,subplot_titles=channels,
                      vertical_spacing=min(.04,.5/max(len(channels),1)))
    for row,channel in enumerate(channels,1):
        y=chart_values(frame,sample,channel,x_column)
        fig.add_trace(go.Scattergl(x=x,y=y,name=channel,mode='lines',connectgaps=False),row=row,col=1)
        fig.update_yaxes(title_text=signal_unit(session,channel),row=row,col=1)
    fig.update_xaxes(title_text=x_column+' (s)' if x_column in ['elapsed_s','relative_s','lap_elapsed_s'] else x_column,
                     row=len(channels),col=1)
    fig.update_layout(template='plotly_dark',height=max(330,190*len(channels)),
                      hovermode='x unified',showlegend=False,margin=dict(t=35,b=30))
    st.plotly_chart(fig,width='stretch',key=key)
    st.caption(f'{len(sample):,} punti nel grafico; {len(frame):,} campioni disponibili ai calcoli.')


def metric_export(table,filename,key):
    st.download_button('Esporta metriche CSV',table.to_csv(index=False).encode('utf-8'),
                       file_name=filename,mime='text/csv',key=key)


def capability_table(session):
    from motorsport.analytics.readiness import assess_capabilities
    return pd.DataFrame([{'capability':k,**v} for k,v in assess_capabilities(session).items()])
