"""Source-coordinate trajectory with controls, time inspection and sample marker."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from motorsport.analytics.position import position_view
from motorsport.analytics.channels import signal_unit
from motorsport.analytics.timebase import numeric
from motorsport_ui.telemetry import select_telemetry,time_window,quality_caption

st.title('Position Analysis')
session=select_telemetry('position')
frame=time_window(session.data,'position_window')
options=[c for c in ['speed_kmh','throttle_pct','brake_pct','steering','elapsed_s'] if c in frame]
color=st.selectbox('Colore traiettoria',options) if options else None
trace,stats=position_view(frame,color)
quality_caption(frame)
st.caption(f"Posizioni finite: {stats['finite_positions']:,} / {stats['samples']:,} · "
           f"posizioni invalide: {stats['invalid_positions']:,} · "
           +session.metadata.get('position_provenance','Provenienza e precisione delle coordinate non verificate.'))
if trace.empty:
    st.info('Posizione non disponibile: servono almeno tre coordinate finite con variazione spaziale.');st.stop()
valid=np.isfinite(np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]).all(axis=1)
available=frame.loc[valid]
selection=st.slider('Campione selezionato nella finestra',0,len(available)-1,0) if len(available)>1 else 0
point=available.iloc[selection]
hover=[c for c in ['elapsed_s','speed_kmh','throttle_pct','brake_pct','gear'] if c in trace]
custom=trace[hover].to_numpy() if hover else None
template='x=%{x:.2f}<br>y=%{y:.2f}'
for index,c in enumerate(hover):template+=f'<br>{c}=%{{customdata[{index}]:.3f}}'
template+='<extra></extra>'
fig=go.Figure(go.Scattergl(x=trace.pos_x,y=trace.pos_y,mode='markers',
    marker=dict(size=4,color=trace[color] if color else '#63b3ff',colorscale='Turbo',showscale=color is not None,
                colorbar=dict(title=f'{color} ({signal_unit(session,color)})' if color else '')),
    customdata=custom,hovertemplate=template,name='Traiettoria sorgente'))
fig.add_trace(go.Scatter(x=[point.pos_x],y=[point.pos_y],mode='markers',
                         marker=dict(size=15,color='#fff',symbol='x'),name='Campione selezionato'))
fig.update_layout(template='plotly_dark',height=620,xaxis_title='pos_x · '+signal_unit(session,'pos_x'),
                  yaxis_title='pos_y · '+signal_unit(session,'pos_y'),
                  legend=dict(orientation='h',y=1.10,x=0))
fig.update_yaxes(scaleanchor='x',scaleratio=1)
st.plotly_chart(fig,width='stretch')
st.dataframe(pd.DataFrame([point[hover]]),hide_index=True)
st.warning('Traiettoria in coordinate sorgente: non identifica una geometria certificata del circuito, '
           'posizioni esatte delle curve o una linea di partenza. Nel dataset originale le posizioni sono integrate e possono accumulare deriva.')
st.caption('Heading non visualizzato: nessun adattatore corrente dichiara una convenzione planare verificata. '
           'In GT7 i campi rot_* sono componenti di un quaternione, non angoli di orientamento.')
