"""Equal numeric scale, full finite extent, and constrained square data domain."""
import numpy as np
import plotly.express as px

from motorsport.analytics.channels import signal_unit,paired_channels,usable_channels
from motorsport.analytics.timebase import numeric
from motorsport.analytics.session_metrics import chart_sample


def gg_figure(session,frame):
    if not paired_channels(frame,'g_lat','g_lon'):
        return None
    lat,lon=signal_unit(session,'g_lat'),signal_unit(session,'g_lon')
    if lat.lower()!=lon.lower():
        return None  # Different or unverified incompatible scales cannot form a physical G-G diagram.
    extent=np.r_[numeric(frame,'g_lat'),numeric(frame,'g_lon')]
    finite=extent[np.isfinite(extent)]
    radius=max(float(np.abs(finite).max())*1.05,1e-6) if len(finite) else 1.
    if radius<1e-5:
        radius=1.
    sample=chart_sample(frame,['g_lat','g_lon'],max_points=3500)
    sample=sample.assign(**{'Campione sorgente':sample.index.astype(str)})
    fig=px.scatter(sample,x='g_lat',y='g_lon',render_mode='svg',opacity=.55,hover_data=['Campione sorgente'],
        color='speed_kmh' if 'speed_kmh' in usable_channels(frame,['speed_kmh']) else None,
        title='Diagramma G-G · '+('g' if lat.lower()=='g' else 'scala sorgente'),template='plotly_dark',
        labels={'g_lat':f'Accelerazione laterale ({lat})','g_lon':f'Accelerazione longitudinale ({lon})',
                'speed_kmh':'Velocità (km/h)'})
    fig.update_layout(height=620,margin=dict(l=70,r=70,t=70,b=70),uirevision='gg_equal_scale')
    fig.update_xaxes(range=[-radius,radius],constrain='domain',constraintoward='center')
    fig.update_yaxes(range=[-radius,radius],scaleanchor='x',scaleratio=1,constrain='domain',constraintoward='middle')
    return fig
