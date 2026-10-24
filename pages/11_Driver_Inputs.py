"""Standalone compatibility wrapper; navigation uses Data Explorer."""
import streamlit as st
from motorsport_ui.telemetry import select_telemetry, time_window
from motorsport_ui.inputs import render_driver_inputs
st.title('Driver Inputs')
session=select_telemetry('inputs')
render_driver_inputs(session,time_window(session.data,'inputs_window'))
