"""Causal model fitting is an explicit action; ordinary page visits are offline."""
import pandas as pd
import plotly.express as px
import streamlit as st

from motorsport.ml.features import FEATURES,retrospective_features
from motorsport.ml.training import train,EXPERIMENTAL
from motorsport.ml.artifacts import LocalArtifactStore
from motorsport_ui.ml import ROOT,select_corpus,show_eligibility,snapshot_table,get_bundle,display_table

st.title('Machine Learning')
st.caption('v0.6 · Feature causali e valutazione su giri e sessioni separati')
corpus=select_corpus('training')
gate=show_eligibility(corpus)
if not corpus.laps:
    st.info('Nessun giro con target verificato: il dataset rimane esplorabile nelle pagine di telemetria.')
    st.stop()
st.caption(corpus.name)
table,rejections=snapshot_table(corpus)
st.write(f'{len(table)} snapshot accettati · {len(rejections)} checkpoint esclusi · {len(corpus.exclusions)} esclusioni di sorgenti/giri')
with st.expander('Provenienza, esclusioni e qualità degli snapshot'):
    st.dataframe(display_table(corpus.targets),width='stretch')
    if corpus.exclusions:st.dataframe(pd.DataFrame(corpus.exclusions),width='stretch')
    if not rejections.empty:st.dataframe(rejections,width='stretch')
    st.download_button('Esporta snapshot con target e provenienza',table.to_csv(index=False).encode(),
                       'causal_snapshots_v06.csv','text/csv')
available=[name for name in FEATURES if not table.empty and table[name].notna().any()]
features=st.multiselect('Feature causali',list(FEATURES),default=available)
st.caption('Statistiche calcolate soltanto entro 10, 20, 30, 45 e 60 s. Attività sterzo disponibile solo con gradi dichiarati. '
           'Le feature selezionate e il preprocessing rimangono fissi dopo il training.')
single=gate['physical_sessions']==1 and len(corpus.laps)>=6
experimental=False
if not gate['eligible'] and single:
    st.warning(EXPERIMENTAL)
    experimental=st.checkbox('Abilita caso di studio sperimentale',value=False)
can_train=bool(features) and (gate['eligible'] or experimental)
if st.button('Addestra e valuta i tre modelli',disabled=not can_train,type='primary'):
    try:
        with st.spinner('Training separato da validazione e test…'):
            bundle=train(corpus,features,experimental=experimental)
            st.session_state.setdefault('ml_bundles',{})[corpus.identity]=bundle
    except ValueError as exc:
        st.error(str(exc))
bundle=get_bundle(corpus)
if bundle is not None:
    st.subheader('Risultati delle partizioni indipendenti')
    st.info(bundle.mode)
    st.write('Modello selezionato esclusivamente dalla validazione: **'+bundle.selected_model+'**')
    st.caption('Nessun refit su validazione/test. I prefissi di un giro restano nella stessa partizione. '
               'I riferimenti storici usano soltanto target di training già conclusi prima del giro corrente.')
    st.dataframe(bundle.split,width='stretch')
    st.write('Feature usate dal bundle: '+', '.join(bundle.feature_names))
    partition=st.radio('Partizione di valutazione',['test','validation'],horizontal=True)
    st.dataframe(bundle.reports['overall'].query('partition==@partition'),width='stretch')
    st.subheader('Confronto con baseline sullo stesso insieme di snapshot')
    st.dataframe(bundle.reports['baselines'].query('partition==@partition'),width='stretch')
    model=st.selectbox('Modello da ispezionare',list(bundle.models),index=list(bundle.models).index(bundle.selected_model))
    result=bundle.predictions.query('partition==@partition and model==@model')
    if not result.empty:
        left,right=st.columns(2)
        left.plotly_chart(px.scatter(result,x='target_s',y='prediction_s',color='checkpoint_s',hover_data=['lap_uid'],
            labels={'target_s':'Tempo verificato (s)','prediction_s':'Tempo previsto (s)'},title='Previsto e verificato'),width='stretch')
        right.plotly_chart(px.histogram(result,x='error_s',nbins=15,title='Distribuzione errori · previsto − verificato (s)'),width='stretch')
    for label,key in [('Errori per checkpoint','by_checkpoint'),('Errori per giro completo','by_lap'),('Errori per sessione fisica','by_session')]:
        with st.expander(label):
            st.dataframe(bundle.reports[key].query('partition==@partition and model==@model'),width='stretch')
    with st.expander('Errori individuali e copertura'):
        st.dataframe(result[['lap_uid','physical_session_id','checkpoint_s','target_s','prediction_s','error_s']],width='stretch')
    st.subheader('Importanza delle feature sulla validazione')
    if bundle.importance.empty:
        st.info('Importanza non stimata: meno di cinque giri di validazione.')
    else:
        importance=bundle.importance.query('model==@model').sort_values('mae_increase_s')
        st.plotly_chart(px.bar(importance,x='mae_increase_s',y='feature',orientation='h',
            title='Aumento MAE dopo permutazione · 3 ripetizioni'),width='stretch')
        st.caption('Diagnostica descrittiva con prefissi correlati; non è una misura di causalità fisica né una prova statistica.')
    if st.button('Salva bundle locale verificabile'):
        path=LocalArtifactStore(ROOT/'artifacts/models').save(bundle,'telemetry-'+corpus.identity[:16])
        st.success('Bundle e preprocessing salvati in '+str(path.relative_to(ROOT)))
    st.download_button('Esporta errori indipendenti CSV',bundle.predictions.to_csv(index=False).encode(),
                       'ml_errors_v06.csv','text/csv')
else:
    st.info('Nessun modello addestrato per questo corpus. Il training parte soltanto dal pulsante esplicito.')
with st.expander('Analisi descrittiva retrospettiva dei giri completi'):
    st.caption('Usa il giro completo: queste colonne non entrano nei modelli progressivi.')
    st.dataframe(display_table(retrospective_features(corpus)),width='stretch')
