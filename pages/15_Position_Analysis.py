"""Standalone compatibility wrapper; navigation uses Data Explorer."""
import streamlit as st
from motorsport_ui.telemetry import select_telemetry, time_window
from motorsport_ui.position import render_position
st.title('Position Analysis')
session=select_telemetry('position')
render_position(session,time_window(session.data,'position_window'))
