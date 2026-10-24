"""Standalone compatibility wrapper; navigation uses Data Explorer."""
import streamlit as st
from motorsport_ui.telemetry import select_telemetry, time_window
from motorsport_ui.tyres import render_tyres
st.title('Tyre Analysis')
session=select_telemetry('tyres')
render_tyres(session,time_window(session.data,'tyres_window'))
