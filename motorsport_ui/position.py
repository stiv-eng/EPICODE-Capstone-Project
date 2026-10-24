"""Shared colored source trajectory for all adapters and uploads."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from motorsport.analytics.position import position_segments, color_channels
from motorsport.analytics.channels import signal_unit
from motorsport.analytics.timebase import numeric
from .visuals import trajectory_figure


def render_position(session,frame):
    options=color_channels(frame)
    color=st.selectbox('Colore traiettoria',options,index=options.index('speed_kmh') if 'speed_kmh' in options else 0,key='position_color',
                       format_func=lambda c:f'{c} · {signal_unit(session,c)}') if options else None
    segments,stats=position_segments(frame,color)
    if segments.empty:
        st.info('Track visualization unavailable. Servono coordinate X/Y finite e variabili con tempo dichiarato e campioni consecutivi. Nessuna geometria è ricostruita.');return
    fig=trajectory_figure(segments,frame,color,signal_unit(session,color) if color else '')
    valid=np.isfinite(np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]).all(axis=1)
    available=frame.loc[valid]
    index=st.slider('Campione selezionato nella finestra',0,len(available)-1,0,key='position_instant') if len(available)>1 else 0
    point=available.iloc[index]
    fig.add_trace(go.Scatter(x=[point.pos_x],y=[point.pos_y],mode='markers',
                             marker=dict(size=13,color='white',symbol='x'),name='Campione selezionato'))
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
