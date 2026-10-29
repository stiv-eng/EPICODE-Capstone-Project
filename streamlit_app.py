"""Offline simulator telemetry analysis entrypoint."""
import streamlit as st

st.set_page_config(page_title='Motorsport Telemetry Analyzer', page_icon='🏎️', layout='wide')


def home():
    st.title('Motorsport Telemetry Analyzer')
    st.caption('v0.9.4 · Deterministic Telemetry Lap Analysis · Python · Plotly')
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
    st.info('I dati già installati si analizzano offline, senza un simulatore in esecuzione.')
    st.markdown('Sono disponibili le registrazioni **Barcelona GP / Dallara F317**, '
                '**ACGym Monza** e **GT7 Trial Mountain**, quando installate. '
                'Data Explorer e Telemetry Comparison usano i confini dei giri verificati e i campioni sorgente osservati.')
    st.page_link('pages/14_Session_Comparison.py',label='Apri Telemetry Comparison',icon='📉')
    st.page_link('pages/16_Telemetry_Lap_Analysis.py',label='Apri Telemetry Lap Analysis',icon='🏁')
    st.caption('Seleziona una sessione, esplora i segnali e confronta giri o finestre temporali. '
               'Hover e cursore condiviso mantengono sincronizzata la lettura dei grafici.')


pages = {'Telemetria locale': [st.Page(home, title='Home', icon='🏁', default=True),
                             st.Page('pages/10_Session_Overview.py', title='Session Overview',icon='📈',url_path='overview'),
                             st.Page('pages/00_Data_Explorer.py', title='Data Explorer', icon='📊'),
                             st.Page('pages/14_Session_Comparison.py',title='Telemetry Comparison',icon='📉',url_path='comparison'),
                             st.Page('pages/16_Telemetry_Lap_Analysis.py',title='Telemetry Lap Analysis',icon='🏁',url_path='lap-analysis')]}
with st.sidebar:
    st.caption('Motorsport Telemetry Analyzer · v0.9.4')
st.navigation(pages).run()
