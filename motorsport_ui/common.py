"""Accesso FastF1 e selettori condivisi fra tutte le pagine Streamlit.

I moduli di analisi sono indipendenti dall'interfaccia: questa dipendenza da
Streamlit resta isolata, per consentire test senza server web.
"""
from pathlib import Path

import streamlit as st

CACHE_DIR = '.fastf1_cache'


def setup_cache():
    import fastf1
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)


@st.cache_data(show_spinner=False, ttl=3600, max_entries=12)
def event_names(year):
    import fastf1
    setup_cache()
    events = fastf1.get_event_schedule(int(year), include_testing=False)
    return [str(name) for name in events['EventName'].dropna().unique()]


@st.cache_resource(show_spinner=False, max_entries=6)
def session_data(year, event, code):
    import fastf1
    setup_cache()
    session = fastf1.get_session(int(year), event, code)
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    return session


def select_session(prefix='analysis', default='R'):
    """Un unico metodo di selezione per ciascuna pagina, evita duplicazioni."""
    with st.sidebar:
        st.subheader('Sessione Formula 1')
        year = st.number_input('Stagione', 2018, 2026, 2024, key=f'{prefix}_year')
        try:
            events = event_names(int(year))
        except Exception as exc:
            st.warning(f'Calendario non disponibile: {exc}')
            events = []
        if events:
            event = st.selectbox('Gran Premio', events, key=f'{prefix}_event')
        else:
            event = st.text_input('Gran Premio / numero round', 'Monza', key=f'{prefix}_event_text')
        labels = {'FP1': 'FP1', 'FP2': 'FP2', 'FP3': 'FP3', 'Q': 'Qualifica', 'R': 'Gara', 'S': 'Sprint'}
        codes = list(labels)
        code = st.selectbox('Sessione', codes, index=codes.index(default),
                            format_func=labels.get, key=f'{prefix}_session')
    return int(year), event, code


def load_selected_session(year, event, code):
    try:
        with st.spinner(f'Caricamento {event} {year} · {code}…'):
            return session_data(year, event, code)
    except Exception as exc:
        st.error(f'Sessione non disponibile: {exc}')
        st.info('Verifica che la sessione sia disputata e che FastF1 possa scaricare i dati.')
        st.stop()


def lap_choices(session, driver):
    """Restituisce lista di tuple (label, lap) per selection UI."""
    laps = session.laps.pick_drivers([driver])
    if 'LapTime' in laps:
        laps = laps.loc[laps['LapTime'].notna()]
    if 'IsAccurate' in laps:
        laps = laps.loc[laps['IsAccurate'].fillna(False).astype(bool)]
    if 'Deleted' in laps:
        laps = laps.loc[~laps['Deleted'].fillna(False).astype(bool)]
    choices = []
    for _, lap in laps.sort_values('LapNumber').iterrows():
        sec = lap['LapTime'].total_seconds()
        choices.append((f"Giro {int(lap['LapNumber'])} · {sec:.3f} s · {lap.get('Compound', '?')}", lap))
    return choices