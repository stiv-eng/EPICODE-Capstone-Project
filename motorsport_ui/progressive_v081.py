"""High-frequency recorded replay with per-session causal inference caches."""
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from motorsport.ml.barcelona_recovery import ROOT
from motorsport.ml.dense_experiment_v080 import MODEL_ROOT
from motorsport.ml.replay_v081 import ReplayEngine, advance_checkpoint
from motorsport_ui.progressive_v080 import cached_fold, evidence
from motorsport_ui.hover import render_figures, observed_tolerance


def _stamp(path):
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


@st.cache_data(show_spinner=False)
def runtime_evidence(stamp):
    return json.loads((ROOT/'docs/ML_RESULTS_V081.json').read_text(encoding='utf-8'))


def render(corpus):
    st.caption('Sperimentale v0.8.1 · SVR-DENSE v0.8 · replay di telemetria registrata, timer sorgente')
    path = ROOT/'docs/ML_RESULTS_V080.json'
    if not path.exists():
        st.info('Artefatti SVR-DENSE v0.8 non installati. Nessun training automatico.')
        return
    try:
        result, _, _, folds = evidence(_stamp(path))
        binding = result['compatibility']
        if corpus.identity != binding['base_corpus_id']:
            raise ValueError('Corpus incompatibile con il modello sperimentale')
        allowed = set(folds.lap_uid)
        sources = {lap.lap_uid:lap for lap in corpus.laps if lap.lap_uid in allowed}
        uid = st.selectbox('Giro di sviluppo v0.8.1', list(sources), key='v081_lap',
            format_func=lambda key:sources[key].physical_session_id+' · '+key[-14:])
        source = sources[uid]
        fold = int(folds.set_index('lap_uid').loc[uid, 'fold'])
        artifact = MODEL_ROOT/f'dense-v080-{fold}.joblib'
        stamp = (*_stamp(artifact), *_stamp(artifact.with_suffix('.json')), *_stamp(MODEL_ROOT/'.local-signing-key'))
        bundle, _ = cached_fold(json.dumps(binding, sort_keys=True), fold, False, stamp)
    except (OSError, ValueError, KeyError) as exc:
        st.info('Artefatti sperimentali compatibili non disponibili: '+str(exc))
        return
    st.info('SVR-DENSE sperimentale, addestrato ogni 5 s. Fold '+str(fold)+
            ': il blocco selezionato è escluso dal training. Correzioni fisiche e di arresto deterministiche, '
            'separate dal modello. Riferimento operativo: SVR v0.7.1.')
    intervals = ['1 secondo', '5 secondi']
    runtime_path = ROOT/'docs/ML_RESULTS_V081.json'
    if runtime_path.exists() and runtime_evidence(_stamp(runtime_path)).get('half_second_supported', False):
        intervals.append('0.5 secondi')
    cadence_label = st.selectbox('Intervallo aggiornamenti v0.8.1', intervals, key='v081_cadence')
    cadence = float(cadence_label.split()[0])
    signature = (uid, stamp, cadence)
    if st.session_state.get('v081_engine_signature') != signature:
        st.session_state['v081_engine'] = ReplayEngine(source, bundle)
        st.session_state['v081_engine_signature'] = signature
        st.session_state.pop('v081_checkpoint', None)
        st.session_state['v081_playing'] = False
        st.session_state['v081_reveal'] = False
    engine = st.session_state['v081_engine']
    points = engine.index.schedule(cadence)
    if not points:
        st.info('Nessun checkpoint con osservazioni valide e recenti.')
        return
    st.caption('Arresto: ≤2 km/h per 1 s osservato. Ripartenza: ≥4 km/h per 0,3 s. '
               'Una pausa del replay non aggiunge tempo al giro. Nessuna connessione live al simulatore.')
    selected = st.multiselect('Stime da confrontare', ['SVR grezzo', 'Vincolo fisico', 'Stop-aware'],
        default=['Vincolo fisico', 'Stop-aware'], key='v081_estimates')
    playing = st.toggle('Riproduci registrazione', value=False, key='v081_playing')
    at_end = st.session_state.get('v081_checkpoint') == points[-1]

    @st.fragment(run_every=cadence if playing and not at_end else None)
    def replay_fragment():
        current = st.session_state.get('v081_checkpoint', points[0])
        if playing:
            st.session_state['v081_checkpoint'] = advance_checkpoint(points, current, True)
        checkpoint = st.select_slider('Checkpoint registrato (s)', points, value=points[0], key='v081_checkpoint')
        # Rewinds and selection changes get isolated state. Previously calculated
        # rows may be reused because they were computed before their own cutoff.
        session_engine = st.session_state['v081_engine']
        if checkpoint < max(session_engine.rows, default=0.) and checkpoint not in session_engine.rows:
            session_engine = ReplayEngine(source, bundle)
            st.session_state['v081_engine'] = session_engine
        for t in points:
            if t > checkpoint:
                break
            session_engine.predict(t)
        current_row = session_engine.rows[checkpoint]
        history = pd.DataFrame([session_engine.rows[t] for t in points if t <= checkpoint])
        a, b, c = st.columns(3)
        a.metric('Tempo osservato v0.8.1', f"{current_row['observed_elapsed_s']:.3f} s")
        b.metric('Tempo finale previsto · stop-aware', f"{current_row['stop_aware_prediction_s']:.3f} s")
        c.metric('Velocità corrente', f"{current_row['speed_kmh']:.1f} km/h")
        st.caption(f"Checkpoint nominale {checkpoint:g} s · campione osservato {current_row['observed_elapsed_s']:.3f} s · "
                   f"età campione {current_row['sample_age_s']*1000:.1f} ms · stato {current_row['driving_state']}")
        if current_row['bound_active']:
            st.caption(f"Vincolo fisico attivo: +{current_row['bound_adjustment_s']:.3f} s rispetto al grezzo.")
        columns = {'SVR grezzo':'raw_prediction_s', 'Vincolo fisico':'bounded_prediction_s', 'Stop-aware':'stop_aware_prediction_s'}
        payload = history[['observed_elapsed_s', *[columns[s] for s in selected]]].rename(columns={v:k for k,v in columns.items()})
        figures = []
        if selected:
            plot = px.line(payload, x='observed_elapsed_s', y=selected,
                labels={'observed_elapsed_s':'Tempo osservato (s)', 'value':'Tempo finale stimato (s)', 'variable':'Stima'},
                title='SVR-DENSE · stima finale e correzioni causali')
            for trace in plot.data:
                trace.update(meta=dict(unit='s'))
            figures.append((plot, 'time'))
        signals = source.frame.iloc[:session_engine.index.position(checkpoint)+1][['lap_elapsed_s', 'speed_kmh', 'throttle_pct', 'brake_pct']]
        signal_plot = px.line(signals.iloc[::max(1, len(signals)//1500)], x='lap_elapsed_s',
            y=['speed_kmh', 'throttle_pct', 'brake_pct'], title='Segnali sorgente osservati')
        for trace in signal_plot.data:
            trace.update(meta=dict(unit='km/h' if trace.name == 'speed_kmh' else '%',
                                   tolerance=observed_tolerance(signals.lap_elapsed_s)))
        figures.append((signal_plot, 'time'))
        render_figures(figures, key='experimental_replay_v081')
        with st.expander('Valori grezzi e correzioni'):
            st.dataframe(history, hide_index=True, width='stretch')
        if session_engine.index.clock_interrupted and checkpoint == points[-1]:
            st.warning('Replay interrotto: discontinuità del clock sorgente; stato successivo incerto. Nessun arresto dedotto dal vuoto.')
        st.caption(f"Inferenze SVR memorizzate nella sessione: {session_engine.model_calls}. "
                   'Hover e cursore operano nel browser senza ricalcolare le previsioni.')
        if st.checkbox('Rivela risultato retrospettivo v0.8.1', value=False, key='v081_reveal'):
            target = float(corpus.targets.set_index('lap_uid').loc[uid, 'target_s'])
            st.metric('Risultato finale verificato', f'{target:.3f} s')
            st.metric('Errore stop-aware retrospettivo', f"{current_row['stop_aware_prediction_s']-target:+.3f} s")
        if playing and checkpoint == points[-1] and not at_end:
            st.rerun()

    replay_fragment()
