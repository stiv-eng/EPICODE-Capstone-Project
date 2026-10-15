"""Telemetria di due giri - distanza allineata senza utilizzare dati esterni."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from motorsport_ui.analytics import sampled_car_data, telemetry_delta
from motorsport_ui.common import select_session, load_selected_session, lap_choices

st.set_page_config(layout='wide')
st.title('Telemetry Comparison')
st.caption('Speed · Throttle · Brake · RPM · Gear · Delta tempo cumulato')
year, event, code = select_session('tel', default='Q')
session = load_selected_session(year, event, code)
drivers = sorted(session.laps['Driver'].dropna().astype(str).unique())
if not drivers:
    st.warning('Nessun pilota disponibile.'); st.stop()
left, right = st.columns(2)
selection = []
for col, label, index in [(left, 'Giro A (riferimento)', 0), (right, 'Giro B', min(1, len(drivers)-1))]:
    with col:
        d = st.selectbox(f'Pilota · {label}', drivers, index=index, key=f'{label}_driver')
        laps = lap_choices(session, d)
        if not laps:
            st.warning(f'Nessun giro disponibile per {d}'); st.stop()
        i = st.selectbox(label, range(len(laps)), format_func=lambda j, rows=laps: rows[j][0],
                         key=f'{label}_lap')
        selection.append((d, laps[i][1]))
try:
    a = sampled_car_data(selection[0][1]); b = sampled_car_data(selection[1][1])
except Exception as exc:
    st.error(f'Telemetria non disponibile: {exc}'); st.stop()
if a.empty or b.empty:
    st.warning('Campioni telemetrici insufficienti.'); st.stop()

colors = ['#26a9ff', '#f7805c']
labels = [f'{d} · Lap {int(l["LapNumber"])}' for d, l in selection]
fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.035,
                    row_heights=[0.32, 0.17, 0.17, 0.17, 0.17],
                    subplot_titles=['Velocità (km/h)', 'Acceleratore (%)', 'Freno', 'RPM', 'Marcia'])
for idx, telemetry in enumerate((a, b)):
    for row, key in enumerate(['Speed', 'Throttle', 'Brake', 'RPM', 'nGear'], start=1):
        y = telemetry[key].astype(float) if key != 'Brake' else telemetry[key].fillna(False).astype(float)
        fig.add_trace(go.Scatter(x=telemetry['Distance'], y=y, name=labels[idx],
                                 line_color=colors[idx], mode='lines', legendgroup=labels[idx],
                                 showlegend=row == 1), row=row, col=1)
fig.update_layout(height=850, hovermode='x unified', margin={'t': 65})
fig.update_xaxes(title_text='Distanza (m)', row=5, col=1)
st.plotly_chart(fig, use_container_width=True)

delta = telemetry_delta(a, b)
if not delta.empty:
    chart = go.Figure(go.Scatter(x=delta['Distance'], y=delta['delta_s'],
                                 line_color='#e98065', name='B − A'))
    chart.add_hline(y=0, line_dash='dash')
    chart.update_layout(title='Delta cumulato B − A · positivo = B più lento',
                        xaxis_title='Distanza (m)', yaxis_title='Differenza (s)', height=300)
    st.plotly_chart(chart, use_container_width=True)
    st.caption('Delta ottenuto per interpolazione della telemetria temporale sullo stesso '
               'asse distanza integrata. È un’approssimazione, non un timing ufficiale.')