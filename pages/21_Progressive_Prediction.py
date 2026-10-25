"""Interactive retrospective replay with an explicit hidden-target boundary."""
from dataclasses import asdict

import pandas as pd
import plotly.express as px
import streamlit as st
from motorsport_ui.hover import render_figures

from motorsport.ml.features import CHECKPOINTS,prefix_features,causal_prefix
from motorsport.ml.inference import predict,retrospective_error
from motorsport_ui.ml import select_corpus,show_eligibility,get_bundle,baseline_history,barcelona_active

st.title('Progressive Prediction')
st.caption('Replay retrospettivo locale · nessuna connessione live al simulatore')
if barcelona_active():st.caption('Riferimento operativo: SVR v0.7.1 · feature causal-prefix-v06.')
corpus=select_corpus('replay')
gate=show_eligibility(corpus)
if not corpus.laps:
    st.info('Il replay richiede giri completi con target verificati.')
    st.stop()
bundle=get_bundle(corpus)
if barcelona_active():
    replay_mode=st.radio('Modalità di previsione', ['Riferimento operativo', 'Confronto sperimentale v0.8', 'Replay frequente v0.8.1'],
                         index=0, key='progressive_mode')
    if replay_mode=='Replay frequente v0.8.1':
        from motorsport_ui.progressive_v081 import render
        render(corpus)
        st.stop()
    if replay_mode=='Confronto sperimentale v0.8':
        from motorsport_ui.progressive_v080 import render
        render(corpus,bundle)
        st.stop()
history=baseline_history(corpus,bundle)
ids={lap.lap_uid:lap for lap in corpus.laps}
labels={lap.lap_uid:f'{lap.physical_session_id} · giro {lap.lap_uid.split(":lap:")[-1]}' for lap in corpus.laps}
if bundle is not None:
    test_ids=set(bundle.split.query("partition=='test'").lap_uid)
    default=next((i for i,lap in enumerate(corpus.laps) if lap.lap_uid in test_ids),0)
else:
    default=len(corpus.laps)-1
uid=st.selectbox('Giro validato',list(ids),index=default,format_func=labels.get)
source=ids[uid]
if barcelona_active():
    from motorsport.ml.barcelona_recovery import predict
    st.caption('Mediana fissata sui giri di training: riferimento offline, senza aggiornamenti dai target di validazione/test.')
options=['Baseline-only']+(([bundle.selected_model] if barcelona_active() else list(bundle.models)) if bundle is not None else [])
choice=st.selectbox('Motore di previsione',options,index=options.index(bundle.selected_model) if bundle is not None else 0)
model=None if choice=='Baseline-only' else bundle.models[choice]
mode='Baseline-only · riferimenti di training precedenti' if model is None else bundle.mode
st.info(mode)
if barcelona_active() and bundle is None:
    st.info('Modello Barcelona non disponibile: replay dei soli segnali osservati. Nessuna previsione o baseline di training viene fabbricata.')
partition=None
if bundle is not None:
    partition=bundle.split.set_index('lap_uid').loc[uid,'partition']
    st.caption('Partizione del giro: '+partition)
    if partition=='train' and model is not None:
        st.warning('Giro usato nel training: questo replay non è una valutazione indipendente.')
checkpoints=[]
for checkpoint in CHECKPOINTS:
    try:
        prefix_features(source,checkpoint)
        checkpoints.append(checkpoint)
    except ValueError:
        pass
if not checkpoints:
    st.warning('Nessun checkpoint con copertura causale sufficiente.')
    st.stop()
checkpoint=st.select_slider('Checkpoint trascorso (s)',options=checkpoints,value=checkpoints[0])
predictions=[]
for current in checkpoints:
    if current>checkpoint:break
    options_v071={'date_reliability':bundle.date_reliability if bundle is not None else {}} if barcelona_active() else {}
    predictions.append(predict(source,current,model,bundle.feature_names if model is not None else (),history,
        model_domain=bundle.domain if model is not None else None,**options_v071))
current=predictions[-1]
a,b,c=st.columns(3)
a.metric('Tempo osservato',f'{current.observed_elapsed_s:.3f} s')
b.metric('Tempo finale previsto','Non disponibile' if current.predicted_final_s is None else f'{current.predicted_final_s:.3f} s')
c.metric('Baseline mediana storica','Non disponibile' if current.baseline_s is None else f'{current.baseline_s:.3f} s')
if current.baseline_s is None:st.caption('Nessun giro precedente comparabile consentito per il riferimento storico.')
prefix,quality=causal_prefix(source,checkpoint)
st.caption(f"Qualità: {quality['status']} · copertura segnali {quality['min_core_coverage']:.1%} · "
           f"{quality['samples']} campioni osservati. Nessuna distanza finale usata.")
signals=prefix[['lap_elapsed_s','speed_kmh','throttle_pct','brake_pct']].copy()
# Rendering is bounded; calculations above use every observed export sample.
stride=max(1,len(signals)//3000)
signals_figure=px.line(signals.iloc[::stride],x='lap_elapsed_s',y=['speed_kmh','throttle_pct','brake_pct'],
    labels={'lap_elapsed_s':'Tempo osservato del giro (s)'},title='Velocità (km/h) e input (%) osservati fino al checkpoint')
history_frame=pd.DataFrame([asdict(p) for p in predictions]).drop(columns='quality')
history_figure=px.line(history_frame,x='checkpoint_s',y=['predicted_final_s','baseline_s'],markers=True,
    title='Storia delle previsioni disponibili (s)')
# Only causal prefix and predictions enter this component. No full-lap target,
# source telemetry tail or corpus table is serialized into the browser payload.
from motorsport_ui.hover import observed_tolerance
for trace in signals_figure.data:
    trace.update(meta=dict(unit='km/h' if trace.name=='speed_kmh' else '%',
                           tolerance=observed_tolerance(signals.lap_elapsed_s)))
for trace in history_figure.data:trace.update(meta=dict(unit='s'))
figures=[(signals_figure,'time')]
if history_frame[['predicted_final_s','baseline_s']].notna().any().any():figures.append((history_figure,'time'))
render_figures(figures,key='replay_charts')
st.dataframe(history_frame,width='stretch')
if st.checkbox('Mostra valutazione retrospettiva e risultato finale',value=False):
    target=float(corpus.targets.set_index('lap_uid').loc[uid,'target_s'])
    error=retrospective_error(current,target)
    st.metric('Risultato finale verificato',f'{target:.3f} s')
    st.metric('Errore previsto − verificato','Non disponibile' if error is None else f'{error:+.3f} s')
    st.caption('Target rivelato su richiesta soltanto dopo la previsione. Fonte: '+
               corpus.targets.set_index('lap_uid').loc[uid,'target_source'])
    if partition=='train':st.warning('Errore sul training; non misura prestazioni indipendenti.')
