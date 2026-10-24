"""Dashboard Plotly: tempi, stint, pneumatici e regressioni lineari."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from motorsport_ui.hover import render_chart,render_figures
from motorsport_ui.analytics import clean_lap_table, driver_summary, stint_summary, degradation_regression
from motorsport_ui.common import select_session, load_selected_session

st.set_page_config(layout='wide')
st.title('Lap & Stint Analysis')
st.caption('Confronto giri, consistenza del passo e strategia pneumatici')
year, event, code = select_session('lap', default='R')
session = load_selected_session(year, event, code)
frame = clean_lap_table(session.laps)
if frame.empty:
    st.warning('Non ci sono giri validi per questa sessione.'); st.stop()
all_drivers = sorted(frame['Driver'].unique())
selected = st.multiselect('Piloti', all_drivers, default=all_drivers[:min(5, len(all_drivers))])
if not selected:
    st.info('Seleziona almeno un pilota.'); st.stop()
filtered = frame.loc[frame['Driver'].isin(selected)]
summary = driver_summary(filtered)
fastest = summary.iloc[0]
a, b, c = st.columns(3)
a.metric('Giri validi', f'{len(filtered)}')
b.metric('Miglior giro', f"{fastest['best']:.3f} s")
c.metric('Pilota più veloce', str(fastest['Driver']))

section=st.radio('Analisi legacy',['Lap times', 'Pneumatici / Stint', 'Regressione passo'],horizontal=True)
if section=='Lap times':
    fig = px.scatter(filtered, x='LapNumber', y='LapTimeSeconds', color='Driver',
                     symbol='Compound', hover_data=['Stint','TyreLife'],
                     labels={'LapNumber':'Numero giro', 'LapTimeSeconds':'Tempo sul giro (s)'},
                     title='Evoluzione tempi sul giro')
    fig.update_traces(marker={'size': 8})
    box = px.box(filtered, x='Driver', y='LapTimeSeconds', color='Driver', points='all',
                 title='Distribuzione tempi (filtrati)')
    render_figures([(fig,'xy'),(box,'xy')],key='legacy_lap_times')
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.download_button('Esporta giri CSV', filtered.to_csv(index=False).encode(),
                       file_name=f'{year}_{code}_lap_times.csv', mime='text/csv')
elif section=='Pneumatici / Stint':
    stints = stint_summary(filtered)
    fig = go.Figure()
    tyre_colors = {'SOFT': '#e94b55', 'MEDIUM': '#f0c34e', 'HARD': '#dedede',
                   'INTERMEDIATE': '#4ba56d', 'WET': '#4c9de0'}
    for _, r in stints.iterrows():
        fig.add_trace(go.Bar(name=f"{r['Driver']} {r['Compound']}",
                             x=[r['last_lap']-r['first_lap']+1], y=[r['Driver']],
                             base=[r['first_lap']-1], orientation='h',
                             marker_color=tyre_colors.get(str(r['Compound']), '#999999'),
                             customdata=[[r['Stint'], r['Compound'], r['best_s']]],
                             hovertemplate='Stint %{customdata[0]} · %{customdata[1]}<br>Best %{customdata[2]:.3f} s<extra></extra>',
                             showlegend=False))
    fig.update_layout(barmode='overlay', title='Sequenza stint (giri cronologici)',
                      xaxis_title='Numero giro', yaxis_title='Pilota')
    render_chart(fig, use_container_width=True)
    st.dataframe(stints, use_container_width=True, hide_index=True)
else:
    result = degradation_regression(filtered)
    st.caption('Fit lineare osservazionale su TyreLife all’interno di ogni stint. '
               'Traffico, carburante, safety car e condizioni pista NON sono controllati: '
               'non equivale a una stima causale del degrado pneumatici.')
    if result.empty:
        st.info('Numero insufficiente di giri validi con TyreLife per fare una regressione.');
    else:
        st.dataframe(result, use_container_width=True, hide_index=True)
        positive = result.loc[result['laps'] >= 3]
        f = px.bar(positive, x='Driver', y='slope_s_per_tyre_lap', color='Compound',
                   hover_data=['Stint', 'r2', 'laps'], barmode='group',
                   title='Pendenza tempo sul giro vs TyreLife (s/giro gomma)')
        render_chart(f, use_container_width=True)
