"""Dynamics exploration with source units and bounded scatter views."""
import plotly.express as px
import streamlit as st

from motorsport.analytics.channels import signal_unit,available_corners,paired_channels,usable_channels
from motorsport.analytics.session_metrics import chart_sample
from motorsport_ui.telemetry import signal_chart,quality_caption
from .widgets import valid_selectbox
from .gg import gg_figure
from .hover import render_figures


def render_dynamics(session, frame):
    quality_caption(frame)
    st.info('Le unità dei segnali sono dichiarate dalla sorgente dove note. Accelerazioni, sterzo, slip e sospensioni '
            'con calibrazione sconosciuta conservano la scala sorgente; le correlazioni non provano causalità.')
    accel=signal_chart(frame,['g_lat','g_lon'],session,key='dynamics_accel',render=False)
    gg=gg_figure(session,frame)
    spatial=[]
    if gg is not None:
        spatial.append((gg,'xy'))
        st.caption('Stessa scala sui due assi e area dati quadrata. Le unità sorgente non verificate non sono presentate come g fisici.')
    else:
        st.info('G-G non disponibile: servono accelerazioni laterale e longitudinale finite, simultanee e con la stessa unità dichiarata.')
    for title,x,y in [('Velocità e accelerazione laterale','speed_kmh','g_lat'),
                       ('Sterzo e velocità di imbardata','steering','yaw_rate')]:
        if y=='yaw_rate' and y not in frame and 'ang_vel_y' in frame:y='ang_vel_y'
        if paired_channels(frame,x,y):
            sample=chart_sample(frame,[x,y],max_points=3500)
            sample=sample.assign(**{'Campione sorgente':sample.index.astype(str)})
            spatial.append((px.scatter(sample,x=x,y=y,color='speed_kmh' if 'speed_kmh' in usable_channels(frame,['speed_kmh']) else None,
                                      render_mode='svg',title=title,template='plotly_dark',opacity=.55,hover_data=['Campione sorgente'],
                                      labels={x:f'{x} ({signal_unit(session,x)})',y:f'{y} ({signal_unit(session,y)})'}),'xy'))
        else:st.info(f'{title}: canali richiesti non disponibili.')
    families={'Slip angle':usable_channels(frame,['slip_angle']),'Wheel loads':list(available_corners(frame,'load').values()),
              'Suspension':list(available_corners(frame,'susp').values()),
              'Wheel speeds':list(available_corners(frame,'wheel_speed').values()) or list(available_corners(frame,'wheel_rps').values())}
    families={name:channels for name,channels in families.items() if channels}
    family=valid_selectbox('Famiglia dinamica',families,key='dynamics_family_choice')
    if family:
        family_figure=signal_chart(frame,families[family],session,key='dynamics_family',render=False)
    else:
        st.info('Nessuna famiglia dinamica aggiuntiva utilizzabile. Carica slip, carichi, sospensioni o velocità ruota con unità dichiarate.')
        family_figure=None
    figures=([(accel,'time' if accel.layout.meta['temporal_axis'] else 'xy')] if accel is not None else [])+spatial
    if family_figure is not None:
        figures.append((family_figure,'time' if family_figure.layout.meta['temporal_axis'] else 'xy'))
    if figures:render_figures(figures,key='dynamics_charts')
    st.caption('Per GT7 wheel_rps ha convenzione di segno propria; non è convertito automaticamente in velocità lineare. '
               'sway/surge non hanno unità fisiche certificate: il diagramma non viene presentato come un inviluppo in g calibrati.')
