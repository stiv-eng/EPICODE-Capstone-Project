"""Mappa circuito e velocita' - traccia XY da FastF1 con Plotly."""
import plotly.graph_objects as go
import streamlit as st
from motorsport_ui.common import select_session, load_selected_session, lap_choices

st.set_page_config(layout='wide')
st.title('Track Map & Speed')
st.caption('Visualizzazione della posizione XY lungo il tracciato e distribuzione velocità')
year, event, code = select_session('map', default='Q')
session = load_selected_session(year, event, code)
drivers = sorted(session.laps['Driver'].dropna().astype(str).unique())
if not drivers:
    st.warning('Nessun pilota disponibile.'); st.stop()
driver = st.selectbox('Pilota', drivers)
laps = lap_choices(session, driver)
if not laps:
    st.warning('Nessun giro cronometrato.'); st.stop()
idx = st.selectbox('Giro', range(len(laps)), format_func=lambda i: laps[i][0])
try:
    telemetry = laps[idx][1].get_telemetry().dropna(subset=['X', 'Y', 'Speed']).copy()
except Exception as exc:
    st.error(f'Posizioni telemetriche non disponibili: {exc}'); st.stop()
if len(telemetry) < 5:
    st.warning('Dati XY insufficienti per disegnare il circuito.'); st.stop()
fig = go.Figure()
fig.add_trace(go.Scatter(x=telemetry['X'], y=telemetry['Y'], mode='lines',
                         line={'color': '#4f5867', 'width': 9}, name='Tracciato'))
fig.add_trace(go.Scatter(x=telemetry['X'], y=telemetry['Y'], mode='markers',
                         marker={'size': 5, 'color': telemetry['Speed'], 'colorscale': 'Turbo',
                                 'showscale': True, 'colorbar': {'title': 'km/h'}},
                         hovertemplate='X=%{x:.0f} · Y=%{y:.0f}<br>Velocità=%{marker.color:.0f} km/h<extra></extra>',
                         name='Velocità'))
fig.update_layout(height=720, title=f'{event} · {driver} · giro {int(laps[idx][1]["LapNumber"])}',
                  xaxis={'visible': False, 'scaleanchor': 'y', 'scaleratio': 1},
                  yaxis={'visible': False}, showlegend=False,
                  margin={'t': 60, 'l': 15, 'r': 15, 'b': 15})
st.plotly_chart(fig, use_container_width=True)
st.caption('Le coordinate X/Y di FastF1 sono relative alla pista, non coordinate geografiche GPS. '
           'La mappa dipende dalla qualità del segnale di posizione disponibile.')