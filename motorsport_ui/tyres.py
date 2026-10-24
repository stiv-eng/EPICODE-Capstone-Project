"""Four-corner source telemetry; no inferred wear or setup causality."""
import pandas as pd
import streamlit as st

from motorsport.analytics.channels import TYRE_FAMILIES,corner_channels,signal_unit
from motorsport.analytics.timebase import weighted_signal
from motorsport_ui.telemetry import signal_chart,metric_export


def render_tyres(session, frame):
    family=st.selectbox('Famiglia pneumatici',list(TYRE_FAMILIES))
    corners=corner_channels(frame,TYRE_FAMILIES[family])
    if family=='Wheel speed' and not corners:
        corners=corner_channels(frame,'wheel_rps')
    if not corners:
        st.info('Famiglia non disponibile in questo dataset. Nessun segnale sostitutivo viene generato.')
        return
    chosen=st.multiselect('Ruote',list(corners),default=list(corners))
    channels=[corners[c] for c in chosen]
    signal_chart(frame,channels,session,key='tyres_signals')
    table=pd.DataFrame([{'corner':corner,'channel':corners[corner],'unit':signal_unit(session,corners[corner]),
                        **weighted_signal(frame,corners[corner])} for corner in chosen])
    st.dataframe(table,hide_index=True,width='stretch')
    metric_export(table,'tyre_metrics.csv','tyre_csv')
    st.caption('FL/FR/RL/RR: anteriore sinistra/destra, posteriore sinistra/destra. '
               'I segnali sono riportati dalla sorgente; wear non viene reinterpretato come perdita di prestazione. '
               'Differenze termiche o correlazioni con i carichi non dimostrano degrado o causalità del setup.')
    if any(c.startswith('wheel_rps') for c in channels):
        st.caption('Velocità rotazionale GT7 con segno sorgente: negativa in avanzamento. Non è convertita in velocità lineare della ruota.')
