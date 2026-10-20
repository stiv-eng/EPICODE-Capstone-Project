"""Offline-first entrypoint; legacy pages are opt-in and lazily executed."""
import streamlit as st

st.set_page_config(page_title='Motorsport Telemetry Analyzer', page_icon='🏎️', layout='wide')


def home():
    st.title('Motorsport Telemetry Analyzer')
    st.caption('v0.4 · Dataset Foundation · Python · Plotly')
    st.markdown('Una piattaforma di analisi telemetrica che evolve verso sorgenti indipendenti '
                'dal simulatore. Questa versione lavora con file **Parquet e CSV locali**.')
    st.markdown('Nel **Data Explorer** puoi aprire il dataset allegato, caricare altri file, '
                'controllare la qualità dei segnali e studiare telemetria e posizione. '
                'I calcoli usano tutti i campioni; i grafici limitano i punti visualizzati.')
    st.markdown('Le analisi sui giri sono disponibili soltanto con confini validati. '
                'La sessione rimane esplorabile anche senza informazioni affidabili sui giri.')
    st.page_link('pages/00_Data_Explorer.py', label='Apri Data Explorer', icon='📊')
    st.info('Il dataset locale non richiede download, FastF1 o un simulatore in esecuzione.')
    st.markdown('I moduli storici SVR e Keras sono conservati. La loro migrazione '
                'sul modello dati comune è prevista per v0.6 e v0.7.')


pages = {'Telemetria locale': [st.Page(home, title='Home', icon='🏁', default=True),
                             st.Page('pages/00_Data_Explorer.py', title='Data Explorer', icon='📊')]}
with st.sidebar:
    st.caption('Motorsport Telemetry Analyzer · v0.4')
    legacy = st.checkbox('Mostra pagine legacy Formula 1', value=False)
    if legacy:
        st.warning('Le pagine legacy usano FastF1 e possono richiedere rete e dipendenze opzionali.')
if legacy:
    pages['Legacy Formula 1 · FastF1'] = [
        st.Page('pages/01_Lap_and_Stint_Analysis.py', title='Legacy · Lap & Stint'),
        st.Page('pages/02_Telemetry_Comparison.py', title='Legacy · Telemetry Comparison'),
        st.Page('pages/03_Track_Map.py', title='Legacy · Track Map'),
        st.Page('pages/04_Legacy_SVR.py', title='Legacy · Historical SVR'),
        st.Page('pages/04_Model_Evaluation.py', title='Legacy · Model Evaluation'),
        st.Page('pages/05_Dynamic_Lap_Time_Prediction.py', title='Legacy · Keras Prediction'),
    ]
st.navigation(pages).run()
