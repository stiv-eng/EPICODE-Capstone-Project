"""Two explicit session windows, or strictly validated complete source laps."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from motorsport.analytics.comparison import SessionWindow,compare_windows,lap_trace,common_channels,cumulative_lap_delta
from motorsport.analytics.session_metrics import chart_sample
from motorsport.analytics.timebase import weighted_signal,numeric,chart_values
from motorsport_ui.telemetry import source_catalog,get_source,metric_export

st.title('Telemetry Comparison')
sources=source_catalog()
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
mode=st.radio('Modalità confronto',['Finestre di sessione','Giri verificati'],horizontal=True)
channels=['speed_kmh','throttle_pct','brake_pct','steering','rpm','gear','g_lat','g_lon']
common,rejected=common_channels(a,b,channels)
if rejected:
    with st.expander('Canali esclusi dal confronto'):
        st.json(rejected)
selected=st.multiselect('Canali confrontati',common,default=common[:3],max_selections=8)
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
else:
    if not a.laps.available or not b.laps.available:
        st.info('Modalità giri non disponibile: entrambe le sessioni richiedono confini completi validati. '
                'Il Parquet originale v0.4 ha contatori costanti.');st.stop()
    with left:aid=st.selectbox('Giro verificato A',a.laps.laps.lap_id.tolist())
    with right:bid=st.selectbox('Giro verificato B',b.laps.laps.lap_id.tolist(),index=min(1,len(b.laps.laps)-1))
    if a.metadata.get('track_id')!=b.metadata.get('track_id') or not a.metadata.get('track_id'):
        st.info('Confronto giri non disponibile: identità del tracciato comune non verificata.');st.stop()
    try:av,bv=lap_trace(a,aid),lap_trace(b,bid)
    except ValueError as exc:st.info(str(exc));st.stop()
    axis='normalized_driven_progress';axis_label='Frazione della distanza percorsa (0–1) · allineamento approssimativo'
    st.warning('La frazione della distanza percorsa confronta la forma dei segnali; traiettorie diverse non corrispondono necessariamente allo stesso punto fisico. '
               'Il delta cumulato richiede un riferimento comune del tracciato verificato.')
    summary=pd.DataFrame([{'channel':c,'A_time_mean':weighted_signal(av.assign(elapsed_s=av.lap_elapsed_s),c)['time_mean'],
                            'B_time_mean':weighted_signal(bv.assign(elapsed_s=bv.lap_elapsed_s),c)['time_mean']} for c in selected])
    st.dataframe(pd.concat([a.laps.laps.loc[a.laps.laps.lap_id.eq(aid)].assign(selection='A'),
                            b.laps.laps.loc[b.laps.laps.lap_id.eq(bid)].assign(selection='B')]),hide_index=True)
    try:
        delta=cumulative_lap_delta(a,b,aid,bid)
    except ValueError as exc:st.info(str(exc))
    else:
        fig=go.Figure(go.Scatter(x=delta.distance_m,y=delta.delta_s,name='B − A'))
        fig.update_layout(template='plotly_dark',xaxis_title='Distanza riferimento (m)',yaxis_title='Delta B − A (s)')
        st.plotly_chart(fig,width='stretch')

if selected:
    fig=make_subplots(rows=len(selected),cols=1,shared_xaxes=True,subplot_titles=selected)
    for view,label,color in [(av,'A','#63b3ff'),(bv,'B','#ff6d55')]:
        sample=chart_sample(view,selected,max_points=5000)
        for row,c in enumerate(selected,1):
            fig.add_trace(go.Scattergl(x=sample[axis],y=chart_values(view,sample,c,'elapsed_s' if mode=='Finestre di sessione' else 'lap_elapsed_s'),name=f'{label} · {c}',
                                      legendgroup=label,line=dict(color=color),mode='lines',connectgaps=False),row=row,col=1)
    fig.update_layout(template='plotly_dark',height=max(350,200*len(selected)),hovermode='x unified')
    fig.update_xaxes(title_text=axis_label,row=len(selected),col=1)
    st.plotly_chart(fig,width='stretch')
else:st.info('Seleziona almeno un canale compatibile.')
st.dataframe(summary,hide_index=True,width='stretch')
metric_export(summary,'comparison_metrics.csv','comparison_csv')
if saved:
    with st.expander(f'Finestre conservate nella sessione: {len(saved)}'):
        st.dataframe(pd.DataFrame([vars(w['window']) for w in saved]),hide_index=True)
        if st.button('Svuota selezioni salvate'):saved.clear();st.rerun()
