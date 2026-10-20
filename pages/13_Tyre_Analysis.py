"""Four-corner source telemetry; no inferred wear or setup causality."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from motorsport.analytics.channels import TYRE_FAMILIES,corner_channels,signal_unit
from motorsport.analytics.timebase import weighted_signal,chart_values
from motorsport.analytics.session_metrics import chart_sample
from motorsport_ui.telemetry import select_telemetry,time_window,metric_export

st.title('Tyre Analysis')
session=select_telemetry('tyres')
frame=time_window(session.data,'tyres_window')
family=st.selectbox('Famiglia pneumatici',list(TYRE_FAMILIES))
corners=corner_channels(frame,TYRE_FAMILIES[family])
if not corners:
    st.info('Famiglia non disponibile in questo dataset. Nessun segnale sostitutivo viene generato.')
    st.stop()
chosen=st.multiselect('Ruote',list(corners),default=list(corners))
channels=[corners[c] for c in chosen]
sample=chart_sample(frame,channels,max_points=5000)
fig=go.Figure()
for corner in chosen:
    channel=corners[corner]
    fig.add_trace(go.Scattergl(x=sample.elapsed_s if 'elapsed_s' in sample else sample.index,
                              y=chart_values(frame,sample,channel),name=f'{corner} · {signal_unit(session,channel)}',mode='lines',connectgaps=False))
fig.update_layout(template='plotly_dark',height=500,hovermode='x unified',
                  xaxis_title='Tempo sessione (s)' if 'elapsed_s' in sample else 'Campione',
                  yaxis_title='Valore riportato dalla sorgente')
st.plotly_chart(fig,width='stretch')
table=pd.DataFrame([{'corner':corner,'channel':corners[corner],'unit':signal_unit(session,corners[corner]),
                    **weighted_signal(frame,corners[corner])} for corner in chosen])
st.dataframe(table,hide_index=True,width='stretch')
metric_export(table,'tyre_metrics.csv','tyre_csv')
st.caption('FL/FR/RL/RR: anteriore sinistra/destra, posteriore sinistra/destra. '
           'I segnali sono riportati dalla sorgente; wear non viene reinterpretato come perdita di prestazione. '
           'Differenze termiche o correlazioni con i carichi non dimostrano degrado o causalità del setup.')
