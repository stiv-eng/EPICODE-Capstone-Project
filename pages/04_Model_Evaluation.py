"""Audit della rete: metrica FP holdout + test onesto su giri Q (mai nel train)."""
import plotly.express as px
import streamlit as st
from motorsport_prediction.model import evaluate_qualifying, summarize_qualifying
from motorsport_prediction.data import load_qualifying

st.set_page_config(layout='wide')
st.title('Model Evaluation')
st.caption('Validazione sui giri FP separati e valutazione su qualifica storica')
trained_bundle = st.session_state.get('lap_pred_training')
key = st.session_state.get('lap_pred_training_key')
if not trained_bundle or not key:
    st.info('Vai in **Dynamic Lap Time Prediction** e addestra un modello FP1/FP2/FP3. '\
            'Successivamente torna qui: il modello è condiviso via session_state.')
    st.stop()
trained, refs, counts = trained_bundle
year, event, _ = key
st.write(f'Weekend del modello: **{year} · {event}**')
mae_baseline = trained.metrics['validation_macro_baseline_mae_s']
mae_model = trained.metrics['validation_macro_keras_mae_s']
c1, c2 = st.columns(2)
c1.metric('FP holdout · baseline MAE macro', f'{mae_baseline:.3f} s')
c2.metric('FP holdout · Keras MAE macro', f'{mae_model:.3f} s', delta=f'{mae_baseline-mae_model:+.3f} s', delta_color='normal')
st.caption('Il holdout è per giro completo, non per snapshot. Non è una validazione '
           'indipendente per weekend; tutti i piloti condividono la stessa baseline FP3.')
if st.button('Valuta tutti i giri disponibili di qualifica', type='primary'):
    try:
        with st.spinner('Caricamento qualifica e valutazione out-of-sample...'):
            q = load_qualifying(year, event, max_per_driver=None)
            result = evaluate_qualifying(q, refs, trained)
            st.session_state['lap_pred_eval'] = (key, result)
    except Exception as exc:
        st.error(f'Valutazione non riuscita: {exc}')
saved = st.session_state.get('lap_pred_eval')
if saved and saved[0] == key:
    df = saved[1]
    metrics, lap_metrics, stages = summarize_qualifying(df)
    a,b,c = st.columns(3)
    a.metric('Giri Q valutati', metrics['laps'])
    b.metric('Baseline · MAE macro', f"{metrics['baseline_macro_mae_s']:.3f} s")
    c.metric('Keras · MAE macro', f"{metrics['keras_macro_mae_s']:.3f} s",
             delta=f"{metrics['improvement_s']:+.3f} s di miglioramento")
    stages_long = stages.melt('stage', var_name='Metodo', value_name='MAE (s)')
    st.plotly_chart(px.bar(stages_long, x='stage', y='MAE (s)', color='Metodo',
                           barmode='group', title='Errore medio per fase del giro'),
                    use_container_width=True)
    st.dataframe(lap_metrics, hide_index=True, use_container_width=True)
    st.download_button('Esporta predictions Q CSV', df.to_csv(index=False).encode(),
                       file_name=f'Q_predictions_{year}.csv', mime='text/csv')
    st.warning('Il confronto con il tempo reale Q è fatto solo **a posteriori**. '
               'Nessuna label Q è usata per addestrare il modello. '
               'Il miglioramento non è garantito: controlla il segno del delta.')