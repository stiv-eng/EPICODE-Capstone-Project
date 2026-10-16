"""Avvio autonomo Streamlit. Non modifica alcun entrypoint del repository legacy."""
import streamlit as st

st.set_page_config(page_title='Motorsport Performance Analysis', page_icon='🏎️', layout='wide')
st.title('Motorsport Performance Analysis')
st.caption('Formula 1 · FastF1 · Python · Plotly · Keras')
st.markdown('''
### Analisi telemetrica e previsione del tempo sul giro

Questa interfaccia unisce l'analisi esplorativa delle sessioni Formula 1 con una
rete neurale per prevedere progressivamente il tempo finale durante il replay
storico di un giro di qualifica.

Scegli una pagina nel menu a sinistra:

- **Lap & Stint Analysis:** tempi sul giro, risultati, strategie pneumatici e regressioni.
- **Telemetry Comparison:** due giri a confronto, throttle/brake/RPM, delta tempo.
- **Track Map:** traiettoria XY e distribuzione delle velocità.
- **Historical SVR:** regressione classica del progetto originale (solo retrospettiva).
- **Dynamic Lap Time Prediction:** addestramento FP1/FP2/FP3 e replay qualifica.
- **Model Evaluation:** confronto quantitativo tra baseline e rete sui giri di qualifica.

**Dati:** FastF1 (richiede connessione al primo utilizzo); per la rete neurale,
la qualifica è riservata esclusivamente a replay e valutazione, mai al training.
''')
st.info('Frontend integrabile: Il codice originale è preservato nel repository di partenza.')