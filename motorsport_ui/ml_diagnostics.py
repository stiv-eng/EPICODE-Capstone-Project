"""Optional, read-only development evidence; production reference is unchanged."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from motorsport.ml.barcelona_recovery import ROOT,file_sha
from motorsport.ml.temporal_features_v072 import FEATURE_SETS,VERSION
from motorsport_ui.hover import render_figures,render_chart


def render_development(corpus,root=ROOT):
    root=Path(root);docs=root/'docs';result_path=docs/'ML_RESULTS_V072.json'
    if not result_path.exists():
        st.info('Confronto di sviluppo non ancora disponibile. Esegui python -m scripts.run_barcelona_v072; nessun training automatico.')
        return
    try:
        results=json.loads(result_path.read_text(encoding='utf-8'))
        identity=results['compatibility']
        if identity['base_corpus_id']!=corpus.identity or identity['protocol_sha256']!=file_sha(docs/'ML_PROTOCOL_V072.json'):
            raise ValueError('Diagnostica non compatibile con corpus/protocollo attivo')
        for name,digest in results['evidence_sha256'].items():
            if file_sha(docs/name)!=digest:raise ValueError('Evidenza di sviluppo modificata: '+name)
    except (OSError,ValueError,KeyError) as exc:
        st.error('Diagnostica di sviluppo non verificata: '+str(exc));return
    st.subheader('Diagnosi ML v0.7.2 · valutazione solo sviluppo')
    st.info('Riferimento operativo: SVR v0.7.1 immutabile. Le varianti sono sperimentali; nessuna sostituzione automatica.')
    a,b,c=st.columns(3)
    a.metric('Giri di sviluppo',results['development_laps'])
    b.metric('Blocchi di sviluppo',results['development_blocks'])
    c.metric('Test storico valutato dalle varianti',results['historical_test_evaluations'])
    st.caption('103 training + 66 validation originali, cinque fold per recording; 845 prefissi correlati di 169 giri. '
               'I 36 giri del test v0.7.1 sono già osservati e restano esclusi dagli esperimenti. '
               'Questi risultati out-of-fold non sono un nuovo test indipendente.')
    chosen=results['selection']['selected_development_variant']
    st.write('Feature version: **'+VERSION+'** · variante scelta dal protocollo di sviluppo: **'+chosen+'**')
    if chosen=='F0':st.caption('Nessuna variante supera tutti i criteri preregistrati di miglioramento e protezione della coda lenta.')
    else:st.caption('Miglioramento di sviluppo conforme ai criteri preregistrati; rimane sperimentale e richiede un nuovo test intatto.')
    overall=pd.read_csv(docs/'DEVELOPMENT_OVERALL_V072.csv')
    overall['features']=overall.variant.map(lambda v:len(FEATURE_SETS[v]))
    st.dataframe(overall[['variant','features','mae_s','rmse_s','bias_s','p90_absolute_error_s',
                          'recording_macro_mae_s','prediction_to_target_std','predicted_on_actual_slope']],width='stretch')
    folds=pd.read_csv(docs/'DEVELOPMENT_FOLD_METRICS_V072.csv')
    with st.expander('Variazione tra fold e decisione sulle varianti'):
        st.dataframe(folds[['variant','fold','training_laps','validation_laps','mae_s','rmse_s','bias_s',
                            'recording_macro_mae_s']],width='stretch')
        st.dataframe(pd.DataFrame(results['selection']['decisions']),width='stretch')
    variant=st.selectbox('Variante di sviluppo',list(FEATURE_SETS),index=list(FEATURE_SETS).index(chosen),
                         key='diagnosis_v072_variant')
    st.caption('Feature della variante: '+', '.join(FEATURE_SETS[variant]))
    details=pd.read_csv(docs/'DEVELOPMENT_DETAILS_V072.csv')
    selected=details.loc[details.variant.isin({'F0',variant})]
    checkpoints=selected.query("dimension=='checkpoint_s'").copy()
    checkpoints['checkpoint_s']=pd.to_numeric(checkpoints.value)
    pace=selected.query("dimension=='pace_band'")
    predictions=pd.read_csv(docs/'DEVELOPMENT_PREDICTIONS_V072.csv')
    observed=predictions.query('variant==@variant')
    calibration=px.scatter(observed,x='target_s',y='prediction_s',color='checkpoint_s',
        title='Sviluppo out-of-fold · previsto e verificato',
        labels={'target_s':'Target verificato (s)','prediction_s':'Previsione (s)'})
    lo=min(observed.target_s.min(),observed.prediction_s.min());hi=max(observed.target_s.max(),observed.prediction_s.max())
    calibration.add_shape(type='line',x0=lo,x1=hi,y0=lo,y1=hi,line=dict(color='gray',dash='dash'))
    render_figures([
        (px.bar(overall,x='variant',y='mae_s',color='variant',title='MAE out-of-fold · stessa popolazione',
                labels={'mae_s':'MAE (s)'}),'xy'),
        (px.line(checkpoints,x='checkpoint_s',y='mae_s',color='variant',markers=True,
                 title='Errore per checkpoint · sviluppo',labels={'checkpoint_s':'Checkpoint (s)','mae_s':'MAE (s)'}),'time'),
        (px.bar(pace,x='value',y='mae_s',color='variant',barmode='group',title='Errore per fascia di passo · sviluppo',
                labels={'value':'Fascia','mae_s':'MAE (s)'}),'xy'),
        (calibration,'xy')],key='development_v072_charts')
    st.subheader('Esempi retrospettivi di sviluppo')
    examples=pd.read_csv(docs/'DEVELOPMENT_EXAMPLES_V072.csv')
    options=examples[['lap_uid','example']].drop_duplicates('lap_uid')
    labels=dict(zip(options.lap_uid,options.example))
    uid=st.selectbox('Esempio di sviluppo',list(labels),format_func=labels.get,key='diagnosis_v072_example')
    example=examples.query('lap_uid==@uid')
    target=float(example.target_s.iloc[0])
    st.caption(f'Target retrospettivo verificato: {target:.3f} s. Esempi fissati per quantili e caso difficile F0; tutte le varianti mostrate.')
    figure=px.line(example,x='checkpoint_s',y='prediction_s',color='variant',markers=True,
                   title='Previsioni ai checkpoint · esempi di sviluppo',labels={'checkpoint_s':'Checkpoint (s)','prediction_s':'Tempo finale previsto (s)'})
    figure.add_hline(y=target,line_dash='dash')
    render_chart(figure,mode='time',key='development_v072_example')
    st.caption('La pesatura F0W è una prova separata sulle feature originali: classi ricavate dai soli target di training del fold, '
               'con uguale peso per i cinque prefissi di ogni giro. Nessun giro valido è stato rimosso.')
