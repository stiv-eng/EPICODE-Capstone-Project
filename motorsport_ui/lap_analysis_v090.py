"""Recorded spatial comparison UI; core analysis remains independent of Streamlit."""
from dataclasses import asdict
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from motorsport.lap_analysis.data import spatial_source,from_session,capabilities
from motorsport.lap_analysis.geometry import GeometryConfig
from motorsport.lap_analysis.alignment import AlignmentConfig
from motorsport.lap_analysis.analysis import analyze_laps,json_facts
from motorsport_ui.telemetry import ROOT,select_telemetry,source_catalog,get_source,source_signature
from motorsport_ui.selection import lap_labels,selection_identity
from motorsport_ui.hover import render_figures,render_chart,observed_tolerance


@st.cache_data(show_spinner=False,max_entries=4)
def cached_spatial(key,signature,identity,_session):
    return spatial_source(_session,key,ROOT)


@st.cache_data(show_spinner=False,max_entries=12)
def cached_analysis(key_a,key_b,signature_a,signature_b,lap_a,lap_b,configuration,_reference,_analyzed):
    options=json.loads(configuration)
    return analyze_laps(_reference,_analyzed,GeometryConfig(**options['geometry']),AlignmentConfig(**options['alignment']))


def trajectory_figure(result,maximum=False):
    geometry=result.geometry
    fig=go.Figure()
    seen=set()
    for section in geometry.sections:
        indexes=section['reference_indices']
        indexes=indexes+[(indexes[-1]+1)%len(geometry.s)]
        xy=geometry.xy[indexes]
        kind=section['kind'];label={'corner':'Curve da geometria','straight':'Rettilinei','boundary':'Zona traguardo: curvatura non verificata'}[kind]
        fig.add_trace(go.Scatter(x=xy[:,0],y=xy[:,1],mode='lines',name=label,legendgroup=kind,
            showlegend=kind not in seen,line=dict(color='#ff965c' if kind=='corner' else ('#c5a0e6' if kind=='boundary' else '#8995a7'),width=3),
            customdata=[[section['section_id']]]*len(xy),hovertemplate='%{customdata[0]}<br>x=%{x:.2f} m<br>y=%{y:.2f} m<extra></extra>'))
        seen.add(kind)
    corners=[section for section in geometry.sections if section['kind']=='corner']
    for field,label,color,symbol in [('curvature_weighted_apex_proxy','Curvature-weighted apex proxy','#4bd8db','circle'),
                                      ('maximum_curvature_point','Maximum-curvature point','#dc8af2','x')]:
        if field=='maximum_curvature_point' and not maximum:
            continue
        selected=[s for s in corners if s[field]]
        if selected:
            fig.add_trace(go.Scatter(x=[s[field]['xy'][0] for s in selected],y=[s[field]['xy'][1] for s in selected],
                mode='markers+text' if field=='curvature_weighted_apex_proxy' else 'markers',text=[s['section_id'] for s in selected],
                textposition='top center',name=label,marker=dict(color=color,symbol=symbol,size=9),
                customdata=[[s['section_id'],s[field]['s_m']] for s in selected],
                hovertemplate='%{customdata[0]}<br>s=%{customdata[1]:.2f} m<br>x=%{x:.2f} m<br>y=%{y:.2f} m<extra></extra>'))
    fig.update_layout(title='Traiettoria di riferimento osservata · geometria deterministica',height=570,
        xaxis_title='X sorgente (m)',yaxis_title='Y sorgente (m)',legend=dict(orientation='h'),uirevision='lap-analysis-map')
    fig.update_yaxes(scaleanchor='x',scaleratio=1)
    return fig


def _distance_axis(fig):
    fig.update_layout(meta=dict(cursor_label='s',cursor_unit='m',temporal_axis=False,
        cursor_sample_policy='posizione sul riferimento comune; campione osservato/allineato più vicino entro tolleranza.'))
    return fig


def corner_signals(result,section):
    choices=[('speed_kmh','Velocità','km/h'),('brake_pct','Freno','%'),('throttle_pct','Acceleratore','%'),
             ('steering','Sterzo',None),('g_lat','Accelerazione laterale',None),('g_lon','Accelerazione longitudinale',None)]
    choices=[row for row in choices if any(row[0] in aligned.lap.frame for aligned in (result.reference,result.analyzed))]
    fig=make_subplots(rows=len(choices),cols=1,shared_xaxes=True,vertical_spacing=.025)
    start,end=section['start_s_m'],section['end_s_m']
    length=result.geometry.length_m
    for number,aligned in enumerate((result.reference,result.analyzed)):
        position=aligned.progress
        mask=((position>=start)|(position<=end)) if section['wraps_start_finish'] else ((position>=start)&(position<=end))
        indexes=np.flatnonzero(mask)
        local=np.where(position[indexes]<start,position[indexes]+length,position[indexes]) if section['wraps_start_finish'] else position[indexes]
        order=np.argsort(local,kind='stable');indexes=indexes[order];local=local[order]
        stride=max(1,len(indexes)//1400);indexes=indexes[::stride];local=local[::stride]
        for row,(channel,label,unit) in enumerate(choices,1):
            if channel not in aligned.lap.frame:
                continue
            values=aligned.lap.frame[channel].to_numpy(float)[indexes].copy()
            # Break at the actual two-fragment seam and observed spatial gaps;
            # never draw a line through a missing piece of telemetry.
            if len(indexes)>1:
                gaps=(np.abs(np.diff(indexes))>max(stride*2,2)) | (np.diff(local)>15.)
                values[np.flatnonzero(gaps)+1]=np.nan
            color='#63b3ff' if number==0 else '#ff965c'
            label_lap='Riferimento' if number==0 else 'Analizzato'
            fig.add_trace(go.Scatter(x=local,y=values,mode='lines',name=label_lap,legendgroup=label_lap,
                showlegend=row==1,line=dict(color=color),connectgaps=False,
                customdata=[[str(i)] for i in indexes],
                meta=dict(channel=label,selection_id=label_lap,unit=unit or aligned.lap.units.get(channel,'unità non verificata'),
                          tolerance=observed_tolerance(aligned.progress),sample_label='Campione sorgente')),row=row,col=1)
            fig.update_yaxes(title_text=label+' ('+(unit or aligned.lap.units.get(channel,'?'))+')',row=row,col=1)
    fig.update_xaxes(title_text='Posizione sul riferimento comune (m)',row=len(choices),col=1)
    fig.update_layout(height=max(420,145*len(choices)),title='Segnali osservati nella curva selezionata',margin=dict(t=50))
    return _distance_axis(fig)


def render():
    st.title('Telemetry Lap Analysis')
    st.caption('v0.9.0 · confronto deterministico di giri registrati · misure e proxy geometrici, senza attribuzioni causali')
    reference_session=select_telemetry('lap_analysis')
    key_a=st.session_state['telemetry_active_key']
    if st.session_state.get('lap_analysis_reference_source')!=key_a:
        st.session_state['lap_analysis_reference_source']=key_a
        st.session_state['lap_analysis_source_b']=key_a
        for name in ('lap_analysis_ref','lap_analysis_lap','lap_analysis_corner'):
            st.session_state.pop(name,None)
    catalog=source_catalog(include_acgym=True)
    key_b=st.selectbox('Sessione del giro analizzato',list(catalog),index=list(catalog).index(key_a),format_func=catalog.get,key='lap_analysis_source_b')
    if st.session_state.get('lap_analysis_previous_b')!=key_b:
        st.session_state['lap_analysis_previous_b']=key_b
        st.session_state.pop('lap_analysis_lap',None)
        st.session_state.pop('lap_analysis_corner',None)
    try:
        analyzed_session=get_source(key_b)
    except (OSError,ValueError) as exc:
        st.info('Sessione analizzata non disponibile: '+str(exc));return
    labels_a,labels_b=lap_labels(reference_session),lap_labels(analyzed_session)
    if not labels_a or not labels_b:
        st.info('Servono giri completi verificati in entrambe le sessioni. Le finestre generiche restano disponibili in Telemetry Comparison.')
        return
    fastest=reference_session.laps.laps.sort_values('duration_s').lap_id.tolist()
    lap_a=st.selectbox('Giro di riferimento',list(labels_a),index=list(labels_a).index(fastest[0]),format_func=labels_a.get,key='lap_analysis_ref')
    candidates=analyzed_session.laps.laps.sort_values('duration_s').lap_id.tolist()
    default_b=next((value for value in candidates if key_a!=key_b or value!=lap_a),candidates[0])
    lap_b=st.selectbox('Giro analizzato',list(labels_b),index=list(labels_b).index(default_b),format_func=labels_b.get,key='lap_analysis_lap')
    with st.expander('Parametri geometrici e limiti di qualità',expanded=False):
        radius=st.number_input('Soglia raggio curva (m)',20.,500.,150.,10.,key='lap_analysis_radius')
        spacing=st.number_input('Risoluzione spaziale (m)',.25,10.,1.5,.25,key='lap_analysis_spacing')
        smoothing=st.number_input('Finestra smoothing spaziale (m)',1.,31.,9.,2.,key='lap_analysis_smoothing')
        minimum=st.number_input('Lunghezza minima curva (m)',1.,60.,12.,1.,key='lap_analysis_minimum')
        merge=st.number_input('Intervallo breve da unire (m)',.5,30.,6.,.5,key='lap_analysis_merge')
        closure=st.number_input('Chiusura massima traiettoria (m)',1.,30.,8.,1.,key='lap_analysis_closure')
        offset=st.number_input('Scostamento massimo dal riferimento (m)',1.,30.,12.,1.,key='lap_analysis_offset')
        st.caption('Soglia predefinita 150 m; sezioni definite una sola volta sul riferimento. Le curve rilevate non sono etichette ufficiali del circuito.')
    signature_a=(source_signature(key_a),selection_identity(reference_session))
    signature_b=(source_signature(key_b),selection_identity(analyzed_session))
    spatial_a=cached_spatial(key_a,*signature_a,reference_session)
    spatial_b=cached_spatial(key_b,*signature_b,analyzed_session)
    a,b=from_session(reference_session,lap_a,spatial_a),from_session(analyzed_session,lap_b,spatial_b)
    options=dict(geometry=asdict(GeometryConfig(spacing,radius,smoothing,minimum,merge,closure)),
                 alignment=asdict(AlignmentConfig(max_offset_m=offset)))
    options['implementation_stamp']=[(p.name,p.stat().st_mtime_ns,p.stat().st_size) for p in sorted((ROOT/'motorsport/lap_analysis').glob('*.py'))]
    result=cached_analysis(key_a,key_b,signature_a,signature_b,str(lap_a),str(lap_b),json.dumps(options,sort_keys=True),a,b)
    report=result.report
    c1,c2,c3=st.columns(3)
    c1.metric('Tempo riferimento',f'{a.duration_s:.3f} s')
    c2.metric('Tempo analizzato',f'{b.duration_s:.3f} s')
    c3.metric('Differenza totale misurata',f'{b.duration_s-a.duration_s:+.3f} s')
    st.caption('Coordinate: '+a.position_provenance+' · asse comune dalla proiezione X/Y, mai dalla durata o dalla distanza normalizzata di ciascun giro.')
    with st.expander('Canali, unità e misure sull’intero giro'):
        rows=[dict(lap=label,channel=name,**value) for label,source in [('Riferimento',a),('Analizzato',b)] for name,value in capabilities(source).items()]
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.json(report['whole_lap'])
    facts=json_facts(result)
    st.download_button('Esporta fatti JSON',json.dumps(facts,indent=2,ensure_ascii=False,allow_nan=False),
        file_name='telemetry_lap_analysis_v090.json',mime='application/json',key='lap_analysis_export',on_click='ignore')
    maximum=st.checkbox('Mostra maximum-curvature point (diagnostica)',False,key='lap_analysis_maximum')
    if result.geometry is not None:
        render_chart(trajectory_figure(result,maximum),mode='xy',key='lap_analysis_geometry')
        st.caption(f"{sum(s['kind']=='corner' for s in result.geometry.sections)} curve geometriche · "
                   f"{result.geometry.length_m:.1f} m sul riferimento · raggio soglia {radius:g} m · "
                   'apice operativo: curvature-weighted apex proxy, non apice fisico verificato.')
        if not result.geometry.quality.get('seam_curvature_available',True):
            st.caption('La piccola giunzione al traguardo non verifica una tangente continua: la zona B conserva il tempo, con curvatura e tipo di curva non classificati.')
    if report['status']!='valid':
        st.warning('Analisi spaziale non disponibile: '+'; '.join(report['alignment']['reasons']))
        st.caption('Tempi giro e riepiloghi temporali restano misurabili. Nessuna curva o perdita di tempo viene inventata per il confronto.')
        return
    st.success('Allineamento spaziale valido nei limiti dichiarati')
    qa,qb=report['alignment']['reference'],report['alignment']['analyzed']
    st.caption(f"Scostamento P95 A/B: {qa['p95_offset_m']:.2f}/{qb['p95_offset_m']:.2f} m · "
               f"riconciliazione sezioni {report['reconciliation']['error_s']:.3g} s · "
               'ancore di timing indipendenti 0/fine giro; gli ultimi campioni possono precedere il traguardo di ≤100 ms.')
    section_table=pd.DataFrame(report['section_deltas'])
    contributions=go.Figure(go.Bar(x=section_table.section_id,y=section_table.delta_s,
        marker_color=['#ff965c' if value>=0 else '#4bd8db' for value in section_table.delta_s],name='Contributo sezione'))
    contributions.update_layout(title='Contributi netti delle sezioni: curve, rettilinei e zona traguardo',xaxis_title='Sezione del riferimento',yaxis_title='Δ tempo B − A (s)',height=330)
    render_chart(contributions,mode='xy',key='lap_analysis_contributions')
    corners=[s for s in result.geometry.sections if s['kind']=='corner']
    if not corners:
        st.info('Nessuna curva supera la soglia selezionata. La decomposizione include comunque i rettilinei.')
        return
    selected=st.selectbox('Curva da ispezionare',[s['section_id'] for s in corners],key='lap_analysis_corner')
    section=next(s for s in corners if s['section_id']==selected)
    contribution=next(s for s in report['section_deltas'] if s['section_id']==selected)
    st.subheader(f"{selected}: {contribution['delta_s']:+.3f} s rispetto al riferimento")
    measured=next(c for c in report['corners'] if c['section_id']==selected)
    concise=[]
    labels={'brake_onset_position_m':'Posizione inizio frenata','speed_at_apex_kmh':'Velocità al proxy di apice',
            'throttle_after_apex_delay_s':'Ritardo applicazione acceleratore'}
    for metric in measured['kpis']:
        if metric['name'] in labels and metric['validity']=='valid':
            concise.append(f"{labels[metric['name']]} Δ {metric['difference']:+.2f} {metric['unit']}")
    if concise:
        st.write(' · '.join(concise))
    kpis=pd.DataFrame(measured['kpis'])
    st.dataframe(kpis[['name','unit','reference_value','analyzed_value','difference','validity','explanation']],hide_index=True,width='stretch')
    delta=go.Figure(go.Scatter(x=result.trace.reference_s_m,y=result.trace.delta_s,mode='lines',name='Δ tempo B − A',
        meta=dict(unit='s',channel='Delta cumulato',tolerance=result.geometry.quality['actual_spacing_m']*.51)))
    delta.update_layout(title='Delta cumulato sul riferimento comune',xaxis_title='Posizione comune (m)',yaxis_title='Δ tempo (s)',height=350)
    _distance_axis(delta)
    render_figures([(delta,'time'),(corner_signals(result,section),'time')],key='lap_analysis_spatial_signals')
    with st.expander('Definizioni, finestre effettive e qualità'):
        st.json(dict(kpis=measured['kpis'],braking_events=measured['braking_events'],alignment=report['alignment']))
        st.dataframe(section_table,hide_index=True,width='stretch')
    st.caption(f"Calcolo deterministico {report['runtime_s']:.3f} s; risultati memorizzati per sorgenti, giri e parametri. "
               'La selezione della curva e l’hover non modificano l’analisi. Differenze di input e differenze di tempo non dimostrano causalità.')
