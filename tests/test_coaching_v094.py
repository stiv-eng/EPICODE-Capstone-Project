"""Focused coaching checks: deterministic evidence, text, manual UI and local API."""
import copy
import io
import json
import math
from pathlib import Path
import re
from urllib import error, request

import pytest
from streamlit.testing.v1 import AppTest

from motorsport.coaching import (CoachingError, LMStudioClient, MAX_INPUT_CHARS,
                                MAX_TOKENS, cache_key, canonical, format_number, messages,
                                prepare_input, present_input)

ROOT = Path(__file__).resolve().parents[1]
TEXT = '  **C01**: 90 km/h versus 100 km/h.\n\nTest a smoother entry; check apex speed and section time.\n'


@pytest.fixture
def report():
    sections = [dict(section_id=f'C{i:02}', kind='corner', delta_s=delta, validity='valid')
                for i, delta in enumerate([.8, .4, .3, .2, -.3], 1)]
    corners = [dict(section_id=s['section_id'], kpis=[
        dict(name='speed_at_apex_kmh', reference_value=100., analyzed_value=90.,
             difference=-10., unit='km/h', validity='valid', definition='Speed at the geometric apex proxy'),
        dict(name='brake_onset_position_m', reference_value=999999., analyzed_value=999998.,
             difference=-1., unit='m', validity='uncertain', explanation='ambiguous events'),
        dict(name='steering_at_apex', reference_value=None, analyzed_value=None,
             difference=None, unit='unknown', validity='unavailable', explanation='unknown unit')]) for s in sections]
    return dict(schema_version='deterministic-lap-analysis/1.0', status='partial', runtime_s=.1,
        source=dict(reference=dict(session_id='a', track_id='track', car_id='car'),
                    analyzed=dict(session_id='b', track_id='track', car_id='car')),
        laps=dict(reference_id=1, analyzed_id=2, reference_time_s=100., analyzed_time_s=102., measured_lap_delta_s=2.),
        config=dict(radius=150), section_deltas=sections, corners=corners,
        unallocated_delta=dict(value_s=.6, required=True),
        alignment=dict(reasons=['unreliable projection'], analyzed=dict(p95_offset_m=2.5)),
        raw_telemetry=[999999]*2000)


@pytest.fixture
def api(monkeypatch):
    calls = []
    visible = dict(data=[dict(id='actual-instance'), dict(id='second-instance'), dict(id='downloaded-only')])
    def model(identifier, loaded=True):
        return dict(type='llm', key='qwen-file', display_name='Local Qwen', quantization=dict(name='Q4_K_M'),
            capabilities=dict(reasoning=dict(allowed_options=['off', 'on'])),
            loaded_instances=[dict(id=identifier, config=dict(context_length=8192))] if loaded else [])
    native = dict(models=[model('actual-instance'), model('second-instance'), model('downloaded-only', False),
                         dict(type='embedding', loaded_instances=[dict(id='not-a-chat-model')])])
    completion = dict(choices=[dict(finish_reason='stop', message=dict(content=TEXT))])
    def open_request(self, req, timeout=None):
        calls.append(req)
        if req.full_url.endswith('/api/v1/models'): data = native
        elif req.full_url.endswith('/v1/models'): data = visible
        else: data = completion
        return io.BytesIO(canonical(data).encode())
    monkeypatch.setattr(request.OpenerDirector, 'open', open_request)
    return calls, native, completion


def posts(calls):
    return [req for req in calls if req.get_method() == 'POST']


def app_for(report):
    app = AppTest.from_string('''
import streamlit as st
from motorsport_ui.coaching import render_coach, render_corner_coach
st.write('Deterministic analysis remains available')
render_coach(st.session_state['facts'])
selected = st.selectbox('Curva da ispezionare', ['C01', 'C02'], key='lap_analysis_corner')
render_corner_coach(st.session_state['facts'], selected)
''')
    app.session_state['facts'] = report
    return app.run()


def shows_text(app):
    # Streamlit normalizes outer Markdown whitespace; the client/cache keep it intact.
    return any(m.value == TEXT.strip() for m in app.markdown)


def test_lap_evidence_preserves_measurements_and_excludes_uncertain_values(report):
    original = copy.deepcopy(report)
    compact = prepare_input(report)
    assert len(compact['priorities']) == 4
    assert [c['section'] for c in compact['priorities']] == ['C01', 'C02', 'C03', 'C05']
    assert len(canonical(compact)) <= MAX_INPUT_CHARS
    assert 'raw_telemetry' not in compact and '999999' not in canonical(compact)
    assert compact['total_delta_s'] == 2. and compact['unallocated_delta_s'] == .6
    assert compact['alignment_quality']['analyzed']['p95_offset_m'] == 2.5
    assert compact['remaining']['delta_s'] == .2
    assert compact['excluded_kpis']['uncertain'] == 5
    for corner in compact['priorities']:
        metric = corner['kpis'][0]
        assert [metric[k] for k in ('reference_value', 'analyzed_value', 'difference', 'unit')] == [100., 90., -10., 'km/h']
    assert report == original
    report['section_deltas'][0]['partial_section'] = True
    assert all(c['section'] != 'C01' for c in prepare_input(report)['priorities'])


def test_lap_skips_identical_metrics_and_prefers_informative_corners(report):
    metric = report['corners'][0]['kpis'][0]
    metric.update(analyzed_value=100.001, difference=.001)
    fallback = dict(name='entry_speed_kmh', reference_value=120., analyzed_value=115.,
                    difference=-5., unit='km/h', validity='valid')
    report['corners'][0]['kpis'].append(fallback)
    assert prepare_input(report)['priorities'][0]['kpis'][0]['name'] == 'entry_speed_kmh'
    report['corners'][0]['kpis'].pop()
    compact = prepare_input(report)
    assert all(c['section'] != 'C01' for c in compact['priorities'])
    for corner in report['corners']:
        corner['kpis'][0].update(analyzed_value=100., difference=0.)
    compact = prepare_input(report)
    assert not any(c['kpis'] for c in compact['priorities'])
    assert 'no_supported_technique' in compact['limitations']


def test_selected_corner_gets_all_valid_kpis_and_only_its_context(report):
    report['corners'][1]['kpis'].append(dict(name='exit_speed_kmh', reference_value=130.,
        analyzed_value=130., difference=0., unit='km/h', validity='valid', definition='Speed at exit'))
    compact = prepare_input(report, 'corner', 'C02')
    assert compact['mode'] == 'corner' and compact['selected_corner'] == 'C02'
    assert [c['section'] for c in compact['priorities']] == ['C02']
    assert {m['name'] for m in compact['priorities'][0]['kpis']} == {'speed_at_apex_kmh', 'exit_speed_kmh'}
    assert all('definition' in m for m in compact['priorities'][0]['kpis'])
    assert compact['excluded_kpis']['uncertain'] == 1
    assert compact['total_delta_s'] == 2. and compact['priorities'][0]['delta_s'] == .4
    for mode, corner in [('corner', 'C99'), ('corner', None), ('invalid', None)]:
        with pytest.raises(CoachingError): prepare_input(report, mode, corner)
    report['section_deltas'][1]['partial_section'] = True
    with pytest.raises(CoachingError): prepare_input(report, 'corner', 'C02')


@pytest.mark.parametrize('relative', [
    'artifacts/v093-facts-20240304_AB-6.json',
    'artifacts/v093-facts-20240229_HC-2.json',
    'artifacts/v090/facts-GT7-13.json',
])
def test_existing_real_json_facts_in_both_modes(relative):
    path = ROOT/relative
    if not path.exists(): pytest.skip('Optional installed real-analysis artifact absent')
    original = json.loads(path.read_text(encoding='utf-8'))
    lap = prepare_input(original)
    assert 3 <= len(lap['priorities']) <= 4
    corner = prepare_input(original, 'corner', lap['priorities'][0]['section'])
    for compact in (lap, corner):
        assert len(canonical(compact)) <= MAX_INPUT_CHARS
        assert compact['alignment'] == original['status']
        assert compact['measured_delta_s']+compact['unallocated_delta_s'] == pytest.approx(compact['total_delta_s'])
        for selected in compact['priorities']:
            for metric in selected['kpis']:
                source = next(m for c in original['corners'] if c['section_id'] == selected['section']
                              for m in c['kpis'] if m['name'] == metric['name'])
                assert source['validity'] == 'valid'
                assert all(metric[k] == source[k] for k in ('reference_value', 'analyzed_value', 'difference', 'unit'))


@pytest.mark.parametrize('mode,corner', [('lap', None), ('corner', 'C02')])
def test_one_plain_text_completion_per_mode(api, report, mode, corner):
    calls, native, _ = api
    client = LMStudioClient(); models = client.discover()
    assert [m.identifier for m in models] == ['actual-instance', 'second-instance']
    compact = prepare_input(report, mode, corner)
    assert client.generate(compact, models[0], 'en') == TEXT
    assert len(posts(calls)) == 1
    body = json.loads(posts(calls)[0].data)
    assert body['model'] == 'actual-instance' and body['max_tokens'] == MAX_TOKENS
    assert body['stream'] is False and body['reasoning_effort'] == 'none'
    assert body['messages'][1]['content'].endswith('/no_think')
    assert 'response_format' not in body
    assert ('Lap Coaching' if mode == 'lap' else 'Corner Coaching') in body['messages'][0]['content']
    supplied = json.loads(body['messages'][1]['content'].splitlines()[0])
    assert supplied['mode'] == mode and supplied['selected_corner'] == corner
    native['models'][0]['loaded_instances'] = []
    with pytest.raises(CoachingError, match='caricato'): client.generate(compact, models[0], 'en')
    assert len(posts(calls)) == 1


def test_text_has_no_semantic_filter_and_reasoning_option_is_conditional(api, report):
    _, native, completion = api
    native['models'][0]['capabilities'] = {}
    text = 'C01: try braking 20 m later; could the difference be caused by oversteer?'
    completion['choices'][0]['message']['content'] = text
    client = LMStudioClient(); model = client.discover()[0]
    assert client.generate(prepare_input(report), model, 'it') == text
    body = json.loads(posts(api[0])[0].data)
    assert 'reasoning_effort' not in body
    assert 'in Italian.' in body['messages'][0]['content']


@pytest.mark.parametrize('content,finish', [('', 'stop'), ('  \n', 'stop'), (None, 'stop'),
    ([], 'stop'), ('partial text', 'length'), ('refused', 'content_filter')])
def test_empty_or_failed_generation(api, report, content, finish):
    _, _, completion = api
    completion['choices'][0].update(message=dict(content=content), finish_reason=finish)
    client = LMStudioClient(); model = client.discover()[0]
    with pytest.raises(CoachingError): client.generate(prepare_input(report), model, 'en')


@pytest.mark.parametrize('completion', [{}, {'choices': []}, {'choices': [{}]}, {'choices': None}])
def test_malformed_chat_envelope(api, report, completion):
    api[2].clear(); api[2].update(completion)
    client = LMStudioClient(); model = client.discover()[0]
    with pytest.raises(CoachingError): client.generate(prepare_input(report), model, 'en')


def test_cache_keys_cover_inputs_settings_language_model_and_mode(api, report):
    client = LMStudioClient(); models = client.discover()
    key = cache_key(report, client.url, models[0], 'en')
    changed = copy.deepcopy(report); changed['runtime_s'] = 99
    assert cache_key(changed, client.url, models[0], 'en') == key
    for field in ('config', 'laps', 'source', 'corners'):
        changed = copy.deepcopy(report); changed[field] = dict(changed=True)
        assert cache_key(changed, client.url, models[0], 'en') != key
    assert cache_key(report, client.url, models[1], 'en') != key
    assert cache_key(report, client.url, models[0], 'it') != key
    assert cache_key(report, 'http://localhost:1234/v1', models[0], 'en') != key
    corner1 = cache_key(report, client.url, models[0], 'en', 'corner', 'C01')
    corner2 = cache_key(report, client.url, models[0], 'en', 'corner', 'C02')
    assert len({key, corner1, corner2}) == 3


def test_streamlit_manual_independent_modes_and_cache(api, report):
    calls, _, _ = api
    app = app_for(report)
    assert not app.exception and not calls
    assert app.button(key='coach_generate_lap').disabled
    assert app.button(key='coach_generate_corner').disabled
    app.button(key='coach_connect').click().run()
    assert not app.exception and len(calls) == 2
    app.selectbox(key='coach_language').set_value('en').run()
    app.selectbox(key='lap_analysis_corner').set_value('C02').run()
    assert len(calls) == 2  # Selection changes never generate.
    app.button(key='coach_generate_corner').click().run()
    assert not app.exception and len(posts(calls)) == 1 and shows_text(app)
    assert json.loads(posts(calls)[0].data)['messages'][0]['content'].find('Corner Coaching') >= 0
    app.button(key='coach_generate_lap').click().run()
    assert not app.exception and len(posts(calls)) == 2
    count = len(calls)
    app.run(); app.button(key='coach_generate_lap').click().run()
    app.button(key='coach_generate_corner').click().run()
    assert len(calls) == count  # Cached buttons do not even recheck residency.
    app.selectbox(key='lap_analysis_corner').set_value('C01').run()
    assert len(calls) == count and shows_text(app)  # Lap result survives corner changes.
    app.button(key='coach_generate_corner').click().run()
    assert len(posts(calls)) == 3
    count = len(calls)
    for key, value in [('coach_model', 'second-instance'), ('coach_language', 'it')]:
        app.selectbox(key=key).set_value(value).run()
        assert not shows_text(app) and len(calls) == count
    app.button(key='coach_generate_lap').click().run()
    assert len(posts(calls)) == 4
    app.session_state['facts'] = dict(report, config=dict(radius=140)); app.run()
    assert not shows_text(app) and len(posts(calls)) == 4
    app.text_input(key='coach_url').set_value('http://localhost:4321/v1').run()
    assert app.button(key='coach_generate_lap').disabled and app.button(key='coach_generate_corner').disabled
    assert len(posts(calls)) == 4


def test_failure_is_local_and_never_retried_on_rerun(api, report):
    calls, _, completion = api
    app = app_for(report); app.button(key='coach_connect').click().run()
    completion['choices'][0]['message']['content'] = ''
    app.button(key='coach_generate_lap').click().run()
    assert not app.exception and any('vuota' in m.value for m in app.error)
    count = len(calls); app.run()
    assert len(calls) == count
    completion['choices'][0]['message']['content'] = TEXT
    app.button(key='coach_generate_corner').click().run()
    assert not app.exception and shows_text(app) and len(posts(calls)) == 2
    assert any('Deterministic analysis remains' in m.value for m in app.markdown)


def test_disconnected_and_empty_server_are_optional(monkeypatch, report, api):
    api[1]['models'] = []
    app = app_for(report); app.button(key='coach_connect').click().run()
    assert not app.exception and any('Nessun modello' in m.value for m in app.info)
    assert app.button(key='coach_generate_lap').disabled and app.button(key='coach_generate_corner').disabled
    def offline(*args, **kwargs): raise error.URLError('connection refused')
    monkeypatch.setattr(request.OpenerDirector, 'open', offline)
    app.button(key='coach_connect').click().run()
    assert not app.exception and any('non raggiungibile' in m.value for m in app.error)
    assert any('Deterministic analysis remains' in m.value for m in app.markdown)


@pytest.mark.parametrize('failure,match', [
    (error.HTTPError('local', 401, 'unauthorized', {}, None), 'LM_STUDIO_API_KEY'),
    (error.HTTPError('local', 500, 'server failure', {}, None), 'HTTP 500'),
    (TimeoutError('timeout'), 'timeout'), (error.URLError('refused'), 'non raggiungibile'),
])
def test_essential_transport_errors(monkeypatch, failure, match):
    def fail(*args, **kwargs): raise failure
    monkeypatch.setattr(request.OpenerDirector, 'open', fail)
    with pytest.raises(CoachingError, match=match): LMStudioClient().discover()


@pytest.mark.parametrize('raw', [b'not JSON', b'[]', b'{"data":null}'])
def test_invalid_discovery_response(monkeypatch, raw):
    monkeypatch.setattr(request.OpenerDirector, 'open', lambda *a, **kw: io.BytesIO(raw))
    with pytest.raises(CoachingError): LMStudioClient().discover()


@pytest.mark.parametrize('url', ['https://api.example.com/v1', 'http://localhost:1234/bad', 'http://localhost:bad/v1'])
def test_local_api_url(url):
    with pytest.raises(CoachingError): LMStudioClient(url)


def test_no_alignment_still_allows_lap_commentary(report):
    report.update(status='unavailable', section_deltas=[], corners=[], unallocated_delta=dict(value_s=2., required=True))
    compact = prepare_input(report)
    assert compact['priorities'] == [] and compact['total_delta_s'] == 2.
    assert 'no_supported_technique' in compact['limitations']
    prompt = messages(compact, 'en')[0]['content']
    assert 'If evidence is insufficient for a directional action' in prompt
    assert 'specific telemetry check instead' in prompt


@pytest.mark.parametrize('mode,corner', [('lap', None), ('corner', 'C02')])
@pytest.mark.parametrize('language', ['it', 'en'])
def test_natural_coaching_prompt_keeps_evidence_and_mode_scope(report, mode, corner, language):
    compact = prepare_input(report, mode, corner)
    system, user = messages(compact, language)
    prompt = system['content']
    assert 'Evidence → Action → Verification' in prompt
    assert '{MEASURED EVIDENCE} → {SPECIFIC DRIVING ACTION TO TEST} → {TELEMETRY METRIC TO VERIFY THE RESULT}' in prompt
    assert 'never print these placeholders' in prompt
    assert 'all supplied valid KPI categories without favoring any driving input' in prompt
    assert 'most relevant to the observed performance gap' in prompt
    assert 'distinct experiments instead of repetitive recommendations' in prompt
    assert 'No driving input or higher, lower, earlier or later KPI value is inherently better' in prompt
    assert 'Distinguish observed differences from possible causes' in prompt
    # Instructions stay abstract; actual telemetry remains in the separate evidence payload.
    instructions = prompt+'\n'+'\n'.join(user['content'].splitlines()[1:])
    assert not re.search(r'\b(?:throttle|brake|braking|steering|apex)\b', instructions, re.I)
    assert not re.search(r'\bC\d{2}\b|\b\d+\.\d+\b', instructions)
    assert 'do not write literal Evidence, Action or Verification labels' in prompt
    assert 'natural, flowing sentences' in prompt
    assert 'speaking directly to the driver' in prompt
    headings = ('Riepilogo', 'Azioni consigliate') if language == 'it' else ('Summary', 'Recommended Actions')
    assert "Use exactly two sections, headed '"+headings[0]+"' then '"+headings[1]+"'" in prompt
    assert 'only when the available KPI evidence supports' in prompt
    assert 'do not add repeated cautionary notes' in prompt
    assert 'Do not fabricate measurements' in prompt
    if mode == 'lap':
        assert '2–4 recommendations' in prompt and 'overall lap performance' in prompt
    else:
        assert '1–3 relevant driving experiments' in prompt and 'measured corner time difference' in prompt
    assert 'Do not repeat the full KPI table' in prompt
    assert all(heading in user['content'] for heading in headings)
    assert json.loads(user['content'].splitlines()[0]) == present_input(compact)
    assert user['content'].endswith('/no_think')


def test_evidence_selection_does_not_amplify_throttle_category(report):
    # More available metrics in one category must not crowd out the other lap evidence.
    available = [('brake_onset_position_m', 'm'), ('speed_at_apex_kmh', 'km/h'),
                 ('steering_rms_rate', 'deg/s'), ('throttle_after_apex_delay_s', 's'),
                 ('throttle_at_apex_pct', '%'), ('maximum_exit_throttle_pct', '%')]
    report['corners'][0]['kpis'] = [dict(name=name, unit=unit, reference_value=10.,
        analyzed_value=8., difference=-2., validity='valid') for name, unit in available]
    lap = prepare_input(report)
    selected = next(c for c in lap['priorities'] if c['section'] == 'C01')
    assert {m['name'] for m in selected['kpis']} == {
        'brake_onset_position_m', 'speed_at_apex_kmh', 'steering_rms_rate', 'throttle_after_apex_delay_s'}
    corner = prepare_input(report, 'corner', 'C01')
    assert {m['name'] for m in corner['priorities'][0]['kpis']} == {name for name, unit in available}


@pytest.mark.parametrize('mode,expected_tables', [('lap', 4), ('corner', 0)])
def test_corner_coach_does_not_repeat_kpi_table(report, mode, expected_tables):
    app = AppTest.from_string('''
import streamlit as st
from motorsport.coaching import prepare_input
from motorsport_ui.coaching import render_evidence
compact = prepare_input(st.session_state['facts'], st.session_state['mode'], 'C02')
render_evidence(compact, 'en', {})
''')
    app.session_state['facts'] = report
    app.session_state['mode'] = mode
    app.run()
    assert not app.exception and len(app.dataframe) == expected_tables
    assert any('Alignment:' in item.value for item in app.caption)


@pytest.mark.parametrize('value,expected', [
    (72.4413762, '72.441'), (.1643987, '0.164'), (12., '12'),
    (5.67891, '5.679'), (-.0004, '0'), (-0., '0'), (-1.234567, '-1.235'),
    (1.2, '1.2'), (.1+.2, '0.3'),
])
def test_numeric_presentation(value, expected):
    assert format_number(value) == expected


@pytest.mark.parametrize('unit,reference,analyzed,difference,target,expected', [
    ('m/s', 20., 15., -5., 'km/h', ['72', '54', '-18']),
    ('mph', 10., 5., -5., 'km/h', ['16.093', '8.047', '-8.047']),
    ('cm', 1200.1, 1500.9, 300.8, 'm', ['12.001', '15.009', '3.008']),
    ('ms', 164.3987, 1.2345, -163.1642, 's', ['0.164', '0.001', '-0.163']),
    ('rad', math.pi/2, math.pi/3, -math.pi/6, '°', ['90', '60', '-30']),
    ('deg', 1.234567, -2.345678, -3.580245, '°', ['1.235', '-2.346', '-3.58']),
    ('rad/s', math.pi/2, math.pi/3, -math.pi/6, '°/s', ['90', '60', '-30']),
    ('deg/s', 5.67891, 0., -5.67891, '°/s', ['5.679', '0', '-5.679']),
    ('%', 40.200001, 90.300002, 50.100001, '%', ['40.2', '90.3', '50.1']),
    ('g', 1.234567, 2.345678, 1.111111, 'g', ['1.235', '2.346', '1.111']),
])
def test_coaching_unit_conversion_preserves_all_three_values(unit, reference, analyzed, difference, target, expected):
    metric = dict(unit=unit, reference_value=reference, analyzed_value=analyzed, difference=difference)
    original = copy.deepcopy(metric)
    display = present_input(metric)
    assert display['unit'] == target
    assert [display[k] for k in ('reference_value', 'analyzed_value', 'difference')] == expected
    assert metric == original
    assert present_input(display) == display


@pytest.mark.parametrize('mode,corner', [('lap', None), ('corner', 'C01')])
def test_prompt_formats_all_evidence_without_rounding_internal_values(report, mode, corner):
    report['laps'].update(reference_time_s=100.1234567, analyzed_time_s=102.1234567)
    report['corners'][0]['kpis'][0].update(unit='m/s', reference_value=20.1234567,
                                         analyzed_value=19.0123456, difference=-1.1111111)
    report['corners'][0]['kpis'].append(dict(name='steering_rms_rate', unit='rad/s',
        reference_value=math.pi/2, analyzed_value=math.pi/3, difference=-math.pi/6, validity='valid'))
    report['alignment']['analyzed']['p95_offset_m'] = -.00001
    report['config']['kpis'] = dict(brake_on_persistence_s=.15000000000002)
    report['geometry'] = dict(sections=[dict(section_id='C01', start_s_m=12.00000001,
        end_s_m=125.12345678, curvature_weighted_apex_proxy=dict(s_m=72.4413762, xy=[.1+.2, -.000001]))])
    original = copy.deepcopy(report)
    compact = prepare_input(report, mode, corner)
    internal = copy.deepcopy(compact)
    supplied = json.loads(messages(compact, 'en')[1]['content'].splitlines()[0])
    assert report == original and compact == internal
    assert supplied['laps']['reference_time_s'] == '100.123'
    assert supplied['alignment_quality']['analyzed']['p95_offset_m'] == '0'
    assert supplied['measurement_settings']['brake_on_persistence_s'] == '0.15'
    selected = next(c for c in supplied['priorities'] if c['section'] == 'C01')
    assert selected['delta_s'] == '0.8'
    assert selected['geometry']['curvature_weighted_apex_proxy']['xy'] == ['0.3', '0']
    speed = next(m for m in selected['kpis'] if m['name'] == 'speed_at_apex_kmh')
    assert [speed[k] for k in ('reference_value', 'analyzed_value', 'difference', 'unit')] == ['72.444', '68.444', '-4', 'km/h']
    steering = next(m for m in selected['kpis'] if m['name'] == 'steering_rms_rate')
    assert steering['unit'] == '°/s' and steering['difference'] == '-30'
    def check_numbers(value):
        if isinstance(value, dict):
            for item in value.values(): check_numbers(item)
        elif isinstance(value, list):
            for item in value: check_numbers(item)
        else:
            assert not isinstance(value, float)
            if isinstance(value, str) and re.fullmatch(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?', value):
                assert re.fullmatch(r'-?\d+(?:\.\d{1,3})?', value) and value != '-0'
    check_numbers(supplied)


def test_ui_uses_same_converted_measurements_as_prompt(api, report):
    report['corners'][0]['kpis'].append(dict(name='steering_at_apex', unit='rad',
        reference_value=math.pi/2, analyzed_value=math.pi/3, difference=-math.pi/6, validity='valid'))
    report['laps'].update(reference_time_s=100.1234567, analyzed_time_s=102.1234567)
    app = app_for(report)
    app.button(key='coach_connect').click().run()
    app.button(key='coach_generate_lap').click().run()
    assert not app.exception
    payload = json.loads(json.loads(posts(api[0])[0].data)['messages'][1]['content'].splitlines()[0])
    metric = next(m for m in payload['priorities'][0]['kpis'] if m['name'] == 'steering_at_apex')
    table = app.dataframe[0].value
    row = table.loc[table['Unit'] == '°'].iloc[0]
    assert [row[k] for k in ('Reference', 'Analyzed', 'Difference', 'Unit')] == [
        metric[k] for k in ('reference_value', 'analyzed_value', 'difference', 'unit')]
    assert any('100.123 s' in m.value for m in app.markdown)
