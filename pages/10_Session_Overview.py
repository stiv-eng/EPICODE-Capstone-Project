"""Session overview with separate sample and observed-time statistics."""
import pandas as pd
import plotly.express as px
import streamlit as st

from motorsport.analytics.overview import overview_metrics,gear_distribution
from motorsport.analytics.driver_inputs import driver_metrics
from motorsport.analytics.readiness import lap_features
from motorsport_ui.telemetry import select_telemetry,quality_caption,signal_chart,metric_export,capability_table

st.title('Session Overview')
session=select_telemetry('overview')
frame=session.data
summary=overview_metrics(frame)
clock=summary['time']
a,b,c,d=st.columns(4)
a.metric('Tempo registrato',f"{clock['span_s']:.2f} s" if clock['span_s'] is not None else 'N/D')
b.metric('Tempo osservato',f"{clock['observed_s']:.2f} s")
c.metric('Campioni tempo/velocità validi',f"{summary['valid_time_speed_samples']:,}")
rate=session.quality.get('time') or {}
d.metric('Frequenza osservata',f"{rate['observed_rate_hz']:.2f} Hz" if rate.get('observed_rate_hz') else 'N/D')
st.caption('Campioni validi: tempo finito e velocità 0–500 km/h, dove questi canali sono disponibili. Gli altri segnali hanno copertura propria.')
quality_caption(frame)
table=pd.DataFrame([{'channel':channel,**stats} for channel,stats in summary['signals'].items()])
st.subheader('Statistiche dei segnali')
st.dataframe(table,hide_index=True,width='stretch')
st.caption('sample_mean: media dei campioni; time_mean: media pesata sugli intervalli osservati; covered_s: supporto valido del singolo segnale.')
metric_export(table,'session_metrics.csv','overview_csv')
usage,_=driver_metrics(frame)
st.subheader('Utilizzo pedali · soglie predefinite')
st.dataframe(pd.DataFrame([{'metric':k,**v} for k,v in usage['usage'].items()]),hide_index=True)
st.caption('Apri Driver Inputs dal menu per configurare le soglie e analizzare gli eventi.')
left,right=st.columns(2)
with left:
    distribution=gear_distribution(frame)
    if len(distribution):
        st.plotly_chart(px.bar(distribution,x='gear',y='time_pct',template='plotly_dark',
                              labels={'gear':'Marcia','time_pct':'Tempo osservato (%)'}),width='stretch')
    else:st.info('Marce non disponibili.')
with right:
    if 'rpm' in frame:
        from motorsport.analytics.session_metrics import chart_sample
        # Histogram uses full data counts, not the chart's downsampled trace.
        import numpy as np
        values=frame.rpm.dropna().to_numpy()
        counts,edges=np.histogram(values[np.isfinite(values)],bins=40)
        st.plotly_chart(px.bar(x=(edges[:-1]+edges[1:])/2,y=counts,template='plotly_dark',
                              labels={'x':'RPM','y':'Campioni'}),width='stretch')
    else:st.info('RPM non disponibile.')
signal_chart(frame,['g_lat','g_lon'],session,key='overview_accel')
with st.expander('Canali termici, pneumatici e dinamica disponibili'):
    st.write([c for c in frame if any(s in c.lower() for s in ['temp','tyre','psi','load','susp','slip','wheel'])])
st.subheader('Capacità del dataset')
st.dataframe(capability_table(session),hide_index=True,width='stretch')
features=lap_features(session)
if not features.empty:
    st.subheader('Giri verificati e feature candidate')
    st.warning('Feature sull’intero giro: analisi retrospettiva. Non usarle per prevedere causalmente il tempo durante lo stesso giro.')
    st.dataframe(features,hide_index=True,width='stretch')
    metric_export(features,'lap_features_v05.csv','lap_features_csv')
