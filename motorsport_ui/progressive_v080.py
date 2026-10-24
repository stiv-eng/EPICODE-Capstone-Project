"""Opt-in target-hidden experimental replay; never fits a model on a rerun."""
import json
import importlib.util
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from motorsport.ml.barcelona_recovery import ROOT, file_sha
from motorsport.ml.dense_experiment_v080 import load_fold, predict, MODEL_ROOT, CANDIDATES
from motorsport.ml.progression_v080 import checkpoints
from motorsport.ml.features import FEATURES, prefix_features, causal_prefix
from motorsport_ui.hover import render_figures, observed_tolerance


@st.cache_resource(show_spinner=False)
def cached_fold(binding_json, fold, with_gru, artifact_stamp, root=str(MODEL_ROOT)):
    return load_fold(json.loads(binding_json), fold, Path(root), with_gru=with_gru)


@st.cache_data(show_spinner=False)
def evidence(result_stamp):
    result = json.loads((ROOT/'docs/ML_RESULTS_V080.json').read_text(encoding='utf-8'))
    for name, sha in result['evidence_sha256'].items():
        if file_sha(ROOT/'docs'/name) != sha:
            raise ValueError('Risultati sperimentali modificati: '+name)
    overall = pd.read_csv(ROOT/'docs/DEVELOPMENT_OVERALL_V080.csv')
    details = pd.read_csv(ROOT/'docs/DEVELOPMENT_DETAILS_V080.csv')
    folds = pd.read_csv(ROOT/'docs/DEVELOPMENT_FOLDS_V080.csv')
    return result, overall, details, folds


def render(corpus, reference):
    st.caption('Sperimentale v0.8 · checkpoint in secondi · replay OOF sui soli giri di sviluppo')
    path = ROOT/'docs/ML_RESULTS_V080.json'
    if not path.exists():
        st.info('Esperimenti non installati. Esegui esplicitamente python -m scripts.run_barcelona_v080; nessun training automatico.')
        return
    try:
        result, overall, details, folds = evidence((path.stat().st_mtime_ns, path.stat().st_size))
        binding = result['compatibility']
        if corpus.identity != binding['base_corpus_id']:
            raise ValueError('Il corpus non coincide con gli artefatti v0.8')
        sources = {lap.lap_uid:lap for lap in corpus.laps if lap.lap_uid in set(folds.lap_uid)}
        uid = st.selectbox('Giro di sviluppo', list(sources), format_func=lambda key:
            sources[key].physical_session_id+' · '+key[-14:], key='v080_lap')
        source = sources[uid]
        fold = int(folds.set_index('lap_uid').loc[uid, 'fold'])
        artifact = MODEL_ROOT/f'dense-v080-{fold}.joblib'
        stamp = (artifact.stat().st_mtime_ns, artifact.stat().st_size)
        bundle, _ = cached_fold(json.dumps(binding, sort_keys=True), fold, False, stamp)
    except (OSError, ValueError, KeyError) as exc:
        st.info('Artefatti sperimentali compatibili non disponibili: '+str(exc))
        return
    st.info('Confronto esplorativo sui 169 giri / 40 blocchi. Il giro selezionato è escluso dal training del fold. '
            'Il riferimento operativo resta SVR v0.7.1; il test storico non è riutilizzato.')
    summary = overall.query("subset=='all'")[['model', 'mae_s', 'recording_macro_mae_s']].copy()
    summary['target'] = summary.model.map(lambda m:'finale diretto' if m in ('SVR-SPARSE', 'SVR-DENSE', 'MEDIAN') else 'tempo rimanente')
    summary['training'] = 'fold v072 · sviluppo · escluso il blocco corrente'
    summary['checkpoint'] = '5 s, prefisso osservato, pesi per giro'
    summary['stato'] = 'Sperimentale · OOF'
    st.dataframe(summary, hide_index=True, width='stretch')
    with st.expander('Errori per fascia di passo e identità del training'):
        st.dataframe(details.query("dimension=='pace_band'")[['model', 'value', 'laps', 'mae_s', 'bias_s']],
                     hide_index=True, width='stretch')
        st.caption('Identità sviluppo: '+binding['development_corpus_id']+' · fold '+str(fold))
        st.caption('MAE complessivo con uguale peso per giro; i checkpoint tardivi hanno meno giri ancora in corso. '
                   'I risultati OOF non sono una nuova misura su dati indipendenti.')
    available = list(CANDIDATES)
    gru_path = MODEL_ROOT/f'dense-v080-{fold}.keras'
    if (not gru_path.exists() or file_sha(gru_path) != bundle.compatibility['gru_sha256']
            or importlib.util.find_spec('keras') is None or importlib.util.find_spec('torch') is None):
        available.remove('GRU')
    if reference is not None:
        available.insert(0, 'SVR v0.7.1')
    selected = st.multiselect('Modelli sperimentali da confrontare', available,
        default=['SVR-REMAINING', 'REMAINING-REFERENCE'], key='v080_models')
    cadence = st.selectbox('Cadenza causale', ['5 secondi', '10 secondi', '15 secondi', 'Compatibilità 10/20/30/45/60 s'], key='v080_cadence')
    points = checkpoints(source, cadence_s=float(cadence.split()[0]) if cadence[0].isdigit() else 5.,
                         compatibility=cadence.startswith('Compatibilità'))
    if not points:
        st.info('Nessun checkpoint causale supportato.')
        return
    checkpoint = st.select_slider('Checkpoint sperimentale (s)', options=points, value=points[0], key='v080_checkpoint')
    gru = None
    if 'GRU' in selected:
        try:
            _, gru = cached_fold(json.dumps(binding, sort_keys=True), fold, True,
                                 stamp+(gru_path.stat().st_mtime_ns, gru_path.stat().st_size))
        except (OSError, ValueError, ImportError) as exc:
            st.info('GRU non disponibile: '+str(exc))
            selected = [name for name in selected if name != 'GRU']
    rows = []
    for current in points:
        if current > checkpoint:
            break
        for model in selected:
            if model == 'SVR v0.7.1':
                features, q = prefix_features(source, current)
                p = float(reference.models['SVR'].predict(pd.DataFrame([features], columns=FEATURES))[0])
                rows.append(dict(checkpoint_s=current, observed_elapsed_s=q['observed_elapsed_s'], prediction_s=p,
                    raw_remaining_s=p-q['observed_elapsed_s'], projected=False, reference_support=None, model=model))
            else:
                rows.append(predict(source, current, bundle, model, gru=gru))
    if 'SVR v0.7.1' in selected:
        partition = reference.split.set_index('lap_uid').loc[uid, 'partition']
        st.caption('SVR v0.7.1 fisso · partizione originale: '+partition+
                   '. Le sue previsioni sul training sono in-sample; i punteggi OOF appartengono a SVR-SPARSE rifittato per fold.')
    frame, quality = causal_prefix(source, checkpoint)
    st.metric('Tempo osservato sperimentale', f"{quality['observed_elapsed_s']:.3f} s")
    st.caption('Tempo effettivo dell’ultimo campione disponibile; nessuna percentuale calcolata dalla durata finale.')
    # No corpus targets, pace labels, final durations or evaluation rows enter
    # these figures or the target-free inference calls above.
    signals = frame[['lap_elapsed_s', 'speed_kmh', 'throttle_pct', 'brake_pct']]
    signal_plot = px.line(signals.iloc[::max(1, len(signals)//3000)], x='lap_elapsed_s',
        y=['speed_kmh', 'throttle_pct', 'brake_pct'], title='Segnali osservati · confronto sperimentale')
    for trace in signal_plot.data:
        trace.update(meta=dict(unit='km/h' if trace.name == 'speed_kmh' else '%', tolerance=observed_tolerance(signals.lap_elapsed_s)))
    figures = [(signal_plot, 'time')]
    history = pd.DataFrame(rows)
    if len(history):
        plot = px.line(history, x='observed_elapsed_s', y='prediction_s', color='model', markers=True,
                       title='Previsioni finali disponibili · secondi osservati')
        for trace in plot.data:
            trace.update(meta=dict(unit='s'))
        figures.append((plot, 'time'))
    render_figures(figures, key='experimental_replay_v080')
    st.dataframe(history, hide_index=True, width='stretch')
    if len(history) and history.projected.any():
        st.caption('Proiezione esplicita: i valori rimanenti negativi sono portati a zero; valori grezzi visibili in tabella.')
    if st.checkbox('Rivela risultato retrospettivo sperimentale', value=False, key='v080_reveal'):
        target = float(corpus.targets.set_index('lap_uid').loc[uid, 'target_s'])
        st.metric('Risultato finale verificato', f'{target:.3f} s')
        if len(history):
            errors = history.groupby('model', sort=False).tail(1)[['model', 'prediction_s']].copy()
            errors['errore_s'] = errors.prediction_s-target
            st.dataframe(errors, hide_index=True, width='stretch')
        st.caption('Valutazione retrospettiva rivelata dopo la previsione. Il target non modifica grafici o input.')
