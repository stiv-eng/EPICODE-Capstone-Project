"""Shared exploration selection; durable state is separate from widget lifetimes."""
import hashlib
import json

import numpy as np
import pandas as pd
import streamlit as st

from motorsport.analytics.timebase import numeric

SECTIONS = ['Signals', 'Driver Inputs', 'Vehicle Dynamics', 'Tyre Analysis', 'Cockpit', 'Position / Track Map']


def lap_labels(session):
    if not session.laps.available or 'lap_id' not in session.data:
        return {}
    labels = {}
    for row in session.laps.laps.itertuples():
        # Only the adapter's verified table supplies identities and measured times.
        if not np.isfinite(row.duration_s) or row.duration_s <= 0:
            continue
        milliseconds = int(round(row.duration_s * 1000))
        minutes, remainder = divmod(milliseconds, 60000)
        seconds, fraction = divmod(remainder, 1000)
        labels[row.lap_id] = f'Lap {row.lap_id:g} — {minutes}:{seconds:02d}.{fraction:03d}'
    return labels


def selection_identity(session):
    payload = [session.metadata['session_id'], session.metadata.get('file_signature'),
               session.metadata.get('normalization'), list(lap_labels(session).items()), len(session.data)]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def reconcile_selection(state, identity, available):
    """Invalidate on source/revision/mapping change, even if lap numbers coincide."""
    if state.get('explorer_identity') != identity:
        state['explorer_identity'] = identity
        state['explorer_selected_laps'] = list(available)[:1]
        state['explorer_time_range'] = None
        for key in ('_explorer_laps', '_explorer_range', 'cockpit_lap', 'cockpit_instant', 'position_instant'):
            state.pop(key, None)
    else:
        state['explorer_selected_laps'] = [lap for lap in state.get('explorer_selected_laps', []) if lap in available]


def selected_frame(session, ids):
    labels = lap_labels(session)
    parts = []
    # Keep source order, including when selections are entered in a different order.
    for lap in labels:
        if lap not in ids:
            continue
        part = session.data.loc[session.data.lap_id.eq(lap).fillna(False)].copy()
        part['_ui_lap'] = labels[lap]
        parts.append(part)
    return pd.concat(parts) if parts else session.data.iloc[:0].copy()


def shared_selection(session):
    labels = lap_labels(session)
    reconcile_selection(st.session_state, selection_identity(session), labels)
    if labels:
        st.session_state['_explorer_laps'] = st.session_state['explorer_selected_laps']
        def laps_changed():
            st.session_state['explorer_selected_laps'] = st.session_state['_explorer_laps']
        ids = st.multiselect('Giri verificati', list(labels), format_func=labels.get, key='_explorer_laps', on_change=laps_changed)
        st.session_state['explorer_selected_laps'] = ids
        st.caption('Giri completi verificati dalla sorgente. Signals usa il tempo relativo del giro; le altre sezioni mantengono la stessa selezione.')
        return selected_frame(session, ids)
    st.caption('Analisi sui giri non disponibile. Seleziona un intervallo del tempo registrato; le finestre non sono giri completi.')
    t = numeric(session.data, 'elapsed_s')
    finite = t[np.isfinite(t)]
    if len(finite) < 2 or finite[-1] <= finite[0] or (np.diff(t) < 0).any():
        st.info('Intervallo temporale non disponibile: dichiara un canale tempo non decrescente nella mappatura. Disponibili i campioni registrati.')
        return session.data
    bounds = (float(finite[0]), float(finite[-1]))
    current = st.session_state['explorer_time_range'] or bounds
    st.session_state['_explorer_range'] = current
    def range_changed():
        st.session_state['explorer_time_range'] = st.session_state['_explorer_range']
    chosen = st.slider('Intervallo di sessione (s)', *bounds, key='_explorer_range', on_change=range_changed)
    st.session_state['explorer_time_range'] = chosen
    positions = np.flatnonzero(np.isfinite(t) & (t >= chosen[0]) & (t <= chosen[1]))
    return session.data.iloc[positions[0]:positions[-1]+1] if len(positions) else session.data.iloc[:0]


def sample_at(frame, instant, time_column='elapsed_s'):
    """Nearest actual finite-time packet, ties resolved to the earlier source row."""
    times = numeric(frame, time_column)
    available = np.flatnonzero(np.isfinite(times))
    if not len(available):
        return None
    return frame.iloc[available[np.argmin(np.abs(times[available] - instant))]]
