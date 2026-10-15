"""Nuova pagina Streamlit: si aggiunge automaticamente a un'app con directory pages/."""
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from motorsport_prediction.data import load_practice, load_qualifying
from motorsport_prediction.features import build_dataset
from motorsport_prediction.model import fit_model, replay_predictions, save_model_artifacts
from motorsport_ui.common import event_names

st.title('Dynamic Lap Time Prediction')
st.caption('Formula 1 · FastF1 · Keras · Qualifying replay')
st.write('Addestramento su FP1, FP2 e FP3 di **un solo weekend**; previsione progressiva di un giro Q.')


@st.cache_resource(show_spinner=False, max_entries=3)
def train_weekend(year, event, limit):
    practice_laps, refs, counts = load_practice(year, event, max_per_driver=limit)
    dataset = build_dataset(practice_laps, refs)
    trained = fit_model(dataset)
    return trained, refs, counts


@st.cache_resource(show_spinner=False, max_entries=3)
def get_qualifying(year, event):
    return load_qualifying(year, event)


with st.sidebar:
    st.header('Weekend F1')
    year = st.number_input('Stagione', min_value=2018, max_value=2026, value=2024, step=1)
    try:
        events = event_names(int(year))
    except Exception:
        events = []
    if events:
        initial = next((i for i, name in enumerate(events) if 'Italian Grand Prix' in name), 0)
        event = st.selectbox('Gran Premio', events, index=initial)
    else:
        event = st.text_input('GP (nome o numero round)', value='Monza')
    limit = st.slider('Giri FP per pilota e sessione', 2, 8, 3)
    st.caption('La prima esecuzione scarica i dati. In seguito FastF1 usa la cache locale.')
    do_train = st.button('Carica FP e addestra modello', type='primary', use_container_width=True)

key = (int(year), event.strip(), limit)
if not event.strip():
    st.info('Inserisci il nome del Gran Premio per proseguire.')
    st.stop()

if do_train:
    try:
        with st.spinner('Acquisizione FP1/FP2/FP3, preprocessing e training...'):
            trained, refs, counts = train_weekend(*key)
        st.session_state['lap_pred_training_key'] = key
        st.session_state['lap_pred_training'] = (trained, refs, counts)
    except Exception as exc:
        st.error(f'Non è stato possibile addestrare il modello: {exc}')

if st.session_state.get('lap_pred_training_key') != key:
    st.info('Seleziona un weekend e premi **Carica FP e addestra modello** per iniziare.')
    st.stop()

trained, references, counts = st.session_state['lap_pred_training']
a, b, c = st.columns(3)
a.metric('MAE baseline · validazione FP', f"{trained.metrics['validation_baseline_mae_s']:.2f} s")
b.metric('MAE Keras · validazione FP', f"{trained.metrics['validation_keras_mae_s']:.2f} s")
c.metric('Giri train / validazione', f"{trained.metrics['train_laps']} / {trained.metrics['validation_laps']}")
st.caption('Metriche mediate sugli snapshot FP di validazione, separati per giro dal train. '
           'Non sono misure di accuratezza in qualifica.')
with st.expander('Dataset e training'):
    st.write('Giri FP caricati:', counts)
    st.write('Correzione residua con MLP Keras (64 → 32 → 1), StandardScaler e OneHotEncoder.')
    st.write('MAE macro FP su giri completi: baseline',
             f"{trained.metrics['validation_macro_baseline_mae_s']:.3f} s",
             ' · Keras', f"{trained.metrics['validation_macro_keras_mae_s']:.3f} s")
    history = pd.DataFrame(trained.history)
    if not history.empty:
        st.line_chart(history[['loss', 'val_loss']], x_label='Epoch', y_label='Huber loss')
    safe_event = re.sub(r'[^a-zA-Z0-9_-]+', '_', event.strip())
    if st.button('Salva modello e preprocessing sul PC/server'):
        location = f'artifacts/{year}_{safe_event}'
        save_model_artifacts(trained, location, {'year': int(year), 'event': event})
        st.success(f'Artefatti salvati in {location}')

st.subheader('Replay di un giro di qualifica')
try:
    with st.spinner('Caricamento giri Q...'):
        q_laps = get_qualifying(int(year), event.strip())
except Exception as exc:
    st.warning(f'Dati qualifica non disponibili: {exc}')
    st.stop()

eligible = [lap for lap in q_laps if lap.driver in references]
if not eligible:
    st.warning('Nessun giro Q con un riferimento FP3 valido dello stesso pilota.')
    st.stop()

pilots = sorted(set(lap.driver for lap in eligible))
driver = st.selectbox('Pilota', pilots)
choices = [lap for lap in eligible if lap.driver == driver]
labels = {lap.uid: f'Lap {lap.lap_number} · {lap.lap_time_s:.3f} s · {lap.compound}' for lap in choices}
chosen_uid = st.selectbox('Giro di qualifica', list(labels), format_func=lambda u: labels[u])
chosen = next(lap for lap in choices if lap.uid == chosen_uid)
reference = references[driver]
trace = replay_predictions(chosen, reference, trained)
st.caption(f'Riferimento: {driver}, miglior giro FP3: {reference.lap_time_s:.3f} s. '
           'La previsione evolve solo in base alla telemetria osservata fino al punto selezionato.')

replay_key = (key, chosen_uid)
if st.session_state.get('lap_pred_replay_key') != replay_key:
    st.session_state['lap_pred_replay_key'] = replay_key
    st.session_state['lap_pred_index'] = 0
    st.session_state['lap_pred_autoplay'] = False


@st.fragment(run_every='0.8s')
def replay():
    n = len(trace)
    # Lo stato di un widget si puo' modificare solo prima di renderizzarlo.
    if st.session_state['lap_pred_index'] >= n-1:
        st.session_state['lap_pred_autoplay'] = False
    cols = st.columns([1, 2, 1])
    with cols[0]:
        if st.button('◀ Indietro', disabled=st.session_state['lap_pred_index'] == 0):
            st.session_state['lap_pred_index'] -= 1
    with cols[1]:
        st.toggle('Riproduzione automatica', key='lap_pred_autoplay')
    with cols[2]:
        if st.button('Avanti ▶', disabled=st.session_state['lap_pred_index'] == n-1):
            st.session_state['lap_pred_index'] += 1
    if st.session_state['lap_pred_autoplay']:
        if st.session_state['lap_pred_index'] < n-1:
            st.session_state['lap_pred_index'] += 1
    index = st.slider('Punto osservato del giro', min_value=0, max_value=n-1,
                      key='lap_pred_index', format='%d')
    current = trace.iloc[index]
    finished = bool(current['is_finish'])
    m1, m2, m3 = st.columns(3)
    m1.metric('Completamento', f"{current['progress']*100:.0f}%")
    m2.metric('Tempo finale previsto', f"{current['prediction_s']:.3f} s")
    m3.metric('Delta da FP3 baseline', f"{current['prediction_s'] - reference.lap_time_s:+.3f} s")
    if finished:
        st.success(f'Giro completato: tempo effettivo {chosen.lap_time_s:.3f} s · '
                   f'ultimo aggiornamento = tempo reale del giro.')
    displayed = trace.iloc[:index+1]
    fig = go.Figure()
    fig.add_scatter(x=displayed['progress']*100, y=displayed['prediction_s'],
                    name='Keras + baseline', mode='lines+markers')
    fig.add_scatter(x=displayed['progress']*100, y=displayed['baseline_s'],
                    name='Baseline FP3', mode='lines', line={'dash': 'dot'})
    if finished:
        fig.add_hline(y=chosen.lap_time_s, line_dash='dash',
                      annotation_text='Tempo Q finale')
    fig.update_layout(title='Evoluzione tempo finale stimato',
                      xaxis_title='Giro completato (%)', yaxis_title='Tempo (s)',
                      legend={'orientation': 'h', 'y': -0.3}, margin={'t': 40, 'b': 40})
    st.plotly_chart(fig, use_container_width=True)
    telemetry = chosen.telemetry
    shown = telemetry.loc[telemetry['elapsed_s'] <= current['elapsed_s']]
    tv = go.Figure()
    tv.add_scatter(x=shown['distance_m'], y=shown['Speed'], mode='lines', name='Speed Q')
    tv.update_layout(title='Telemetria visibile fino allo snapshot',
                     xaxis_title='Distanza percorsa (m)', yaxis_title='Velocità (km/h)',
                     margin={'t': 40, 'b': 40})
    st.plotly_chart(tv, use_container_width=True)

replay()