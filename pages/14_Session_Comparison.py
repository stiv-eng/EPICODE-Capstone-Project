"""Two explicit session windows, or strictly validated complete source laps."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from motorsport_ui.hover import render_chart

from motorsport.analytics.comparison import SessionWindow,compare_windows,common_channels,cumulative_lap_delta
from motorsport.analytics.timebase import weighted_signal,numeric
from motorsport_ui.telemetry import source_catalog,get_source,metric_export
from motorsport_ui.selection import lap_labels,selected_frame
from motorsport_ui.visuals import comparison_figure,session_label
from motorsport_ui.comparison_hover import render_comparison
from motorsport.analytics.channels import usable_channels
from motorsport_ui.widgets import valid_multiselect

st.title('Telemetry Comparison')
sources=source_catalog(include_acgym=True)
if not sources:
    st.info('Apri Data Explorer e carica un dataset.');st.stop()
keys=list(sources)
active=st.session_state.get('telemetry_active_key',keys[0])
left,right=st.columns(2)
with left:ak=st.selectbox('Sessione A',keys,index=keys.index(active) if active in keys else 0,format_func=sources.get)
with right:bk=st.selectbox('Sessione B',keys,index=keys.index(active) if active in keys else 0,format_func=sources.get)
try:a,b=get_source(ak),get_source(bk)
except Exception as exc:st.error(f'Dataset non disponibile: {exc}');st.stop()
st.caption('Base temporale A: '+a.metadata.get('time_basis','tempo dichiarato dalla mappatura')+
           ' · B: '+b.metadata.get('time_basis','tempo dichiarato dalla mappatura'))
modes=['Giri verificati','Finestre di sessione'] if lap_labels(a) and lap_labels(b) else ['Finestre di sessione','Giri verificati']
mode=st.radio('Modalità confronto',modes,horizontal=True,key=f'comparison_mode_{ak}_{bk}')
channels=['speed_kmh','throttle_pct','brake_pct','steering','rpm','gear','g_lat','g_lon']
common,rejected=common_channels(a,b,channels)
common=[c for c in common if c in usable_channels(a.data,[c]) and c in usable_channels(b.data,[c])]
if rejected:
    with st.expander('Canali esclusi dal confronto'):
        st.json(rejected)
selected=valid_multiselect('Canali confrontati',common,key='comparison_channels',default=common[:3],max_selections=8)
saved=st.session_state.setdefault('comparison_windows',[])
if mode=='Finestre di sessione':
    st.info('Le selezioni sono finestre di sessione. L’asse relativo permette confronti temporali; non viene calcolato un delta sul giro.')
    ranges=[]
    for column,label,session,key in [(left,'A',a,ak),(right,'B',b,bk)]:
        with column:
            t=numeric(session.data,'elapsed_s');finite=t[np.isfinite(t)]
            if len(finite)<2 or (np.diff(t)<0).any() or finite[-1]<=finite[0]:
                st.info('Confronto temporale non disponibile: tempo dichiarato insufficiente o non ordinato.');st.stop()
            candidates=[w for w in saved if w['window'].session_id==session.metadata['session_id']]
            choice=st.selectbox(f'Finestra salvata {label}',[-1]+list(range(len(candidates))),
                                 format_func=lambda i:'Nuova finestra' if i<0 else candidates[i]['window'].label,
                                 key=f'{label}_{session.metadata["session_id"]}_saved')
            default=(float(finite[0]),float(min(finite[-1],finite[0]+30)))
            if choice>=0:
                window=candidates[choice]['window'];default=(window.start_s,window.end_s)
                st.caption(f'Finestra salvata selezionata: {default[0]:.3f}–{default[1]:.3f} s')
            bounds=st.slider(f'Finestra {label} (s)',float(finite[0]),float(finite[-1]),default,
                             key=f'{label}_{session.metadata["session_id"]}_{choice}_range')
            ranges.append(bounds)
            title=st.text_input(f'Nome finestra {label}',f'Session window {label}',key=f'window_name_{label}')
            if st.button(f'Salva finestra {label}'):
                if bounds[1]<=bounds[0]:st.warning('Seleziona una durata positiva.')
                elif len(saved)>=20:st.warning('Sono già conservate 20 finestre in questa sessione.')
                else:
                    saved.append({'window':SessionWindow(session.metadata['session_id'],*bounds,title),'source_key':key})
                    st.success('Finestra di sessione salvata.')
    try:
        av,bv,summary,_=compare_windows(a,b,*ranges,selected)
    except ValueError as exc:st.info(str(exc));st.stop()
    axis='relative_s';axis_label='Tempo dalla selezione (s)'
    labels=[f"{session_label(a)} / Finestra A {ranges[0][0]:.1f}-{ranges[0][1]:.1f} s",
            f"{session_label(b)} / Finestra B {ranges[1][0]:.1f}-{ranges[1][1]:.1f} s"]
    identities=[f'{ak}:window:A:{ranges[0]}',f'{bk}:window:B:{ranges[1]}']
else:
    if not a.laps.available or not b.laps.available:
        st.info('Modalità giri non disponibile: entrambe le sessioni richiedono confini completi validati. '
                'Il Parquet originale v0.4 ha contatori costanti.');st.stop()
    alabels,blabels=lap_labels(a),lap_labels(b)
    with left:aid=st.selectbox('Giro verificato A',list(alabels),format_func=alabels.get,key=f'compare_lap_A_{ak}')
    with right:bid=st.selectbox('Giro verificato B',list(blabels),format_func=blabels.get,index=min(1,len(blabels)-1),key=f'compare_lap_B_{bk}')
    if a.metadata.get('track_id')!=b.metadata.get('track_id') or not a.metadata.get('track_id'):
        st.info('Confronto giri non disponibile: identità del tracciato comune non verificata.');st.stop()
    av,bv=selected_frame(a,[aid]),selected_frame(b,[bid])
    axis='lap_elapsed_s';axis_label='Tempo relativo del giro (s)'
    st.caption('Allineamento per tempo relativo del giro misurato dalla sorgente. Non rappresenta posizioni fisiche identiche.')
    labels=[f"{session_label(a)} / {alabels[aid]}",f"{session_label(b)} / {blabels[bid]}"]
    identities=[f'{ak}:lap:{aid}',f'{bk}:lap:{bid}']
    summary=pd.DataFrame([{'channel':c,'A_time_mean':weighted_signal(av.assign(elapsed_s=av.lap_elapsed_s),c)['time_mean'],
                            'B_time_mean':weighted_signal(bv.assign(elapsed_s=bv.lap_elapsed_s),c)['time_mean']} for c in selected])
    st.dataframe(pd.DataFrame([{'Selection':'A','Session':session_label(a),'Lap':alabels[aid]},
                              {'Selection':'B','Session':session_label(b),'Lap':blabels[bid]}]),hide_index=True,width='stretch')
    try:
        delta=cumulative_lap_delta(a,b,aid,bid)
    except ValueError as exc:st.info(str(exc))
    else:
        fig=go.Figure(go.Scatter(x=delta.distance_m,y=delta.delta_s,name='B − A'))
        fig.update_layout(template='plotly_dark',xaxis_title='Distanza riferimento (m)',yaxis_title='Delta B − A (s)')
        render_chart(fig,width='stretch')

if selected:
    selections=list(zip(identities,labels,[av,bv]))
    fig=comparison_figure(selections,selected,axis,axis_label,a)
    st.caption('Passa sui segnali per leggere valori, unità e giro/finestra nel pannello laterale. La lettura resta visibile dopo il passaggio.')
    render_comparison(fig)
else:st.info('Seleziona almeno un canale compatibile.')
st.dataframe(summary,hide_index=True,width='stretch')
metric_export(summary,'comparison_metrics.csv','comparison_csv')
if saved:
    with st.expander(f'Finestre conservate nella sessione: {len(saved)}'):
        st.dataframe(pd.DataFrame([vars(w['window']) for w in saved]),hide_index=True)
        if st.button('Svuota selezioni salvate'):saved.clear();st.rerun()
