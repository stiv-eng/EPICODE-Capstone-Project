"""Essential session information; full-resolution observed-time means preserved."""
import pandas as pd
import streamlit as st
from motorsport.analytics.overview import overview_metrics
from motorsport_ui.telemetry import select_telemetry, quality_caption, metric_export, unavailable_capabilities, render_unavailable

st.title('Session Overview')
session=select_telemetry('overview')
summary=overview_metrics(session.data)
clock=summary['time']
a,b,c,d=st.columns(4)
a.metric('Tempo registrato',f"{clock['span_s']:.2f} s" if clock['span_s'] is not None else 'N/D')
b.metric('Tempo osservato',f"{clock['observed_s']:.2f} s")
c.metric('Campioni tempo/velocita validi',f"{summary['valid_time_speed_samples']:,}")
rate=session.quality.get('time') or {}
d.metric('Frequenza osservata',f"{rate['observed_rate_hz']:.2f} Hz" if rate.get('observed_rate_hz') else 'N/D')
quality_caption(session.data)
table=pd.DataFrame([{'Channel':channel,'Time Measured [s]':stats['covered_s'],'Mean':stats['time_mean']}
                    for channel,stats in summary['signals'].items()],columns=['Channel','Time Measured [s]','Mean'])
st.subheader('Statistiche dei segnali')
st.dataframe(table,hide_index=True,width='stretch')
st.caption('Mean: media pesata sul tempo valido misurato, mantenendo il campione precedente negli intervalli osservati. Lacune e ultimo campione senza durata non aggiungono peso.')
metric_export(table,'session_metrics.csv','overview_csv')
unavailable=unavailable_capabilities(session)
if not unavailable.empty:
    st.subheader('Funzioni non disponibili')
    render_unavailable(session)
st.caption('Input, distribuzioni e segnali dettagliati sono disponibili in Data Explorer.')
