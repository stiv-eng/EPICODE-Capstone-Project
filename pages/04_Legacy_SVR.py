"""Confronto didattico: regressione SVR (modello storico) vs futura previsione Keras."""
import pandas as pd
import plotly.express as px
import streamlit as st
from motorsport_ui.hover import render_chart
from motorsport_ui.common import event_names, session_data
from motorsport_ui.svr import lap_features, fit_svr

st.set_page_config(layout='wide')
st.title('Historical SVR · Machine Learning')
st.caption('Adattamento Streamlit del precedente Codes/Page_3.py')
st.info('SVR usa statistiche dell’intero giro. È un modello retrospettivo, NON una '
        'previsione progressiva causale del giro in corso; per quella usa Keras.')
with st.sidebar:
    year = st.number_input('Stagione · SVR', 2018, 2026, 2024)
    try:
        names = event_names(year)
    except Exception:
        names = []
    event = st.selectbox('GP · SVR', names) if names else st.text_input('GP · SVR', 'Monza')
    driver = st.text_input('Codice pilota (3 lettere)', 'LEC').strip().upper()
    go = st.button('Addestra SVR', type='primary')
if go:
    try:
        frames = []
        for code in ('Q', 'R'):
            session = session_data(year, event, code)
            frames.append(lap_features(session, code, driver))
        dataset = pd.concat(frames, ignore_index=True)
        model, results, scores = fit_svr(dataset)
        st.session_state['svr_results'] = (year, event, driver, dataset, results, scores)
    except Exception as exc:
        st.error(f'SVR non disponibile: {exc}')
saved = st.session_state.get('svr_results')
if saved:
    saved_year, saved_event, saved_driver, dataset, results, scores = saved
    st.subheader(f'{saved_driver} · {saved_event} {saved_year}')
    a, b, c = st.columns(3)
    a.metric('MAE', f"{scores['MAE_s']:.3f} s")
    b.metric('RMSE', f"{scores['RMSE_s']:.3f} s")
    c.metric('R²', f"{scores['R2']:.3f}")
    fig = px.scatter(results, x='actual_s', y='predicted_s',
                     title='SVR · tempo effettivo vs stimato',
                     labels={'actual_s': 'Tempo effettivo [s]',
                             'predicted_s': 'Tempo stimato [s]'})
    vmin = min(results[['actual_s', 'predicted_s']].min())
    vmax = max(results[['actual_s', 'predicted_s']].max())
    fig.add_shape(type='line', x0=vmin, x1=vmax, y0=vmin, y1=vmax,
                  line={'dash': 'dash', 'color': 'white'})
    render_chart(fig, use_container_width=True)
    st.dataframe(dataset, hide_index=True, use_container_width=True)
    st.caption('Suddivisione casuale train/test su giri Q/R di un pilota; metriche '
               'puramente dimostrative, non confrontabili direttamente al test Keras su Q.')
