"""Configurable driver-input occupancy and braking event inspection."""
import pandas as pd
import streamlit as st

from motorsport.analytics.driver_inputs import driver_metrics
from motorsport_ui.telemetry import select_telemetry,time_window,quality_caption,signal_chart,metric_export

st.title('Driver Inputs')
session=select_telemetry('inputs')
frame=time_window(session.data,'inputs_window')
a,b,c,d=st.columns(4)
throttle=a.slider('Soglia acceleratore (%)',0.,100.,90.)
brake=b.slider('Soglia freno (%)',0.,100.,5.)
minimum=c.number_input('Durata minima evento (s)',min_value=0.,value=.1,step=.05)
overlap=d.slider('Acceleratore per sovrapposizione (%)',0.,100.,5.)
metrics,events=driver_metrics(frame,throttle,brake,minimum,overlap)
quality_caption(frame)
st.caption('Uso pedali: percentuale del tempo coperto da valori validi 0–100%, con soglia strettamente superata. '
           'La sovrapposizione richiede entrambi i pedali sopra le rispettive soglie. Nessuna pressione frenante viene dedotta.')
usage=pd.DataFrame([{'metric':k,**v} for k,v in metrics['usage'].items()])
st.dataframe(usage,hide_index=True,width='stretch')
a,b,c=st.columns(3)
a.metric('Eventi osservati / completi',f"{metrics['observed_events']} / {metrics['complete_events']}")
mean=metrics['entry_speed_mean_kmh'];peak=metrics['entry_speed_max_kmh']
b.metric('Velocità ingresso media',f'{mean:.1f} km/h' if mean is not None else 'N/D')
c.metric('Velocità ingresso massima',f'{peak:.1f} km/h' if peak is not None else 'N/D')
st.caption('Evento: sequenza continua di intervalli sopra soglia. Frammenti ai bordi o dopo lacune non sono eventi completi. '
           'La velocità d’ingresso è il campione di inizio osservato; media/massimo riguardano gli eventi completi.')
metric_export(usage,'driver_usage.csv','usage_csv')
with st.expander('Eventi e attività dello sterzo'):
    st.dataframe(events,hide_index=True,width='stretch')
    metric_export(events,'braking_events.csv','events_csv')
    st.json(metrics['steering'])
    activity=metrics['steering_activity_source_units_per_s']
    st.write('Attività sterzo (variazione assoluta per secondo osservato):',activity)
    st.caption('Unità e calibrazione dello sterzo restano quelle della sorgente; non è una misura certificata del lavoro del pilota.')
channels=[c for c in ['throttle_pct','brake_pct','steering','speed_kmh','rpm','gear'] if c in frame]
selected=st.multiselect('Panoramica combinata degli input',channels,default=channels)
signal_chart(frame,selected,session,key='driver_combined')
