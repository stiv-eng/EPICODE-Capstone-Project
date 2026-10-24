"""Offline-first entrypoint; legacy pages are opt-in and lazily executed."""
import streamlit as st

st.set_page_config(page_title='Motorsport Telemetry Analyzer', page_icon='🏎️', layout='wide')


def home():
    st.title('Motorsport Telemetry Analyzer')
    st.caption('v0.6.2 · UI Refinement & ML Health Assessment · Python · Plotly')
    st.markdown('Una piattaforma di analisi telemetrica con esempi locali **GT7 e AssettoCorsaGym** '
                'e supporto per file **Parquet e CSV**, senza simulatore in esecuzione.')
    st.markdown('Nel **Data Explorer** puoi scegliere gli esempi disponibili, caricare altri file, '
                'controllare la qualità dei segnali e studiare telemetria e posizione. '
                'I calcoli usano tutti i campioni; i grafici limitano i punti visualizzati.')
    st.markdown('Le analisi sui giri sono disponibili soltanto con confini validati. '
                'La sessione rimane esplorabile anche senza informazioni affidabili sui giri.')
    st.page_link('pages/00_Data_Explorer.py', label='Apri Data Explorer', icon='📊')
    st.page_link('pages/10_Session_Overview.py', label='Apri Session Overview', icon='📈')
    st.markdown('Analizza input del pilota, dinamica e pneumatici; confronta finestre di sessione '
                'o giri verificati e ispeziona la traiettoria con un marcatore temporale. '
                'Data Explorer raccoglie Signals, Driver Inputs, Vehicle Dynamics, Tyre Analysis, Cockpit e Position / Track Map.')
    st.info('Il dataset locale non richiede download, FastF1 o un simulatore in esecuzione.')
    st.markdown('In **Machine Learning** puoi addestrare Ridge, Random Forest e SVR su prefissi causali. '
                '**Progressive Prediction** riproduce un giro storico senza usare il risultato finale come input. '
                'I moduli storici SVR e Keras restano disponibili nelle pagine legacy.')
    st.page_link('pages/20_Machine_Learning.py',label='Apri Machine Learning')
    st.page_link('pages/21_Progressive_Prediction.py',label='Apri Progressive Prediction')


pages = {'Telemetria locale': [st.Page(home, title='Home', icon='🏁', default=True),
                             st.Page('pages/10_Session_Overview.py', title='Session Overview',icon='📈',url_path='overview'),
                             st.Page('pages/00_Data_Explorer.py', title='Data Explorer', icon='📊'),
                             st.Page('pages/14_Session_Comparison.py',title='Telemetry Comparison',icon='📉',url_path='comparison')]}
pages['Machine Learning']=[st.Page('pages/20_Machine_Learning.py',title='Machine Learning',url_path='ml'),
                           st.Page('pages/21_Progressive_Prediction.py',title='Progressive Prediction',url_path='replay')]
with st.sidebar:
    st.caption('Motorsport Telemetry Analyzer · v0.6.2')
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
