"""Bounded SVG figures avoid accumulating browser WebGL contexts on long pages."""
import hashlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale, qualitative
from plotly.subplots import make_subplots

from motorsport.analytics.channels import signal_unit
from motorsport.analytics.session_metrics import chart_sample
from motorsport.analytics.timebase import chart_values, numeric
from .hover import observed_tolerance


SELECTION_COLORS=['#63b3ff','#ff8c42','#56e39f','#ff6b9d','#d5b8ff','#ffd166','#45d5e8','#ffffff']


def selection_color(identity):
    index=int(hashlib.sha256(identity.encode()).hexdigest()[:8],16)%len(SELECTION_COLORS)
    return SELECTION_COLORS[index]


def session_label(session):
    if 'recording_order' in session.metadata:
        return f"ACGym {session.metadata['filename'].split(' / ')[0]} · stint {session.metadata['recording_order']}"
    return session.metadata['filename']


def comparison_figure(selections, channels, axis, axis_label, session):
    fig=make_subplots(rows=len(channels),cols=1,shared_xaxes=True,
                      subplot_titles=[f'{c} · {signal_unit(session,c)}' for c in channels])
    used=set()
    for slot,(source_identity,label,view) in enumerate(selections):
        identity=f'{slot}:{source_identity}'
        color=selection_color(identity)
        # Deterministic collision resolution for the two compared selections.
        if color in used:
            color=next(c for c in SELECTION_COLORS if c not in used)
        used.add(color)
        sample=chart_sample(view,channels,max_points=5000)
        for row,channel in enumerate(channels,1):
            fig.add_trace(go.Scatter(x=sample[axis],y=chart_values(view,sample,channel,axis),
                name=label,legendgroup=identity,showlegend=row==1,mode='lines',
                line=dict(color=color),connectgaps=False,hoverinfo='none',customdata=[[str(i)] for i in sample.index],
                meta=dict(channel=channel,unit=signal_unit(session,channel),selection_id=identity,
                          source_identity=source_identity,sample_label='Campione sorgente',
                          tolerance=observed_tolerance(view[axis]))),row=row,col=1)
            fig.update_yaxes(title_text=signal_unit(session,channel),row=row,col=1)
    fig.update_layout(template='plotly_dark',height=max(350,220*len(channels)),
                      hovermode='x',legend=dict(orientation='h',y=1.10,yanchor='bottom'),
                      margin=dict(t=140),uirevision='comparison',
                      meta=dict(comparison_axis=axis,selection_labels=[label for _,label,_ in selections]))
    fig.update_xaxes(title_text=axis_label,row=len(channels),col=1)
    return fig


def trajectory_figure(segments, frame, channel, unit='source unit'):
    fig=go.Figure()
    if segments.empty:
        return fig
    values=numeric(segments,'value');finite=np.isfinite(values)
    # Scale uses ALL measurements, including extremes omitted by simplification.
    measured=numeric(frame,channel) if channel else np.array([])
    measured=measured[np.isfinite(measured)]
    unique=np.unique(measured)
    discrete=(len(unique)>0 and len(unique)<=12 and
              (channel=='gear' or unit in ('integer','identifier') or
               (channel in frame and pd.api.types.is_bool_dtype(frame[channel]))))
    groups=[]
    if discrete:
        for i,value in enumerate(unique):
            groups.append((values==value,qualitative.Safe[i%len(qualitative.Safe)],f'{channel} = {value:g} {unit}',True))
    elif len(measured):
        low,high=float(measured.min()),float(measured.max())
        cmin,cmax=(low,high) if low<high else (low-.5,high+.5)
        bins=np.zeros(len(values),dtype=int)
        bins[finite]=np.clip(((values[finite]-cmin)/(cmax-cmin)*32).astype(int),0,31)
        for index in np.unique(bins[finite]):
            groups.append((finite&(bins==index),sample_colorscale('Turbo',[(index+.5)/32])[0],channel,False))
        # A zero-size SVG marker supplies a real continuous scale without a
        # second visible point cloud. No measured extremes are clipped.
        fig.add_trace(go.Scatter(x=[None,None],y=[None,None],mode='markers',showlegend=False,
            marker=dict(color=[low,high],cmin=cmin,cmax=cmax,colorscale='Turbo',showscale=True,
                        colorbar=dict(title=f'{channel} · {unit}'),size=0),hoverinfo='skip'))
    if (~finite).any():
        groups.append((~finite,'#7b8494','Colore non disponibile',True))
    for mask,color,name,legend in groups:
        group=segments.loc[mask]
        if group.empty:
            continue
        xs=np.c_[group.x0,group.x1,np.full(len(group),np.nan)].ravel()
        ys=np.c_[group.y0,group.y1,np.full(len(group),np.nan)].ravel()
        # Endpoint readouts must refer to that endpoint's actual source sample,
        # not repeat the segment-start color value at its far endpoint.
        offsets=np.c_[group.start,group.end,group.start].astype(int).ravel()
        values=numeric(frame,channel) if channel else np.full(len(frame),np.nan)
        custom=[[str(frame.index[i]),float(values[i])] for i in offsets]
        fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',line=dict(color=color,width=3),
            name=name,showlegend=legend,connectgaps=False,customdata=custom,
            hovertemplate=f'Campione sorgente %{{customdata[0]}}<br>x=%{{x:.2f}}<br>y=%{{y:.2f}}<br>{channel or "value"}=%{{customdata[1]}} {unit}<extra></extra>'))
    fig.update_layout(template='plotly_dark',height=620,legend=dict(orientation='h'),
                      margin=dict(t=35),uirevision='trajectory')
    fig.update_yaxes(scaleanchor='x',scaleratio=1)
    return fig
