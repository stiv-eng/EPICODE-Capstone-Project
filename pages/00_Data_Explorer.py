"""One source, one lap/window selection, six lazily rendered analytical sections."""
from pathlib import Path
import pandas as pd
import streamlit as st
from motorsport_ui.explorer_source import explorer_source
from motorsport_ui.selection import shared_selection, SECTIONS
from motorsport_ui.telemetry import signal_chart, render_unavailable
from motorsport.analytics.channels import usable_channels
from motorsport_ui.widgets import valid_multiselect

ROOT = Path(__file__).resolve().parents[1]

st.title('Data Explorer')
st.caption('Signals / Driver Inputs / Vehicle Dynamics / Tyre Analysis / Cockpit / Position / Track Map')
session=explorer_source()
metrics=session.metrics
a,b,c,d=st.columns(4)
a.metric('Campioni',f'{len(session.data):,}')
b.metric('Canali sorgente',len(session.raw.columns))
duration=metrics.get('duration_s');speed=metrics.get('speed_kmh_max')
c.metric('Durata',f'{duration:.2f} s' if duration is not None else 'N/D')
d.metric('Velocita massima',f'{speed:.1f} km/h' if speed is not None else 'N/D')
with st.expander('Dataset e qualita'):
    st.json(session.metadata)
    st.dataframe(pd.DataFrame(session.quality['channels']),hide_index=True,width='stretch')
    st.dataframe(session.raw.head(100),width='stretch')
    render_unavailable(session)
frame=shared_selection(session)
# Only one section mounts at a time; durable state survives widget cleanup.
section=st.radio('Sezione analitica',SECTIONS,horizontal=True,key='explorer_section')
st.subheader(section)
if frame.empty:
    st.info('Seleziona almeno un giro o un intervallo contenente campioni.')
elif section=='Signals':
    expected=['speed_kmh','throttle_pct','brake_pct','steering','rpm','gear']
    missing=[c for c in expected if c not in frame]
    if missing:
        st.info('Canali canonici assenti: '+', '.join(missing)+'. Usa la mappatura se presenti con altri nomi.')
    options=usable_channels(frame)
    channels=valid_multiselect('Segnali da visualizzare',options,key='explorer_channels',
        default=[c for c in expected if c in options][:4],max_selections=8)
    signal_chart(frame,channels,session,key='explorer_signals')
elif section=='Driver Inputs':
    from motorsport_ui.inputs import render_driver_inputs
    render_driver_inputs(session,frame)
elif section=='Vehicle Dynamics':
    from motorsport_ui.dynamics import render_dynamics
    render_dynamics(session,frame)
elif section=='Tyre Analysis':
    from motorsport_ui.tyres import render_tyres
    render_tyres(session,frame)
elif section=='Cockpit':
    from motorsport_ui.cockpit import render_cockpit
    render_cockpit(session,frame)
else:
    from motorsport_ui.position import render_position
    render_position(session,frame)
