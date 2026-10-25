"""Actual Chrome checks, retaining the full v080 workflow and hover checks."""
import json
import time

from scripts.smoke_ui_v080 import exercise as previous


def exercise(call, ready, choose, click, screenshot, base, artifacts):
    previous(call, ready, choose, click, screenshot, base, artifacts)
    results = json.loads((artifacts/'UI_BROWSER_V080.json').read_text(encoding='utf-8'))

    def value(expression):
        result = call('Runtime.evaluate', dict(expression=expression, returnByValue=True))
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result['result'].get('value')

    def settled():
        time.sleep(.3)
        ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
        assert not value("Array.from(document.querySelectorAll('[data-testid=stException]')).map(e=>e.innerText)")

    def record(check, **data):
        results.append(dict(check=check, status='passed', **data))
        (artifacts/'UI_BROWSER_V081.json').write_text(json.dumps(results, indent=2), encoding='utf-8', newline='\n')
        print('PASS:', check, flush=True)

    charts = "Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[]).filter(p=>p._fullLayout).map(p=>({f,p})))"
    click("Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(e=>e.innerText.trim()==='Replay frequente v0.8.1')")
    settled()
    ready('('+charts+').length===2')
    assert not value("document.body.innerText.includes('Risultato finale verificato')")
    assert value("Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes('Intervallo aggiornamenti'))?.querySelector('[role=combobox]')?.value") == '1 secondo'
    record('v081 opt-in defaults to one second and hidden final target')
    slider = "document.querySelector('[role=slider],input[type=range]')"

    def key(name, code):
        call('Input.dispatchKeyEvent', dict(type='keyDown', key=name, windowsVirtualKeyCode=code))
        call('Input.dispatchKeyEvent', dict(type='keyUp', key=name, windowsVirtualKeyCode=code))

    click(slider)
    key('End', 35)
    settled()
    elapsed_expr = "Array.from(document.querySelectorAll('[data-testid=stMetric]')).find(e=>e.innerText.includes('Tempo osservato v0.8.1'))?.querySelector('[data-testid=stMetricValue]')?.innerText"
    elapsed = value(elapsed_expr)
    assert float(elapsed.split()[0]) > 60
    payload = value('('+charts+').map(o=>JSON.stringify(o.p.data))')
    assert all('target_s' not in s and 'target_source' not in s and 'pace_band' not in s for s in payload)
    numeric = value('('+charts+')[0].p._fullData.map(t=>({x:Array.from(t.x),y:Array.from(t.y)}))')
    assert all(max(t['x']) <= float(elapsed.split()[0])+.001 for t in numeric)
    record('v081 late chart payload contains only observed samples and target-free estimates', observed=elapsed)
    calls_before = value("document.body.innerText.match(/Inferenze SVR memorizzate nella sessione: (\\d+)/)?.[1]")
    selected = '('+charts+')[0]'
    value('('+selected+').f.scrollIntoView({block:"start"})')
    geometry = "(()=>{const {f,p}="+selected+";const d=p._fullData[0],i=Math.floor(d.x.length/2),xa=p._fullLayout.xaxis,ya=p._fullLayout.yaxis;const r=f.getBoundingClientRect(),q=p.getBoundingClientRect();return {x:r.x+q.x+xa._offset+xa.c2p(d.x[i]),y:r.y+q.y+ya._offset+ya.c2p(d.y[i])}})()"
    pos = value(geometry)
    value("document.querySelector('[data-testid=stMain]').scrollTop+="+str(pos['y']-430))
    time.sleep(.2)
    pos = value(geometry)
    call('Input.dispatchMouseEvent', dict(type='mouseMoved', **pos))
    time.sleep(.3)
    readout = value('('+selected+').p.closest(".comparison").querySelector(".readout").innerText')
    assert 't = ' in readout and 'Stop-aware' in readout
    assert payload == value('('+charts+').map(o=>JSON.stringify(o.p.data))')
    assert calls_before == value("document.body.innerText.match(/Inferenze SVR memorizzate nella sessione: (\\d+)/)?.[1]")
    record('v081 actual hover preserves numerical payload and Python model-call count', readout=readout, model_calls=calls_before)
    click("Array.from(document.querySelectorAll('[data-testid=stCheckbox]')).find(e=>e.innerText.includes('Rivela risultato retrospettivo v0.8.1'))?.querySelector('label')")
    settled()
    assert value("document.body.innerText.includes('Risultato finale verificato')")
    assert payload == value('('+charts+').map(o=>JSON.stringify(o.p.data))')
    record('v081 explicit reveal preserves both causal charts')
    for label, cadence in [('5 secondi', 5.), ('1 secondo', 1.), ('0.5 secondi', .5)]:
        choose('Intervallo aggiornamenti v0.8.1', label)
        settled()
        click(slider)
        key('Home', 36)
        settled()
        playing_control = "Array.from(document.querySelectorAll('[data-testid=stCheckbox]')).find(e=>e.innerText.includes('Riproduci registrazione'))?.querySelector('label')"
        # Streamlit toggle uses stCheckbox in some versions and stToggle in others.
        playing_control = "Array.from(document.querySelectorAll('[data-testid=stCheckbox],[data-testid=stToggle]')).find(e=>e.innerText.includes('Riproduci registrazione'))?.querySelector('label')"
        before = value(elapsed_expr)
        click(playing_control)
        samples = []
        begin = time.monotonic()
        while time.monotonic()-begin < max(3., cadence+1.):
            samples.append(dict(wall_s=time.monotonic()-begin, observed=value(elapsed_expr)))
            time.sleep(.12)
        click(playing_control)
        settled()
        after = value(elapsed_expr)
        assert float(after.split()[0]) > float(before.split()[0]), (label, samples)
        time.sleep(.8)
        assert value(elapsed_expr) == after
        assert not value("Array.from(document.querySelectorAll('[data-testid=stException]')).length")
        changes = [s for i,s in enumerate(samples) if i and s['observed'] != samples[i-1]['observed']]
        intervals = [b['wall_s']-a['wall_s'] for a,b in zip(changes, changes[1:])]
        record('v081 playback and pause '+label, samples=samples,
               median_observed_wall_interval_s=sorted(intervals)[len(intervals)//2] if intervals else None,
               paused_observation=after)
    for width in (480, 960, 1600):
        call('Emulation.setDeviceMetricsOverride', dict(width=width, height=1200, deviceScaleFactor=1, mobile=False))
        time.sleep(.3)
        assert value("Array.from(document.querySelectorAll('iframe')).every(f=>f.contentDocument.documentElement.scrollWidth<=f.clientWidth+2)")
        record('v081 responsive replay '+str(width))
    screenshot('high_frequency_replay', 'v081')
    click("Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(e=>e.innerText.trim()==='Riferimento operativo')")
    settled()
    assert value("Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes('Motore di previsione'))?.querySelector('[role=combobox]')?.value") == 'SVR'
    record('v081 operational signed SVR remains default and available')
