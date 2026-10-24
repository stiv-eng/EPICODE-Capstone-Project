"""Standalone compatibility wrapper; navigation uses Data Explorer."""
import streamlit as st
from motorsport_ui.telemetry import select_telemetry, time_window
from motorsport_ui.dynamics import render_dynamics
st.title('Vehicle Dynamics')
session=select_telemetry('dynamics')
render_dynamics(session,time_window(session.data,'dynamics_window'))
