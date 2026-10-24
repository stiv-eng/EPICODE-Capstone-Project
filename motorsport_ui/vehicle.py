"""A small vector car in Plotly pixel-sized shapes, anchored to actual XY.

    +X is the artwork's front. Rotate vertices in mathematical XY; Plotly's
    pixel-sized shapes handle the SVG downward screen Y convention. Pixel sizing
    keeps the car recognizable at every data zoom level without a bitmap asset.
"""
import numpy as np
import plotly.graph_objects as go


def add_vehicle(fig,x,y,theta,description):
    if theta is None:
        fig.add_trace(go.Scatter(x=[x],y=[y],mode='markers',name='Veicolo · direzione N/D',
            marker=dict(size=14,color='#fff',line=dict(color='#17202c',width=3)),
            hovertemplate=description+'<br>X=%{x:.3f}<br>Y=%{y:.3f}<extra></extra>'))
        return fig
    cosine,sine=np.cos(theta),np.sin(theta)
    rotation=np.array([[cosine,-sine],[sine,cosine]])
    pieces=[([(-12,-5),(7,-5),(13,-3),(13,3),(7,5),(-12,5)],'#f5f9ff','#132238'),
            ([(1,-3),(7,-3),(9,-2),(9,2),(7,3),(1,3)],'#49c4f5','#132238')]
    for longitudinal in (-7,7):
        for lateral in (-7,7):
            pieces.append(([(longitudinal-3,lateral-2),(longitudinal+3,lateral-2),
                            (longitudinal+3,lateral+2),(longitudinal-3,lateral+2)],'#192433','#dceaff'))
    for vertices,fill,line in pieces:
        points=np.asarray(vertices) @ rotation.T
        path='M '+' L '.join(f'{px:.5f},{py:.5f}' for px,py in points)+' Z'
        fig.add_shape(type='path',path=path,xref='x',yref='y',xsizemode='pixel',ysizemode='pixel',
                      xanchor=float(x),yanchor=float(y),fillcolor=fill,line=dict(color=line,width=1.2),layer='above')
    fig.add_trace(go.Scatter(x=[x],y=[y],mode='markers',name='Veicolo selezionato',
        marker=dict(size=12,color='rgba(255,255,255,0)'),
        hovertemplate=description+'<br>X=%{x:.3f}<br>Y=%{y:.3f}<extra></extra>'))
    return fig
