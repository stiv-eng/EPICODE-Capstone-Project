"""Offline chart-type fixtures for optional legacy renderers (no FastF1 fetch)."""
import pandas as pd
import plotly.express as px

from motorsport_ui.hover import figure_specs


def legacy_specs():
    frame=pd.DataFrame({'Driver':['A']*6+['B']*6,'LapNumber':list(range(1,7))*2,
                        'LapTimeSeconds':[90.,91.,89.,92.,95.,90.,88.,89.,91.,90.,92.,94.],
                        'Stint':[1]*12,'TyreLife':list(range(1,7))*2})
    return figure_specs([
        (px.scatter(frame,x='LapNumber',y='LapTimeSeconds',color='Driver',hover_data=['Stint','TyreLife'],title='Offline legacy lap scatter'),'xy'),
        (px.box(frame,x='Driver',y='LapTimeSeconds',color='Driver',points='all',title='Offline legacy box distribution'),'xy'),
        (px.bar(frame.groupby('Driver',as_index=False).LapTimeSeconds.mean(),x='Driver',y='LapTimeSeconds',title='Offline legacy categorical bars'),'xy')])
