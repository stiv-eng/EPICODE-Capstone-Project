"""Shared colored source trajectory for all adapters and uploads."""
import numpy as np
import pandas as pd
import streamlit as st
from motorsport.analytics.position import position_segments, color_channels,position_adjacency
from motorsport.analytics.orientation import vehicle_orientation
from motorsport.analytics.channels import signal_unit
from motorsport.analytics.timebase import numeric
from .visuals import trajectory_figure
from .widgets import valid_selectbox
from .vehicle import add_vehicle
from .selection import selection_identity


@st.cache_data(show_spinner=False,max_entries=4)
def trajectory_base(frame,color,unit):
    segments,stats=position_segments(frame,color)
    edges,limits=position_adjacency(frame)
    stats.update(limits)
    fig=trajectory_figure(segments,frame,color,unit)
    if segments.empty:
        fig.update_layout(template='plotly_dark',height=620)
        fig.update_yaxes(scaleanchor='x',scaleratio=1)
    return fig,stats,edges


def render_position(session,frame):
    valid=np.isfinite(np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]).all(axis=1)
    if not valid.any():
        st.info('Track visualization unavailable. Servono coordinate X/Y finite e compatibili. Nessuna geometria è ricostruita.');return
    options=color_channels(frame)
    color=valid_selectbox('Colore traiettoria',options,index=options.index('speed_kmh') if 'speed_kmh' in options else 0,key='position_color',
                       format_func=lambda c:f'{c} · {signal_unit(session,c)}') if options else None
    fig,stats,edges=trajectory_base(frame,color,signal_unit(session,color) if color else '')
    if not stats['rendered_segments']:
        st.info('Nessun segmento continuo utilizzabile: viene mostrata soltanto la posizione misurata, con indicatore neutro se la direzione è indefinita.')
    available=frame.loc[valid]
    index=st.slider('Campione selezionato nella finestra',0,len(available)-1,0,key='position_instant') if len(available)>1 else 0
    point=available.iloc[index]
    offset=np.flatnonzero(valid)[index]
    theta,description=vehicle_orientation(frame,offset,session.metadata,edges)
    add_vehicle(fig,point.pos_x,point.pos_y,theta,description)
    fig.update_layout(uirevision=f'{selection_identity(session)}:{frame.index[0]}:{frame.index[-1]}',
        meta=dict(vehicle_sample=str(point.name),vehicle_x=float(point.pos_x),vehicle_y=float(point.pos_y),
                  vehicle_theta=theta,orientation_basis=description))
    st.caption(f'Campione sorgente {point.name} · '+description)
    fig.update_xaxes(title_text='pos_x · '+signal_unit(session,'pos_x'))
    fig.update_yaxes(title_text='pos_y · '+signal_unit(session,'pos_y'))
    st.plotly_chart(fig,width='stretch',key='position_trajectory')
    columns=[c for c in ['elapsed_s','lap_id','lap_elapsed_s','speed_kmh','throttle_pct','brake_pct','gear',color] if c and c in frame]
    st.dataframe(pd.DataFrame([point[list(dict.fromkeys(columns))]]),hide_index=True)
    st.caption(f"{stats['rendered_segments']:,} segmenti · {stats['runs']} frammenti · {stats['finite_positions']:,}/{stats['samples']:,} posizioni finite. "
               'Colore: misura al primo campione del segmento, scala continua in 32 fasce o valori discreti; grigio = misura assente. Estremi inclusi nella scala.')
    st.caption(f"Interruzioni: tempo non crescente, lacune >{stats['gap_threshold_s']:.3f} s, campioni mancanti, cambi giro e salti >20× passo spaziale mediano. "
               'Semplificazione entro ciascun frammento; nessun collegamento tra frammenti.')
    if stats['omitted_runs']:
        st.warning(f"Budget grafico: {stats['omitted_runs']} frammenti brevi omessi. Riduci la selezione.")
    st.warning('Traiettoria in coordinate sorgente; geometria fisica e linea del traguardo non certificate. '+
               session.metadata.get('position_provenance','Provenienza e accuratezza non verificate.'))
