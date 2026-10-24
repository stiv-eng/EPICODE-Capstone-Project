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


def source_catalog(include_acgym=False):
    sources={str(p.resolve()):str(p.relative_to(ROOT)) for folder in [ROOT/'data/raw',ROOT/'data/demo']
             for p in sorted(folder.glob('*')) if p.suffix.lower() in {'.csv','.parquet'}}
    bundle=ROOT/'data/raw/gt7_trial_mountain_962c'
    if (bundle/'data/laps/lap_015.parquet').exists():
        sources[str(bundle.resolve())]='GT7 · Trial Mountain · Porsche 962 C'
    # Individual physical recordings are selectable without concatenating clocks
    # or changing the unchanged ML corpus catalog and its independence rules.
    if include_acgym:
        manifest=ROOT/'docs/ACGYM_MANIFEST_V06.json'
        if manifest.exists():
            for entry in json.loads(manifest.read_text(encoding='utf-8'))['files']:
                path=ROOT/'data/raw/acgym_monza_dallara'/entry['path']
                if path.suffix=='.ld' and path.exists() and entry['driver_label']!='A':
                    sources['acgym:'+entry['path']]='ACGym · '+entry['recording_label']+' / '+path.stem
    for key,session in st.session_state.get('telemetry_registry',{}).items():
        if key.startswith('acgym:') and not include_acgym:
            continue
        sources.setdefault(key,'Upload / '+session.metadata['filename'])
    return sources


def source_signature(key):
    if key.startswith('upload:'):
        return ()
    if key.startswith('acgym:'):
        path=ROOT/'data/raw/acgym_monza_dallara'/key.removeprefix('acgym:')
        paths=[path,path.with_suffix('.ldx'),ROOT/'docs/ACGYM_MANIFEST_V06.json']
        return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths if p.is_file())
    path=Path(key)
    if path.is_dir():
        return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in sorted(path.rglob('*.parquet')))
    if path.is_file():
        stat=path.stat()
        return ((key,stat.st_mtime_ns,stat.st_size),)
    return ()


@st.cache_data(show_spinner=False,max_entries=3)
def load_local(key, signature):
    if key.startswith('acgym:'):
        from motorsport.ingestion.acgym_importer import load_acgym_recording
        manifest=json.loads((ROOT/'docs/ACGYM_MANIFEST_V06.json').read_text(encoding='utf-8'))
        entry=next(e for e in manifest['files'] if e['path']==key.removeprefix('acgym:'))
        directory=(ROOT/'data/raw/acgym_monza_dallara').resolve()
        path=(directory/entry['path']).resolve()
        if not path.is_relative_to(directory):
            raise ValueError('Unsafe source manifest path')
        # Verify both timing evidence and payload before using the existing adapter.
        for item in manifest['files']:
            evidence=(directory/item['path']).resolve()
            if evidence in (path,path.with_suffix('.ldx')):
                if hashlib.sha256(evidence.read_bytes()).hexdigest()!=item['sha256']:
                    raise ValueError('ACGym source integrity mismatch')
        from .acgym import enrich_recording
        return enrich_recording(load_acgym_recording(path,entry,manifest),path)
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
    sources=source_catalog(include_acgym=True)
    if not sources:
        st.info('Apri Data Explorer e carica un file, oppure inserisci CSV/Parquet in data/raw/.')
        st.stop()
    keys=list(sources)
    active=st.session_state.get('telemetry_active_key',keys[0])
    # Widget state is synchronized from durable state; page removal otherwise
    # deletes widgets and stale page-specific keys override the active dataset.
    widget_key=f'{page_key}_source'
    st.session_state[widget_key]=active if active in keys else keys[0]
    def changed():
        st.session_state['telemetry_active_key']=st.session_state[widget_key]
    with st.sidebar:
        key=st.selectbox('Dataset analizzato',keys,
                         format_func=sources.get,key=widget_key,on_change=changed)
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
    groups=list(frame.groupby('_ui_lap',sort=False)) if '_ui_lap' in frame else [('',frame)]
    if '_ui_lap' in frame:
        x_column='lap_elapsed_s'
    fig=make_subplots(rows=len(channels),cols=1,shared_xaxes=True,subplot_titles=channels,
                      vertical_spacing=min(.04,.5/max(len(channels),1)))
    shown=0
    from .visuals import selection_color
    for label,view in groups:
        sample=chart_sample(view,channels,max_points=max(4,5000//len(groups)))
        shown+=len(sample)
        x=sample[x_column] if x_column in sample else sample.index
        for row,channel in enumerate(channels,1):
            y=chart_values(view,sample,channel,x_column)
            # Bounded SVG paths remove dependence on GPU canvas restoration
            # across reruns and section remounts. The intermittent v0.6 symptom
            # was not reproduced in local Chrome; context loss is not asserted.
            fig.add_trace(go.Scatter(x=x,y=y,name=label or channel,mode='lines',connectgaps=False,
                legendgroup=label,showlegend=bool(label) and row==1,
                line=dict(color=selection_color(label)) if label else None),row=row,col=1)
            fig.update_yaxes(title_text=signal_unit(session,channel),row=row,col=1)
    fig.update_xaxes(title_text=x_column+' (s)' if x_column in ['elapsed_s','relative_s','lap_elapsed_s'] else x_column,
                     row=len(channels),col=1)
    fig.update_layout(template='plotly_dark',height=max(330,190*len(channels)),
                      hovermode='x unified',showlegend=len(groups)>1,
                      legend=dict(orientation='h',y=1.08),margin=dict(t=80 if len(groups)>1 else 35,b=30),
                      uirevision=key or 'signals')
    st.plotly_chart(fig,width='stretch',key=key)
    st.caption(f'{shown:,} punti nel grafico; {len(frame):,} campioni disponibili ai calcoli.'
               + (' Asse: tempo relativo del giro in secondi; nessun allineamento tramite timestamp assoluti.' if '_ui_lap' in frame else ''))


def metric_export(table,filename,key):
    st.download_button('Esporta metriche CSV',table.to_csv(index=False).encode('utf-8'),
                       file_name=filename,mime='text/csv',key=key)


def capability_table(session):
    from motorsport.analytics.readiness import assess_capabilities
    return pd.DataFrame([{'capability':k,**v} for k,v in assess_capabilities(session).items()])


def unavailable_capabilities(session):
    from motorsport.analytics.readiness import assess_capabilities
    advice={
        'session_analysis':('Analisi segnali','Carica almeno un canale numerico con valori finiti.'),
        'time_window_comparison':('Confronto temporale','Fornisci un tempo dichiarato non decrescente e intervalli osservati validi.'),
        'track_position_analysis':('Track visualization','Carica telemetria con coordinate X/Y compatibili, finite e variabili.'),
        'validated_lap_analysis':('Lap comparison','Carica contatori giro affidabili e informazioni di timing con confini completi verificabili.'),
        'lap_progress_comparison':('Confronto in distanza','Fornisci giri completi e distanza monotona verificata; resta disponibile il tempo relativo.'),
        'cumulative_lap_delta':('Delta cumulato','Fornisci un riferimento comune verificato di distanza sul tracciato.'),
        'full_lap_targets':('Target tempo giro','Fornisci timing indipendente e confini completi dei giri.'),
        'supervised_ml_eligible':('Training multi-sessione','Apri Machine Learning per la verifica del corpus; fornisci più sessioni indipendenti e segnali completi.'),
        'progressive_dl_eligible':('Deep Learning progressivo','Fornisci un corpus indipendente idoneo e progressione validata; modelli sequenziali fuori ambito v0.6.1.'),
    }
    reasons={
        'session_analysis':'Nessun segnale numerico finito.',
        'time_window_comparison':'Tempo assente, non ordinato o privo di supporto misurato.',
        'track_position_analysis':'Coordinate X/Y assenti, invalide o costanti.',
        'validated_lap_analysis':'Mancano confini giro completi validati.',
        'lap_progress_comparison':'Mancano giri completi con distanza monotona valida.',
        'cumulative_lap_delta':'Manca un riferimento comune verificato di distanza.',
        'full_lap_targets':'Manca un tempo finale validato indipendentemente.',
        'supervised_ml_eligible':'Questa singola sorgente non supera i requisiti multi-sessione.',
        'progressive_dl_eligible':'Corpus o progressione insufficienti per il gate sequenziale.',
    }
    return pd.DataFrame([{'Feature':advice[k][0],'Why unavailable':reasons[k],'Recommended data':advice[k][1]}
                         for k,v in assess_capabilities(session).items() if not v['available']],
                        columns=['Feature','Why unavailable','Recommended data'])


def render_unavailable(session):
    for row in unavailable_capabilities(session).to_dict('records'):
        st.info(f"**{row['Feature']} unavailable.** {row['Why unavailable']} {row['Recommended data']}")
