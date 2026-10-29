"""On-demand local coach; ordinary rendering never contacts the model server."""
import streamlit as st

from motorsport.coaching import DEFAULT_URL,CoachingError,LMStudioClient,cache_key,prepare_input,present_input


LIMITS={
    'reference_not_optimal':('Il riferimento non è una guida teoricamente ottimale.','The reference is not theoretically optimal driving.'),
    'association_not_causation':('Le differenze osservate non dimostrano le cause del delta; i consigli sono ipotesi da provare.','Observed differences do not establish causes of the delta; advice is a hypothesis to test.'),
    'incomplete_alignment':('Allineamento incompleto: solo le sezioni supportate hanno differenze misurate.','Incomplete alignment: only supported sections have measured differences.'),
    'unallocated_not_causal':('Il delta non attribuito è un unico residuo contabile, senza cause individuali assegnate.','Unallocated delta is one accounting remainder, without individual causes assigned.'),
    'excluded_kpis':('KPI incerti o non disponibili esclusi dalle evidenze e dai consigli.','Uncertain or unavailable KPIs are excluded from evidence and advice.'),
    'no_supported_technique':('Evidenze KPI insufficienti per suggerire tecniche specifiche.','Insufficient KPI evidence to suggest specific techniques.'),
}
ITALIAN_METRICS={
    'brake_onset_position_m':'Posizione inizio frenata',
    'braking_distance_m':'Distanza di frenata',
    'braking_duration_s':'Durata frenata',
    'speed_at_apex_kmh':'Velocità al proxy di apice',
    'minimum_corner_speed_kmh':'Velocità minima in curva',
    'entry_speed_kmh':'Velocità ingresso curva',
    'steering_rms_rate':'Velocità RMS dello sterzo (proxy regolarità)',
    'peak_absolute_steering':'Picco assoluto sterzo',
    'steering_at_apex':'Sterzo al proxy di apice',
    'throttle_after_apex_delay_s':'Ritardo riapertura acceleratore',
    'throttle_at_apex_pct':'Acceleratore al proxy di apice',
    'maximum_exit_throttle_pct':'Picco acceleratore in uscita',
}


def render_evidence(compact,language,labels):
    """Keep Python's measured evidence and limitations visible separately from AI prose."""
    compact=present_input(compact)
    it=language=='it';laps=compact['laps']
    with st.expander('Misure e limiti forniti al coach' if it else 'Measurements and limitations supplied to the coach'):
        st.write(f"Reference {laps['reference_id']}: {laps['reference_time_s']} s · "
                 f"Analyzed {laps['analyzed_id']}: {laps['analyzed_time_s']} s · Δ {compact['total_delta_s']} s")
        st.caption(('Sezioni misurate / residuo non attribuito' if it else 'Measured sections / unallocated remainder')+
                   f": {compact['measured_delta_s']} s / {compact['unallocated_delta_s']} s")
        # Corner measurements are already shown in the selected-corner KPI table.
        for corner in compact['priorities'] if compact['mode']=='lap' else []:
            st.write(f"{corner['section']}: Δ {corner['delta_s']} s")
            rows=[dict(KPI=(ITALIAN_METRICS if it else labels).get(m['name'],m['name']),
                Reference=m['reference_value'],Analyzed=m['analyzed_value'],Difference=m['difference'],Unit=m['unit'])
                for m in corner['kpis']]
            if rows:st.dataframe(rows,hide_index=True,width='stretch')
        st.caption(('Allineamento: ' if it else 'Alignment: ')+compact['alignment'])
        st.json(dict(quality=compact['alignment_quality'],reasons=compact['alignment_reasons']))
        for limitation in compact['limitations']:st.write('• '+LIMITS[limitation][not it])


def connected_client():
    """Read the last manual connection, without any HTTP request on reruns."""
    client=LMStudioClient(st.session_state.get('coach_url',DEFAULT_URL))
    connection=st.session_state.get('coach_connection',{})
    if connection.get('url')!=client.url:return client,None
    return client,next((m for m in connection.get('models',[]) if m.identifier==st.session_state.get('coach_model')),None)


def render_generation(report,mode,corner_id=None,metric_labels=None):
    title='Lap Coaching' if mode=='lap' else 'Corner Coaching'
    st.subheader(title)
    language=st.session_state.get('coach_language','it');it=language=='it'
    st.caption('Interpretazione AI: ipotesi da verificare, non fatti ingegneristici validati.' if it else
               'AI interpretation: hypotheses to test, not validated engineering facts.')
    if corner_id is not None:st.caption(('Curva selezionata: ' if it else 'Selected corner: ')+corner_id)
    try:client,model=connected_client()
    except CoachingError:client,model=None,None
    button_key='coach_generate_'+mode
    if model is None:
        st.button('Generate '+title,disabled=True,key=button_key)
        return
    try:
        compact=prepare_input(report,mode,corner_id)
        key=cache_key(report,client.url,model,language,mode,corner_id)
    except CoachingError as exc:
        st.error(str(exc));return
    render_evidence(compact,language,metric_labels or {})
    cache=st.session_state.setdefault('coach_reports',{})
    failures=st.session_state.setdefault('coach_failures',{})
    if st.button('Generate '+title,key=button_key):
        failures.pop(mode,None)
        if key not in cache:
            try:
                with st.spinner('Generazione locale in corso…' if it else 'Generating local coaching…'):
                    result=client.generate(compact,model,language)
                if len(cache)>=8:cache.pop(next(iter(cache)))
                cache[key]=dict(input=compact,result=result)
            except CoachingError as exc:
                failures[mode]=dict(key=key,message=str(exc))
    failure=failures.get(mode)
    if failure and failure['key']==key:st.error(failure['message'])
    if key in cache:st.markdown(cache[key]['result'])


def render_corner_coach(report,corner_id,metric_labels=None):
    with st.expander('Corner Coaching',expanded=False):
        render_generation(report,'corner',corner_id,metric_labels)


def render_coach(report,metric_labels=None):
    with st.expander('AI Driving Coach',expanded=False):
        st.caption('Coaching locale opzionale · nessuna inferenza fino alla richiesta esplicita. Avvia LM Studio esternamente.')
        url=st.text_input('Local API URL',DEFAULT_URL,key='coach_url')
        language=st.selectbox('Language / Lingua',['it','en'],format_func=lambda v:'Italiano' if v=='it' else 'English',key='coach_language')
        try:client=LMStudioClient(url)
        except CoachingError as exc:
            st.error(str(exc));return
        if st.button('Connect / Refresh',key='coach_connect'):
            try:
                models=client.discover()
                st.session_state['coach_connection']=dict(url=client.url,models=models,error=None)
            except CoachingError as exc:
                st.session_state['coach_connection']=dict(url=client.url,models=[],error=str(exc))
        connection=st.session_state.get('coach_connection',{})
        if connection.get('url')!=client.url:
            st.info('Premi Connect / Refresh per verificare il server locale e i modelli già caricati.')
            render_generation(report,'lap',metric_labels=metric_labels);return
        if connection.get('error'):
            st.error(connection['error'])
        models=connection['models']
        if not models:
            if not connection.get('error'):
                st.info('Nessun modello LLM caricato. Carica il modello in LM Studio, poi premi Connect / Refresh.')
            render_generation(report,'lap',metric_labels=metric_labels);return
        by_id={model.identifier:model for model in models}
        if st.session_state.get('coach_model') not in by_id:
            st.session_state.pop('coach_model',None)
        identifier=st.selectbox('Loaded model',list(by_id),key='coach_model',
            format_func=lambda v:f'{v} · {by_id[v].label}')
        model=by_id[identifier]
        st.caption(f'Ultima verifica: {len(models)} modelli caricati · contesto configurato in LM Studio: {model.context_length or "non dichiarato"}.')
        render_generation(report,'lap',metric_labels=metric_labels)
