"""Dynamics exploration with source units and bounded scatter views."""
import plotly.express as px
import streamlit as st

from motorsport.analytics.channels import signal_unit,corner_channels
from motorsport.analytics.session_metrics import chart_sample
from motorsport_ui.telemetry import signal_chart,quality_caption


def render_dynamics(session, frame):
    quality_caption(frame)
    st.info('Le unità dei segnali sono dichiarate dalla sorgente dove note. Accelerazioni, sterzo, slip e sospensioni '
            'con calibrazione sconosciuta conservano la scala sorgente; le correlazioni non provano causalità.')
    signal_chart(frame,['g_lat','g_lon'],session,key='dynamics_accel')
    for title,x,y in [('Diagramma G-G · scala sorgente','g_lat','g_lon'),
                       ('Velocità e accelerazione laterale','speed_kmh','g_lat'),
                       ('Sterzo e velocità di imbardata','steering','yaw_rate')]:
        if y=='yaw_rate' and y not in frame and 'ang_vel_y' in frame:y='ang_vel_y'
        if {x,y}.issubset(frame):
            sample=chart_sample(frame,[x,y],max_points=3500)
            st.plotly_chart(px.scatter(sample,x=x,y=y,color='speed_kmh' if 'speed_kmh' in sample else None,
                                      render_mode='svg',title=title,template='plotly_dark',opacity=.55,
                                      labels={x:f'{x} ({signal_unit(session,x)})',y:f'{y} ({signal_unit(session,y)})'}),width='stretch')
        else:st.info(f'{title}: canali richiesti non disponibili.')
    families={'Slip angle':['slip_angle'],'Wheel loads':list(corner_channels(frame,'load').values()),
              'Suspension':list(corner_channels(frame,'susp').values()),
              'Wheel speeds':list(corner_channels(frame,'wheel_speed').values()) or list(corner_channels(frame,'wheel_rps').values())}
    family=st.selectbox('Famiglia dinamica',list(families))
    signal_chart(frame,families[family],session,key='dynamics_family')
    st.caption('Per GT7 wheel_rps ha convenzione di segno propria; non è convertito automaticamente in velocità lineare. '
               'sway/surge non hanno unità fisiche certificate: il diagramma non viene presentato come un inviluppo in g calibrati.')
