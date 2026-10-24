"""Source-independent recorded telemetry dashboard; no synthesized gauges."""
import html
import numpy as np
import pandas as pd
import streamlit as st
from motorsport.analytics.channels import corner_channels, signal_unit
from motorsport.analytics.timebase import numeric
from .selection import lap_labels, sample_at
from .telemetry import signal_chart


def render_cockpit(session, frame):
    st.caption('Replay di dati registrati. Il cursore sceglie il campione reale più vicino; nessuna acquisizione live o interpolazione.')
    if '_ui_lap' in frame:
        labels=lap_labels(session)
        ids=[lap for lap in labels if frame.lap_id.eq(lap).any()]
        if not ids:
            st.info('Seleziona almeno un giro verificato.');return
        if st.session_state.get('cockpit_lap') not in ids:
            st.session_state.pop('cockpit_lap',None)
        lap=st.selectbox('Giro Cockpit',ids,format_func=labels.get,key='cockpit_lap')
        frame=frame.loc[frame.lap_id.eq(lap).fillna(False)]
        time_column='lap_elapsed_s'
    else:
        time_column='elapsed_s'
    times=numeric(frame,time_column);finite=times[np.isfinite(times)]
    if not len(finite):
        if frame.empty:
            st.info('Nessun campione nella selezione.');return
        index=st.slider('Campione registrato',0,len(frame)-1,0) if len(frame)>1 else 0
        point=frame.iloc[index]
        st.caption('Tempo non disponibile: selezione per ordine dei campioni registrati.')
    else:
        low,high=float(finite.min()),float(finite.max())
        instant=st.slider('Istante replay (s)',low,high,low,
            key=f'cockpit_instant_{session.metadata["session_id"]}_{time_column}_{low}_{high}') if low<high else low
        point=sample_at(frame,instant,time_column)
        st.caption(f'Campione sorgente {point.name} · tempo effettivo {point[time_column]:.3f} s')
    channels=[('speed_kmh','SPEED'),('rpm','ENGINE'),('gear','GEAR'),('throttle_pct','THROTTLE'),('brake_pct','BRAKE')]
    cards=[]
    for channel,label in channels:
        if channel not in frame:
            continue
        value=pd.to_numeric(pd.Series([point[channel]]),errors='coerce').iloc[0]
        unit=signal_unit(session,channel)
        number=(f'{value:g}' if channel=='gear' else f'{value:.0f}' if channel=='rpm' else f'{value:.1f}') if np.isfinite(value) else 'N/D'
        bar=''
        if channel in ('throttle_pct','brake_pct') and np.isfinite(value) and 0<=value<=100:
            accent='#52e08a' if channel=='throttle_pct' else '#ff685d'
            bar=f'<progress max="100" value="{value}" style="width:100%;accent-color:{accent}"></progress>'
        cards.append(f'<div style="background:#182230;border:1px solid #40516a;border-radius:12px;padding:18px;min-width:0">'
                     f'<div style="color:#b7c7db;font-size:13px">{label}</div>'
                     f'<div style="font:700 clamp(24px,4vw,42px) monospace;color:#fff">{number}</div>'
                     f'<div style="color:#c3d5ea">{html.escape(unit)}</div>{bar}</div>')
    if cards:
        st.markdown('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr));gap:12px">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    else:
        st.info('Indicatori principali non disponibili. Mappa velocità, RPM, marcia o pedali con unità note.')
    for prefix in ('tyre_core','temp_i','temp_m','temp_o'):
        corners=corner_channels(frame,prefix)
        verified={corner:c for corner,c in corners.items() if signal_unit(session,c) in ('°C','C','degC','°F','F','K')}
        if verified:
            st.write('Temperature pneumatici · '+prefix)
            columns=st.columns(len(verified))
            for column,(corner,channel) in zip(columns,verified.items()):
                value=point[channel]
                column.metric(corner,f'{value:.1f} {signal_unit(session,channel)}' if pd.notna(value) and np.isfinite(value) else 'N/D')
    missing=[label for c,label in channels if c not in frame]
    if missing:
        st.caption('Indicatori non disponibili: '+', '.join(missing))
    if st.checkbox('Mostra tracce di contesto',key='cockpit_context'):
        signal_chart(frame,[c for c,_ in channels],session,x_column=time_column,key='cockpit_context_chart')
