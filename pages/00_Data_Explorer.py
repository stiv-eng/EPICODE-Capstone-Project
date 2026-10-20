"""Explore real telemetry with explicit units and bounded Plotly traces."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from motorsport.pipeline import load_session
from motorsport.processing.schema import CANONICAL, CANONICAL_UNITS, SUPPLIED_V04, SourceProfile
from motorsport.analytics.session_metrics import chart_sample

ROOT = Path(__file__).resolve().parents[1]
AUDITED_SHA256 = 'fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7'


@st.cache_data(show_spinner=False, max_entries=3)
def local_session(path, modified_ns, size, profile_name, columns, units):
    # mtime/size participate in the cache key; conversion options are explicit.
    return load_session(path, profile=SourceProfile(profile_name, columns, units))


@st.cache_data(show_spinner=False, max_entries=2)
def uploaded_session(content, filename, profile_name, columns, units):
    return load_session(content, filename, SourceProfile(profile_name, columns, units))


@st.cache_data(show_spinner=False, max_entries=4)
def is_audited(path, modified_ns, size):
    import hashlib
    with open(path, 'rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest() == AUDITED_SHA256


st.title('Data Explorer')
st.caption('Telemetria locale · qualità dei dati · segnali e posizione')
local_files = sorted(p for folder in [ROOT/'data/raw', ROOT/'data/demo']
                     for p in folder.glob('*') if p.suffix.lower() in {'.parquet', '.csv'})
source_kind = st.radio('Sorgente', ['Dataset locale', 'Carica file'], horizontal=True)
content, filename, selected = None, None, None
audited = False
if source_kind == 'Dataset locale':
    if not local_files:
        st.info('Inserisci un file Parquet o CSV in data/raw/ oppure scegli Carica file.')
        st.stop()
    selected = st.selectbox('Dataset locale', local_files,
                            format_func=lambda p: str(p.relative_to(ROOT)))
    filename = selected.name
    stat = selected.stat()
    audited = is_audited(str(selected), stat.st_mtime_ns, stat.st_size)
else:
    upload = st.file_uploader('Telemetria Parquet o CSV', type=['parquet', 'csv'])
    if upload is None:
        st.info('Carica un file per visualizzare i suoi canali. I file caricati restano in memoria.')
        st.stop()
    content, filename = upload.getvalue(), upload.name

profile_label = st.selectbox('Profilo sorgente',
    ['Canonico / mappatura manuale', 'Dataset allegato v0.4 (unità verificate)'],
    index=1 if audited else 0)
base_profile = SUPPLIED_V04 if profile_label.startswith('Dataset allegato') else CANONICAL
if base_profile == SUPPLIED_V04:
    st.caption('timestamp → secondi; throttle/brake 0–1 → percentuali; '
               'rpms → rpm; pos_z → pos_y. Sterzo e coordinate conservano le unità sorgente.')
else:
    st.caption('Sono riconosciuti i nomi canonici. Per altri schemi dichiara colonne e unità qui sotto.')

try:
    if selected:
        session = local_session(str(selected), stat.st_mtime_ns, stat.st_size,
                                base_profile.name, base_profile.columns, base_profile.units)
    else:
        session = uploaded_session(content, filename, base_profile.name,
                                   base_profile.columns, base_profile.units)
except Exception as exc:
    st.error(f'Impossibile leggere il dataset: {exc}')
    st.stop()

with st.expander('Mappatura colonne e unità'):
    st.write('Modifica solo le corrispondenze di cui conosci le unità. '
             'I canali aggiuntivi rimangono disponibili nel loro formato originale.')
    with st.form('source_mapping'):
        options = ['— assente —'] + list(session.raw.columns)
        targets = ['elapsed_s', 'speed_kmh', 'throttle_pct', 'brake_pct', 'steering',
                   'rpm', 'gear', 'g_lat', 'g_lon', 'pos_x', 'pos_y', 'distance_m']
        chosen_columns, chosen_units = {}, dict(base_profile.units)
        for target in targets:
            default = base_profile.columns.get(target, target)
            choice = st.selectbox(target, options, index=options.index(default) if default in options else 0,
                                  key=f'{filename}_{base_profile.name}_{target}')
            chosen_columns[target] = choice if choice != options[0] else '__unavailable__'
        for target, units in [('elapsed_s', ['s', 'ms', 'us', 'ns', 'datetime']),
                              ('speed_kmh', ['km/h', 'm/s']),
                              ('throttle_pct', ['%', 'fraction']), ('brake_pct', ['%', 'fraction'])]:
            default = base_profile.units.get(target, CANONICAL_UNITS[target])
            chosen_units[target] = st.selectbox(f'Unità sorgente · {target}', units,
                index=units.index(default), key=f'{filename}_{base_profile.name}_{target}_unit')
        apply = st.form_submit_button('Applica mappatura')
    mapping_key = (filename, base_profile.name, stat.st_mtime_ns if selected else hash(content))
    if apply:
        st.session_state['telemetry_mapping'] = (mapping_key, chosen_columns, chosen_units)

custom = st.session_state.get('telemetry_mapping')
if custom and custom[0] == mapping_key:
    try:
        if selected:
            session = local_session(str(selected), stat.st_mtime_ns, stat.st_size,
                                    'Manual mapping', custom[1], custom[2])
        else:
            session = uploaded_session(content, filename, 'Manual mapping', custom[1], custom[2])
    except Exception as exc:
        st.error(f'Mappatura non valida: {exc}')
        st.stop()

data, quality, metrics = session.data, session.quality, session.metrics
a, b, c, d = st.columns(4)
a.metric('Campioni', f'{len(data):,}')
b.metric('Canali sorgente', len(session.raw.columns))
duration = metrics.get('duration_s')
c.metric('Durata', f'{duration:.2f} s' if duration is not None else 'Non disponibile')
speed = metrics.get('speed_kmh_max')
d.metric('Velocità massima', f'{speed:.1f} km/h' if speed is not None else 'Non disponibile')
st.caption('Medie dei segnali calcolate sui campioni completi; non sono medie pesate sul tempo.')

overview, signals, position, laps = st.tabs(['Dataset e qualità', 'Segnali', 'Posizione', 'Giri'])
with overview:
    with st.expander('Metadati e normalizzazione'):
        st.json(session.metadata)
    raw_q = session.raw_quality
    st.write(f"Sorgente: **{raw_q['missing_cells']}** valori mancanti · "
             f"**{raw_q['infinite_cells']}** valori infiniti · **{raw_q['duplicate_rows']}** righe duplicate")
    if raw_q['constant_channels']:
        st.info('Canali costanti: ' + ', '.join(raw_q['constant_channels']))
    if quality['time']:
        time = quality['time']
        rate = time['observed_rate_hz']
        st.write(f"Frequenza media osservata: {rate:.2f} Hz" if rate else 'Frequenza non disponibile')
        if time['duplicate_values'] or time['backward_steps'] or time['large_gaps'] or time['missing_or_nonfinite']:
            st.warning(f"Tempo: {time['duplicate_values']} valori ripetuti, "
                       f"{time['backward_steps']} passi all'indietro, {time['large_gaps']} lacune, "
                       f"{time['missing_or_nonfinite']} valori invalidi. Ordine e righe sorgente sono conservati.")
        with st.expander('Diagnostica temporale'):
            st.json(time)
    for note in session.metadata['normalization']['notes']:
        st.caption(note)
    st.write('Qualità canali normalizzati (include i segnali sorgente preservati)')
    st.dataframe(pd.DataFrame(quality['channels']), hide_index=True, width='stretch')
    st.caption('Fuori soglia: limiti ampi di plausibilità; outlier IQR: oltre 3×IQR, '
               'solo segnalazione esplorativa. Nessuna riga viene eliminata automaticamente.')
    st.write('Anteprima sorgente · primi 100 campioni')
    st.dataframe(session.raw.head(100), width='stretch')
    with st.expander('Anteprima canonica e metriche'):
        st.dataframe(data.head(100), width='stretch')
        st.json(metrics)

with signals:
    expected = ['speed_kmh', 'throttle_pct', 'brake_pct', 'steering', 'rpm', 'gear']
    missing = [c for c in expected if c not in data]
    if missing:
        st.info('Canali canonici assenti: ' + ', '.join(missing) + '. Usa la mappatura se presenti con altri nomi.')
    numeric = list(data.select_dtypes(include='number').columns)
    selected_channels = st.multiselect('Segnali da visualizzare', numeric,
        default=[c for c in expected if c in numeric][:4], max_selections=8)
    view = data
    if len(data) > 1:
        start, end = st.slider('Intervallo campioni', 0, len(data)-1, (0, len(data)-1))
        view = data.iloc[start:end+1]
    if selected_channels and len(view):
        chart = chart_sample(view, selected_channels, max_points=5000)
        x = chart['elapsed_s'] if 'elapsed_s' in chart else chart.index
        fig = make_subplots(rows=len(selected_channels), cols=1, shared_xaxes=True,
                            subplot_titles=selected_channels, vertical_spacing=.04)
        for row, channel in enumerate(selected_channels, 1):
            fig.add_trace(go.Scattergl(x=x, y=chart[channel], name=channel,
                                      mode='lines', connectgaps=False), row=row, col=1)
            unit = CANONICAL_UNITS.get(channel, 'unità sorgente')
            fig.update_yaxes(title_text=unit, row=row, col=1)
        fig.update_xaxes(title_text='Tempo trascorso (s)' if 'elapsed_s' in chart else 'Indice campione',
                         row=len(selected_channels), col=1)
        fig.update_layout(template='plotly_dark', height=max(350, 210*len(selected_channels)),
                          showlegend=False, margin=dict(t=40, b=30))
        st.plotly_chart(fig, width='stretch')
        st.caption(f'{len(chart):,} punti visualizzati su {len(view):,}; '
                   'campionamento per estremi, senza ridurre i dati usati nei calcoli.')
    else:
        st.info('Seleziona almeno un segnale numerico disponibile.')

with position:
    if {'pos_x', 'pos_y'}.issubset(data):
        coordinates = data[['pos_x', 'pos_y']].to_numpy(dtype=float, na_value=np.nan)
        valid = np.isfinite(coordinates).all(axis=1)
        if valid.sum() >= 3 and np.ptp(coordinates[valid], axis=0).min() > 0:
            trace = chart_sample(data, ['pos_x', 'pos_y'], max_points=5000)
            color = trace['speed_kmh'] if 'speed_kmh' in trace and trace.speed_kmh.notna().all() else None
            fig = go.Figure(go.Scattergl(x=trace.pos_x, y=trace.pos_y, mode='markers',
                marker=dict(size=3, color=color, colorscale='Turbo', showscale=color is not None,
                            colorbar=dict(title='km/h')), name='Posizione'))
            fig.update_layout(template='plotly_dark', height=550, xaxis_title='pos_x · unità sorgente',
                              yaxis_title='pos_y · unità sorgente')
            fig.update_yaxes(scaleanchor='x', scaleratio=1)
            st.plotly_chart(fig, width='stretch')
            st.warning('Traccia in coordinate sorgente: accuratezza, deriva e linea del traguardo '
                       'non certificate. La forma da sola non valida i giri.')
        else:
            st.info('Posizioni insufficienti, non finite o costanti: traccia XY non disponibile.')
    else:
        st.info('Posizione XY non disponibile: servono pos_x e pos_y. È possibile mappare pos_z se appropriato.')

with laps:
    if not session.laps.available:
        st.info('Analisi sui giri non disponibile. ' + session.laps.reason)
        st.write('Puoi continuare a esplorare tutti i segnali a livello di sessione.')
    else:
        st.success(session.laps.reason)
        st.dataframe(session.laps.laps, hide_index=True, width='stretch')
        lap_id = st.selectbox('Giro validato', session.laps.laps.lap_id.to_list())
        lap = data.loc[data['lap_id'].eq(lap_id).fillna(False)]
        channels = [c for c in ['speed_kmh', 'throttle_pct', 'brake_pct'] if c in lap]
        chart = chart_sample(lap, channels)
        if channels:
            fig = make_subplots(rows=len(channels), cols=1, shared_xaxes=True, subplot_titles=channels)
            for row, channel in enumerate(channels, 1):
                fig.add_trace(go.Scattergl(x=chart.lap_elapsed_s, y=chart[channel], name=channel), row=row, col=1)
            fig.update_layout(template='plotly_dark', height=210*len(channels), showlegend=False)
            fig.update_xaxes(title_text='Tempo nel giro (s)', row=len(channels), col=1)
            st.plotly_chart(fig, width='stretch')
