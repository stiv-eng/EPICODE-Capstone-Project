"""Offline browser fixture entrypoint; never included in app navigation."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import plotly.graph_objects as go
import streamlit as st
from scripts.hover_fixture_specs import legacy_specs
from motorsport_ui.hover import render_figures

st.set_page_config(layout='wide')
st.title('Offline legacy chart fixtures')
render_figures([(go.Figure(spec),'xy') for spec in legacy_specs()],key='legacy_fixtures')
from motorsport.pipeline import build_session
from motorsport_ui.telemetry import signal_chart
import pandas as pd
clockless=build_session(pd.DataFrame({'speed_kmh':[50.,60.,70.]}),{'filename':'no declared clock'})
signal_chart(clockless.data,['speed_kmh'],clockless,key='clockless_signals')
