"""One local/upload selector and explicit, cached source mapping for the explorer."""
import hashlib
from pathlib import Path
import streamlit as st
from motorsport.pipeline import load_session
from motorsport.processing.schema import CANONICAL, CANONICAL_UNITS, SUPPLIED_V04, SourceProfile
from .telemetry import select_telemetry, register_session


@st.cache_data(show_spinner=False,max_entries=3)
def mapped_session(content, filename, profile_name, columns, units, signature=()):
    return load_session(content, filename, SourceProfile(profile_name,columns,units))


def upload_session(content,filename):
    from .telemetry import SUPPLIED_HASH
    audited=hashlib.sha256(content).hexdigest()==SUPPLIED_HASH
    profile=SUPPLIED_V04 if audited else CANONICAL
    session=mapped_session(content,filename,profile.name,profile.columns,profile.units)
    if audited:
        session.metadata.update(position_provenance='integrated velocity; drift and accuracy unverified',
                                time_basis='simulator timestamp; repeated values retained')
    return session


def explorer_source():
    kind=st.radio('Sorgente',['Dataset locale','Carica file'],horizontal=True,key='explorer_source_kind')
    selected=None
    if kind=='Carica file':
        upload=st.file_uploader('Telemetria Parquet o CSV',type=['parquet','csv'],key='explorer_upload')
        if upload is None:
            st.info('Carica un file per visualizzare i suoi canali. I file caricati restano in memoria.');st.stop()
        content,filename=upload.getvalue(),upload.name
        key='upload:'+hashlib.sha256(content+filename.encode()).hexdigest()
        try:
            from .telemetry import get_source
            session=(get_source(key) if key in st.session_state.get('telemetry_registry',{}) else
                     upload_session(content,filename))
        except Exception as exc:
            st.error(f'Impossibile leggere il dataset: {exc}');st.stop()
    else:
        session=select_telemetry('explorer')
        key=st.session_state['telemetry_active_key']
        filename=session.metadata['filename']
        if not key.startswith(('acgym:','upload:')) and Path(key).is_file():
            selected=Path(key)
        content=str(selected) if selected else None
    if selected or kind=='Carica file':
        audited=session.metadata['normalization']['profile']==SUPPLIED_V04.name
        profile_label=st.selectbox('Profilo sorgente',
            ['Canonico / mappatura manuale','Dataset allegato v0.4 (unità verificate)'],
            index=1 if audited else 0,key='explorer_profile_'+key)
        base=SUPPLIED_V04 if profile_label.startswith('Dataset allegato') else CANONICAL
        with st.expander('Mappatura colonne e unità'):
            st.caption('Dichiara solo unità note. I canali originali sono preservati. Applica per caricare una mappatura diversa.')
            with st.form('source_mapping'):
                options=['— assente —']+list(session.raw.columns)
                columns={};units=dict(base.units)
                targets=['elapsed_s','speed_kmh','throttle_pct','brake_pct','steering','rpm','gear','g_lat','g_lon','pos_x','pos_y','distance_m']
                normalization=session.metadata['normalization']
                mappings=normalization['mappings'] if normalization['profile'] in (base.name,'Manual mapping') else {}
                for target in targets:
                    default=mappings.get(target,{}).get('source',base.columns.get(target,target))
                    choice=st.selectbox(target,options,index=options.index(default) if default in options else 0,
                                        key=f'{filename}_{base.name}_{target}')
                    columns[target]=choice if choice!=options[0] else '__unavailable__'
                for target,choices in [('elapsed_s',['s','ms','us','ns','datetime']),('speed_kmh',['km/h','m/s']),
                                       ('throttle_pct',['%','fraction']),('brake_pct',['%','fraction'])]:
                    default=mappings.get(target,{}).get('source_unit',base.units.get(target,CANONICAL_UNITS[target]))
                    units[target]=st.selectbox('Unità sorgente · '+target,choices,
                        index=choices.index(default) if default in choices else 0,key=f'{filename}_{base.name}_{target}_unit')
                apply=st.form_submit_button('Applica mappatura')
            if apply:
                try:
                    from .telemetry import source_signature
                    session=mapped_session(content,filename,'Manual mapping',columns,units,source_signature(key))
                except Exception as exc:
                    st.error(f'Mappatura non valida: {exc}');st.stop()
    register_session(session,key)
    return session
