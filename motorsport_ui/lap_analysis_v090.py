"""Recorded spatial comparison UI; core analysis remains independent of Streamlit."""
from dataclasses import asdict
import hashlib
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


KPI_LABELS = {
    'braking_event_count':'Braking Event Count',
    'brake_onset_position_m':'Brake Onset Position',
    'brake_release_position_m':'Brake Release Position',
    'braking_distance_m':'Braking Distance',
    'braking_duration_s':'Braking Duration',
    'maximum_brake_pct':'Peak Brake Input',
    'mean_brake_pct':'Mean Brake Input',
    'speed_at_brake_onset_kmh':'Speed at Brake Onset',
    'speed_at_brake_release_kmh':'Speed at Brake Release',
    'brake_onset_to_apex_m':'Brake Onset to Apex Distance',
    'trail_braking_proxy_duration_s':'Trail Braking Duration (Input Proxy)',
    'speed_at_apex_kmh':'Speed at Apex',
    'minimum_corner_speed_kmh':'Minimum Corner Speed',
    'minimum_speed_position_m':'Minimum Speed Position',
    'entry_speed_kmh':'Corner Entry Speed',
    'exit_speed_kmh':'Corner Exit Speed',
    'mean_corner_speed_kmh':'Mean Corner Speed',
    'minimum_trajectory_radius_m':'Minimum Trajectory Radius',
    'maximum_trajectory_curvature_1_m':'Peak Trajectory Curvature',
    'corner_traversal_time_s':'Corner Traversal Time',
    'peak_lateral_acceleration_g':'Peak Lateral Acceleration',
    'mean_absolute_lateral_acceleration_g':'Mean Absolute Lateral Acceleration',
    'braking_to_cornering_transition_s':'Brake Release to Lateral Acceleration Transition',
    'steering_at_apex':'Steering at Apex',
    'peak_absolute_steering':'Peak Absolute Steering',
    'steering_range':'Steering Range',
    'mean_absolute_steering':'Mean Absolute Steering',
    'steering_total_variation':'Steering Total Variation',
    'steering_rms_rate':'Steering RMS Rate (Smoothness Proxy)',
    'throttle_at_apex_pct':'Throttle at Apex',
    'throttle_after_apex_delay_s':'Throttle Reapplication Delay',
    'throttle_after_apex_distance_m':'Throttle Reapplication Distance',
    'first_sustained_throttle_after_minimum_position_m':'Sustained Throttle Position after Minimum Speed',
    'maximum_exit_throttle_pct':'Peak Exit Throttle',
    'mean_exit_acceleration_g':'Mean Exit Acceleration',
}


def kpi_label(metric):
    unit=metric['unit']
    if unit in (None,'None','None/s','unknown','unknown/s','source unit','source unit/s'):
        unit='unità non verificata'
    elif unit=='incompatible':
        unit='unità non confrontabili'
    return KPI_LABELS[metric['name']]+' ['+unit+']'


def remembered_selectbox(label,options,role,identity,default,format_func):
    """Widget identity follows its source; durable choices outlive widget cleanup."""
    if default not in options:
        default=next(iter(options))
    token=role+':'+identity
    key='lap_analysis_'+role+'_'+hashlib.sha256(token.encode()).hexdigest()[:20]
    memory=st.session_state.setdefault('lap_analysis_choices',{})
    if st.session_state.get(key) not in options:
        saved=memory.get(token,default)
        st.session_state[key]=saved if saved in options else default
    def changed():
        st.session_state['lap_analysis_choices'][token]=st.session_state[key]
    value=st.selectbox(label,list(options),format_func=format_func,key=key,on_change=changed)
    memory[token]=value
    return value


def lap_control(session,source_key,role,other_lap=None,same_source=False):
    labels=lap_labels(session)
    identity=source_key+':'+selection_identity(session)
    if not labels:
        st.selectbox('Lap',[],index=None,placeholder='Nessun giro completo verificato',
                     disabled=True,key='lap_analysis_empty_'+role)
        return None,identity
    candidates=session.laps.laps.sort_values('duration_s').lap_id.tolist()
    default=next((lap for lap in candidates if not same_source or lap!=other_lap),candidates[0])
    return remembered_selectbox('Lap',labels,role,identity,default,labels.get),identity


@st.cache_data(show_spinner=False,max_entries=4)
def cached_spatial(key,signature,identity,_session):
    return spatial_source(_session,key,ROOT)


@st.cache_data(show_spinner=False,max_entries=12)
def cached_analysis(key_a,key_b,signature_a,signature_b,lap_a,lap_b,configuration,_reference,_analyzed):
    options=json.loads(configuration)
    return analyze_laps(_reference,_analyzed,GeometryConfig(**options['geometry']),AlignmentConfig(**options['alignment']))


ISSUE_LABELS={
    'unreliable':'Regione non allineata o transizione',
    'offset':'Scostamento dal riferimento',
    'reverse_progress':'Arretramento della progressione proiettata',
    'ambiguous':'Rami geometrici ambigui',
    'progress_jump':'Salto di progressione proiettata',
    'coverage':'Copertura del giro insufficiente',
}
ISSUE_COLORS={'unreliable':'#ff6378','offset':'#ff6378','reverse_progress':'#ffd166','ambiguous':'#dc8af2',
              'progress_jump':'#ff965c','coverage':'#ffffff'}


def trajectory_figure(result):
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
    field='curvature_weighted_apex_proxy'
    selected=[s for s in corners if s[field]]
    if selected:
        fig.add_trace(go.Scatter(x=[s[field]['xy'][0] for s in selected],y=[s[field]['xy'][1] for s in selected],
            mode='markers+text',text=[s['section_id'] for s in selected],
            textposition='top center',name='Curvature-Weighted Apex Proxy',marker=dict(color='#4bd8db',symbol='circle',size=9),
            customdata=[[s['section_id'],s[field]['s_m']] for s in selected],
            hovertemplate='%{customdata[0]}<br>s=%{customdata[1]:.2f} m<br>x=%{x:.2f} m<br>y=%{y:.2f} m<extra></extra>'))
    if result.report['status']!='valid':
        for aligned,label in ((result.reference,'Reference Lap'),(result.analyzed,'Analysis Lap')):
            if aligned is None or not aligned.problem_masks:
                continue
            xy=aligned.lap.frame[['pos_x','pos_y']].to_numpy(float)
            if aligned.quality['status']=='partial':
                good=np.isfinite(aligned.progress)
                indexes=np.unique(np.r_[np.arange(0,len(xy),max(1,int(np.ceil(len(xy)/1800)))),len(xy)-1])
                line=xy[indexes].copy();line[~good[indexes]]=np.nan
                bad=np.cumsum(~good)
                line[1:][np.diff(bad[indexes])>0]=np.nan
                fig.add_trace(go.Scatter(x=line[:,0],y=line[:,1],mode='lines',connectgaps=False,
                    line=dict(color='#63b3ff',width=1.5),name='Allineamento affidabile · '+label,hoverinfo='skip'))
            for code,mask in aligned.problem_masks.items():
                if aligned.quality['status']=='partial' and code!='unreliable':
                    continue
                indexes=np.flatnonzero(mask)
                if not len(indexes):
                    continue
                # Mark actual observations; bounded display never connects
                # separate failed regions or changes the projection result.
                peak=next(i['worst_sample'] for i in aligned.quality['issues'] if i['code']==code)
                peaks=[i['worst_sample'] for i in aligned.quality['issues'] if mask[i['worst_sample']]] if code=='unreliable' else [peak]
                indexes=np.unique(np.r_[indexes[::max(1,int(np.ceil(len(indexes)/800)))],indexes[-1],peaks])
                causes=[' / '.join(ISSUE_LABELS[c] for c,m in aligned.problem_masks.items() if c!='unreliable' and m[i])
                        or ('Lacuna temporale o transizione' if 'Source clock discontinuity or gap' in aligned.quality['reasons'] else
                            'Transizione prudenziale o corrispondenza non ancora confermata') for i in indexes]
                fig.add_trace(go.Scatter(x=xy[indexes,0],y=xy[indexes,1],mode='markers',
                    name=ISSUE_LABELS[code]+' · '+label,marker=dict(color=ISSUE_COLORS[code],size=6),
                    customdata=[[int(i),float(aligned.time[i]),cause] for i,cause in zip(indexes,causes)],
                    hovertemplate='Campione %{customdata[0]:.0f}<br>t=%{customdata[1]:.3f} s<br>x=%{x:.2f} m<br>y=%{y:.2f} m<br>%{customdata[2]}<extra></extra>'))
    finish=result.report.get('finish_marker')
    if finish:
        fig.add_annotation(x=finish['xy'][0],y=finish['xy'][1],text='🏁',showarrow=False,
            yanchor='bottom',font=dict(size=21,family='Segoe UI Emoji, Apple Color Emoji, sans-serif'),
            hovertext='Ultima posizione registrata presso il confine temporale verificato; non una linea ufficiale di arrivo')
    fig.update_layout(title='Traiettoria di riferimento osservata · geometria deterministica',height=570,
        xaxis_title='X sorgente (m)',yaxis_title='Y sorgente (m)',legend=dict(orientation='h'),uirevision='lap-analysis-map')
    fig.update_yaxes(scaleanchor='x',scaleratio=1)
    return fig


def alignment_diagnostics(result):
    reasons=result.report['alignment']['reasons']
    explanations={
        'Projection too far from reference':'La traiettoria supera lo scostamento massimo consentito dal riferimento.',
        'Reverse motion / inconsistent lap direction exceeds tolerance':'La posizione proiettata arretra oltre la tolleranza: il confronto spaziale non è univoco. Questo non prova da solo una retromarcia del veicolo.',
        'Reference has ambiguous nearby branches at matched observations':'La traiettoria incontra rami vicini del riferimento che non possono essere distinti con sicurezza.',
        'Sequential projection contains implausible progress jumps':'Sono presenti salti di progressione incompatibili con gli spostamenti osservati.',
        'Observed circuit coverage does not match both reference boundaries':'I campioni non coprono entrambi i confini spaziali del giro di riferimento.',
        'More than one circuit / invalid progress range':'La progressione supera l’intervallo spaziale consentito per un giro.',
        'Source clock discontinuity or gap':'Il tempo sorgente presenta una discontinuità o una lacuna oltre la soglia.',
        'Witnessed lap timing lacks sufficiently recent boundary observations':'I campioni temporali sono troppo lontani dai confini verificati del giro.',
        'Analyzed trajectory does not satisfy spatial closure tolerance':'La traiettoria analizzata non rispetta la tolleranza di chiusura spaziale.',
        'Open reference geometry: no cyclic lap alignment or complete circuit decomposition':'La traiettoria di riferimento non è chiusa: non è possibile scomporre l’intero giro.',
    }
    for reason in dict.fromkeys(reasons):
        st.write(explanations.get(reason,reason))
    rows=[]
    for aligned,label in ((result.reference,'Reference Lap'),(result.analyzed,'Analysis Lap')):
        if aligned is None:
            continue
        for issue in aligned.quality.get('issues',[]):
            rows.append({'Lap':label,'Controllo':ISSUE_LABELS[issue['code']],
                'Campioni':issue['sample_count'],'Massimo':issue['maximum_observed'],
                'Limite':issue['limit'],'Unità':issue['unit'],
                'Primo tempo [s]':issue['first_time_s'],'Posizione critica [m]':issue['worst_reference_s_m']})
    if rows:
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.caption('I punti colorati sulla mappa sono campioni osservati nelle regioni problematiche; la tabella e il JSON conservano i conteggi completi.')


def _distance_axis(fig):
    fig.update_layout(meta=dict(cursor_label='s',cursor_unit='m',temporal_axis=False,
        cursor_sample_policy='posizione sul riferimento comune; campione osservato/allineato più vicino entro tolleranza.'))
    return fig


def contribution_figure(report):
    measured=report['section_deltas']
    fig=go.Figure()
    if measured:
        fig.add_trace(go.Bar(x=[s['section_id'] for s in measured],y=[s['delta_s'] for s in measured],
            marker_color=['#ff965c' if s['delta_s']>=0 else '#4bd8db' for s in measured],name='Sezioni misurate'))
    residual=report['unallocated_delta']
    if residual['required']:
        fig.add_trace(go.Bar(x=['Non attribuito'],y=[residual['value_s']],
            marker=dict(color='#c5a0e6',pattern_shape='/'),
            name='Delta non attribuito — Allineamento spaziale non disponibile',
            hovertemplate='Residuo contabile: %{y:+.3f} s<br>Non è una perdita misurata individualmente né una causa<extra></extra>'))
    fig.update_layout(title='Contributi misurati e delta non attribuito',xaxis_title='Sezione del riferimento',
        yaxis_title='Δ tempo B − A (s)',height=360,legend=dict(orientation='h',y=-.3))
    return fig


def corner_signals(result,section):
    choices=[('speed_kmh','Velocità','km/h'),('brake_pct','Freno','%'),('throttle_pct','Acceleratore','%'),
             ('steering','Sterzo',None),('g_lat','Accelerazione laterale',None),('g_lon','Accelerazione longitudinale',None)]
    choices=[row for row in choices if any(row[0] in aligned.lap.frame for aligned in (result.reference,result.analyzed))]
    fig=make_subplots(rows=len(choices),cols=1,shared_xaxes=True,vertical_spacing=.04)
    start,end=section['start_s_m'],section['end_s_m']
    length=result.geometry.length_m
    end=end+length if section['wraps_start_finish'] else end
    apex=section['curvature_weighted_apex_proxy']['s_m']
    apex=apex+length if apex<start else apex
    for number,aligned in enumerate((result.reference,result.analyzed)):
        # Context can cross the spatial seam. These are fragments of this same
        # recorded lap, never invented preceding/following-lap observations.
        position=np.concatenate([aligned.progress-length,aligned.progress,aligned.progress+length])
        source_indexes=np.tile(np.arange(len(aligned.progress)),3)
        mask=(position>=start-200.)&(position<=end+120.)
        indexes=source_indexes[mask];local=position[mask]
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
                bad=np.cumsum(~np.isfinite(aligned.progress))
                gaps|=(indexes[1:]>indexes[:-1])&(bad[indexes[1:]]-bad[indexes[:-1]]>0)
                values[np.flatnonzero(gaps)+1]=np.nan
            color='#63b3ff' if number==0 else '#ff965c'
            label_lap='Riferimento' if number==0 else 'Analizzato'
            fig.add_trace(go.Scatter(x=local,y=values,mode='lines',name=label_lap,legendgroup=label_lap,
                showlegend=row==1,line=dict(color=color),connectgaps=False,
                customdata=[[str(i)] for i in indexes],
                meta=dict(channel=label,selection_id=label_lap,unit=unit or aligned.lap.units.get(channel,'unità non verificata'),
                          tolerance=observed_tolerance(aligned.progress),sample_label='Campione sorgente')),row=row,col=1)
            short_label={'g_lat':'Accel. laterale','g_lon':'Accel. longitudinale'}.get(channel,label)
            fig.update_yaxes(title=dict(text=short_label+'<br>['+(unit or aligned.lap.units.get(channel,'?'))+']',standoff=12),
                             automargin=True,row=row,col=1)
    fig.add_vrect(x0=start,x1=end,fillcolor='#4bd8db',opacity=.06,line_width=0,row='all',col=1)
    for first,last in ((start-200.,start),(end,end+120.)):
        fig.add_vrect(x0=first,x1=last,fillcolor='#b6c2d2',opacity=.06,line_width=0,row='all',col=1)
    for position in (start,end):
        fig.add_vline(x=position,line_dash='dot',line_color='#b6c2d2',line_width=1,row='all',col=1)
    fig.add_vline(x=apex,line_dash='dash',line_color='#4bd8db',line_width=1,row='all',col=1)
    fig.update_xaxes(title_text='Posizione sul riferimento comune (m)',row=len(choices),col=1)
    fig.add_annotation(x=0,y=1.02,xref='paper',yref='paper',showarrow=False,xanchor='left',yanchor='bottom',font=dict(size=11),
        text='<span style="color:#4bd8db">■ Geometric Corner</span> · <span style="color:#b6c2d2">■ Analysis Context</span> · <span style="color:#4bd8db">┆ Weighted Apex Proxy</span>')
    fig.update_layout(height=max(520,210*len(choices)),title='Selected Corner · approccio, curva e uscita',
        margin=dict(t=105,b=65,l=110,r=25))
    return _distance_axis(fig)


def render():
    st.title('Telemetry Lap Analysis')
    st.caption('v0.9.3 · confronto deterministico di giri registrati · misure e proxy geometrici, senza attribuzioni causali')
    left,right=st.columns(2)
    with left:
        st.subheader('Reference Lap')
        reference_session=select_telemetry('lap_analysis',label='Session',sidebar=False)
        key_a=st.session_state['telemetry_active_key']
        lap_a,identity_a=lap_control(reference_session,key_a,'ref')
    with right:
        st.subheader('Analysis Lap')
        catalog=source_catalog(include_acgym=True)
        # Migrate the previous reference-bound B choice once, then keep the two
        # session selectors independent, including when A changes.
        previous=st.session_state.get('lap_analysis_choices',{}).get('source_b:'+identity_a,key_a)
        key_b=remembered_selectbox('Session',catalog,'source_b','independent-sessions',previous,catalog.get)
        try:
            analyzed_session=get_source(key_b)
        except (OSError,ValueError) as exc:
            st.info('Sessione analizzata non disponibile: '+str(exc));return
        st.caption(analyzed_session.metadata['filename'])
        if analyzed_session.metadata.get('time_basis'):
            st.caption('Base temporale: '+analyzed_session.metadata['time_basis'])
        lap_b,identity_b=lap_control(analyzed_session,key_b,'lap',lap_a,key_a==key_b)
    if any(reference_session.metadata.get(k)!=analyzed_session.metadata.get(k) for k in ('track_id','car_id')):
        st.warning('Reference Lap e Analysis Lap usano vetture o circuiti incompatibili. Seleziona due sessioni con la stessa vettura e lo stesso circuito.')
        st.caption('Reference: '+str(reference_session.metadata.get('track_id','non verificato'))+' · '+str(reference_session.metadata.get('car_id','non verificata'))+
                   ' | Analysis: '+str(analyzed_session.metadata.get('track_id','non verificato'))+' · '+str(analyzed_session.metadata.get('car_id','non verificata')))
        return
    if st.session_state.get('lap_analysis_pair')!=(identity_a,identity_b):
        st.session_state['lap_analysis_pair']=(identity_a,identity_b)
        st.session_state.pop('lap_analysis_corner',None)
    if lap_a is None or lap_b is None:
        st.info('Servono giri completi verificati in entrambe le sessioni. Le finestre generiche restano disponibili in Telemetry Comparison.')
        return
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
    if result.geometry is not None:
        render_chart(trajectory_figure(result),mode='xy',key='lap_analysis_geometry')
        st.caption(f"{sum(s['kind']=='corner' for s in result.geometry.sections)} curve geometriche · "
                   f"{result.geometry.length_m:.1f} m sul riferimento · raggio soglia {radius:g} m · "
                   'apice operativo: curvature-weighted apex proxy, non apice fisico verificato.')
        if not result.geometry.quality.get('seam_curvature_available',True):
            st.caption('La piccola giunzione al traguardo non verifica una tangente continua: la zona B conserva il tempo, con curvatura e tipo di curva non classificati.')
        if report.get('finish_marker'):
            st.caption('🏁 indica l’ultima posizione registrata presso il confine temporale verificato; l’eventuale zona geometrica B resta distinta e non rappresenta una linea ufficiale di arrivo.')
    if report['status']=='partial':
        st.warning('Allineamento spaziale parziale: regioni affidabili recuperate prima e dopo le zone escluse. Le transizioni incerte restano nel delta non attribuito.')
        with st.expander('Perché alcune regioni non sono disponibili'):
            alignment_diagnostics(result)
    elif report['status']!='valid':
        st.warning('Analisi spaziale non disponibile per questa coppia. Il delta giro misurato resta disponibile; il resto è classificato come delta non attribuito.')
        alignment_diagnostics(result)
    else:
        st.success('Allineamento spaziale valido nei limiti dichiarati')
    reconciliation=report['reconciliation']
    st.caption(f"Delta giro {reconciliation['final_delta_s']:+.3f} s = sezioni misurate {reconciliation['section_sum_delta_s']:+.3f} s + "
               f"delta non attribuito {reconciliation['unallocated_delta_s']:+.3f} s · errore contabile {reconciliation['error_s']:.3g} s.")
    if report['unallocated_delta']['required']:
        st.caption('Delta non attribuito — Allineamento spaziale non disponibile: residuo contabile unico, comprendente sezioni e transizioni non misurabili; non è una perdita causale o un tempo misurato di una singola regione.')
    section_table=pd.DataFrame(report['section_deltas'])
    render_chart(contribution_figure(report),mode='xy',key='lap_analysis_contributions')
    if report['status']=='unavailable':
        return
    measured_ids={s['section_id'] for s in report['section_deltas']}
    corners=[s for s in result.geometry.sections if s['kind']=='corner' and s['section_id'] in measured_ids]
    if not corners:
        st.info('Nessuna curva interamente supportata da mostrare. Restano disponibili i contributi misurabili e il delta non attribuito.')
        return
    if report['status']=='partial':
        st.caption(f'{len(corners)} curve interamente allineate ispezionabili. Ogni KPI richiede anche il supporto della propria finestra di misura.')
        st.caption('I suffissi .1, .2 identificano porzioni affidabili di una sezione; le parti escluse non hanno contributi individuali e confluiscono nel residuo unico.')
    corner_ids=[s['section_id'] for s in corners]
    if st.session_state.get('lap_analysis_corner') not in corner_ids:
        st.session_state.pop('lap_analysis_corner',None)
    selected=st.selectbox('Curva da ispezionare',corner_ids,key='lap_analysis_corner')
    section=next(s for s in corners if s['section_id']==selected)
    contribution=next(s for s in report['section_deltas'] if s['section_id']==selected)
    st.subheader(f"{selected}: {contribution['delta_s']:+.3f} s rispetto al riferimento")
    measured=next(c for c in report['corners'] if c['section_id']==selected)
    concise=[]
    labels={'brake_onset_position_m','speed_at_apex_kmh','throttle_after_apex_delay_s'}
    for metric in measured['kpis']:
        if metric['name'] in labels and metric['validity']=='valid':
            concise.append(f"{kpi_label(metric)} Δ {metric['difference']:+.2f}")
    if concise:
        st.write(' · '.join(concise))
    kpis=pd.DataFrame(measured['kpis'])
    kpis['name']=[kpi_label(m) for m in measured['kpis']]
    st.dataframe(kpis[['name','reference_value','analyzed_value','difference','validity','explanation']].rename(columns={
        'name':'KPI','reference_value':'Reference','analyzed_value':'Analyzed','difference':'Difference',
        'validity':'Quality','explanation':'Details'}),hide_index=True,width='stretch')
    delta=go.Figure(go.Scatter(x=result.trace.reference_s_m,y=result.trace.delta_s,mode='lines',connectgaps=False,name='Δ tempo B − A',
        meta=dict(unit='s',channel='Delta cumulato',tolerance=result.geometry.quality['actual_spacing_m']*.51)))
    delta.update_layout(title='Delta cumulato sul riferimento comune',xaxis_title='Posizione comune (m)',yaxis_title='Δ tempo (s)',height=350)
    _distance_axis(delta)
    render_figures([(delta,'time'),(corner_signals(result,section),'time')],key='lap_analysis_spatial_signals')
    st.caption('Geometric Corner: regione rilevata dalla soglia di raggio corrente (predefinita 150 m). Analysis Context: approccio 200 m e uscita 120 m aggiuntivi. Curvature-Weighted Apex Proxy: linea tratteggiata. Al traguardo i frammenti appartengono allo stesso giro, senza presumere continuità degli eventi.')
    with st.expander('Definizioni, finestre effettive e qualità'):
        st.dataframe(kpis[['name','definition','temporal_window_s','source_signals']].rename(columns={
            'name':'KPI','definition':'Engineering Definition','temporal_window_s':'Observed Time Windows [s]',
            'source_signals':'Source Signals'}),hide_index=True,width='stretch')
        st.json(dict(braking_events=measured['braking_events'],alignment=facts['alignment']))
        st.dataframe(section_table,hide_index=True,width='stretch')
    st.caption(f"Calcolo deterministico {report['runtime_s']:.3f} s; risultati memorizzati per sorgenti, giri e parametri. "
               'La selezione della curva e l’hover non modificano l’analisi. Differenze di input e differenze di tempo non dimostrano causalità.')
