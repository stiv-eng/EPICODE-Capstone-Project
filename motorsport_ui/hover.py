"""Offline external readouts. Rendering never calls back into Python on hover.

The small declared component serves the installed Plotly runtime as a cacheable
local asset, rather than serializing its 4.85 MB source into every figure iframe.
Related figures can share one component/runtime through ``render_figures``.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.colors import qualitative
import streamlit.components.v1 as components


def observed_tolerance(values):
    """Nearest observed sample within 0.51 median ORIGINAL positive time step.

    Display decimation must never enlarge the permitted measurement interval.
    Large gaps and null samples therefore remain unavailable, never interpolated.
    """
    values=np.asarray(values,dtype=float)
    steps=np.diff(values)
    steps=steps[np.isfinite(steps)&(steps>0)]
    return float(np.median(steps)*.51) if len(steps) else 0.


def prepare_figure(figure,mode='xy'):
    """Copy presentation state, retaining all plotted numbers and axis geometry."""
    fig=go.Figure(figure)
    # Streamlit's native chart frontend normally resolves its sentinel palette.
    # A declared component must resolve these presentation colors itself.
    sentinel={f'#0000{i+1:02d}':color for i,color in enumerate(qualitative.Plotly)}
    fig.update_layout(template='plotly_dark')
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    for name in fig.layout:
        if name.startswith('coloraxis'):
            scale=fig.layout[name].colorscale
            if scale and any(str(color).startswith('#0000') for _,color in scale):
                fig.layout[name].colorscale='Viridis'
    selections=[]
    for index,trace in enumerate(fig.data):
        if trace.hoverinfo=='skip':
            continue
        if hasattr(trace,'line') and trace.line.color in sentinel:
            trace.line.color=sentinel[trace.line.color]
        if hasattr(trace,'marker') and isinstance(trace.marker.color,str) and trace.marker.color in sentinel:
            trace.marker.color=sentinel[trace.marker.color]
        meta=dict(trace.meta or {})
        identity=str(meta.get('selection_id',trace.legendgroup or trace.name or index))
        meta.setdefault('selection_id',identity)
        meta.setdefault('channel',trace.name or 'Serie')
        meta.setdefault('unit','')
        if mode=='time':
            meta.setdefault('tolerance',observed_tolerance(trace.x))
            times=np.asarray(trace.x,dtype=float)
            meta['ordered_time']=bool(np.isfinite(times).all() and (np.diff(times)>=0).all())
        # Preserve the meaning of existing customdata, including legacy labels.
        if trace.hovertemplate:
            meta.setdefault('readout_template',trace.hovertemplate)
        trace.update(meta=meta,hoverinfo='none',hovertemplate=None)
        color=trace.line.color if hasattr(trace,'line') else None
        if not color and hasattr(trace,'marker') and isinstance(trace.marker.color,str):
            color=trace.marker.color
        if not color:
            palette=fig.layout.colorway or fig.layout.template.layout.colorway or qualitative.Plotly
            color=palette[index%len(palette)]
            if hasattr(trace,'line'):trace.line.color=color
            if hasattr(trace,'marker') and trace.marker.color is None:trace.marker.color=color
        if color=='rgba(255,255,255,0)':color='#f5f9ff'
        if not any(s['id']==identity for s in selections):
            selections.append(dict(id=identity,label=trace.name or meta['channel'],color=color or '#63b3ff'))
    meta=dict(fig.layout.meta or {})
    meta.update(hover_mode=mode,hover_selections=selections)
    fig.update_layout(meta=meta,hovermode='x' if mode=='time' else 'closest')
    fig.update_xaxes(showspikes=False)
    fig.update_yaxes(showspikes=False)
    return fig


def figure_specs(figures):
    return [json.loads(prepare_figure(fig,mode).to_json()) for fig,mode in figures]


@lru_cache(maxsize=1)
def component():
    html=Path(__file__).with_name('hover.html').read_text(encoding='utf-8')
    runtime=get_plotlyjs()
    runtime_file='plotly.'+hashlib.sha256(runtime.encode()).hexdigest()[:16]+'.min.js'
    html=html.replace('plotly.min.js',runtime_file)
    version=hashlib.sha256((html+runtime).encode()).hexdigest()[:16]
    directory=Path(tempfile.gettempdir())/'motorsport-hover'/version
    directory.mkdir(parents=True,exist_ok=True)
    for name,content in [('index.html',html),(runtime_file,runtime)]:
        path=directory/name
        if not path.exists():
            path.write_text(content,encoding='utf-8',newline='\n')
    return components.declare_component('motorsport_hover',path=str(directory))


def render_figures(figures,*,key=None):
    specs=figure_specs(figures)
    height=sum(int(s['layout'].get('height',450)) for s in specs)+24*max(0,len(specs)-1)
    component()(specs=specs,height=height,key=key,default=None)


def render_chart(figure,*,mode='xy',key=None,**_compat):
    render_figures([(figure,mode)],key=key)
