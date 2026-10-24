"""Real Chrome experimental replay, after every retained v072 workflow."""
import json
import time

from scripts.smoke_ui_v063 import exercise as previous


def exercise(call, ready, choose, click, screenshot, base, artifacts, ml_only=False):
    previous(call, ready, choose, click, screenshot, base, artifacts,
             barcelona=True, diagnosis=True, ml_only=ml_only)
    results = json.loads((artifacts/'UI_BROWSER_V072.json').read_text(encoding='utf-8'))

    def value(expression):
        result = call('Runtime.evaluate', dict(expression=expression, returnByValue=True))
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result['result'].get('value')

    def settled():
        time.sleep(.6)
        ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
        assert not value("Array.from(document.querySelectorAll('[data-testid=stException]')).map(e=>e.innerText)")

    def record(check, **data):
        results.append(dict(check=check, status='passed', **data))
        (artifacts/'UI_BROWSER_V080.json').write_text(json.dumps(results, indent=2), encoding='utf-8', newline='\n')
        print('PASS:', check, flush=True)

    charts = "Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[]).filter(p=>p._fullLayout).map(p=>({f,p})))"
    click("Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(e=>e.innerText.trim()==='Confronto sperimentale v0.8')")
    settled()
    ready("document.body.innerText.includes('Modelli sperimentali da confrontare')")
    assert not value("document.body.innerText.includes('Risultato finale verificato')")
    record('v080 experimental opt-in keeps selected final target hidden')
    control = "Array.from(document.querySelectorAll('[data-testid=stMultiSelect]')).find(e=>e.innerText.includes('Modelli sperimentali da confrontare'))"
    for name in ['RIDGE-ORDERED', 'GRU', 'SVR-DENSE', 'SVR-SPARSE', 'MEDIAN', 'SVR v0.7.1']:
        click('('+control+").querySelector('input')")
        ready("Array.from(document.querySelectorAll('[role=option]')).some(e=>e.innerText.includes("+json.dumps(name)+"))")
        # Exact text avoids choosing SVR-SPARSE when requesting the fixed SVR.
        click("Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText.trim()==="+json.dumps(name)+")")
        call('Input.dispatchKeyEvent', dict(type='keyDown', key='Escape', windowsVirtualKeyCode=27))
        settled()
        record('v080 valid artifact selection '+name)
    slider = "document.querySelector('[role=slider],input[type=range]')"
    click(slider)
    call('Input.dispatchKeyEvent', dict(type='keyDown', key='End', windowsVirtualKeyCode=35))
    call('Input.dispatchKeyEvent', dict(type='keyUp', key='End', windowsVirtualKeyCode=35))
    settled()
    ready('('+charts+').length===2')
    elapsed = value("Array.from(document.querySelectorAll('[data-testid=stMetric]')).find(e=>e.innerText.includes('Tempo osservato sperimentale'))?.querySelector('[data-testid=stMetricValue]')?.innerText")
    assert float(elapsed.split()[0]) > 60, elapsed
    record('v080 dense replay supports late observed prefixes beyond sixty seconds', elapsed=elapsed)
    payload = value('('+charts+').map(o=>JSON.stringify(o.p.data))')
    assert all('target_s' not in s and 'actual_s' not in s and 'target_source' not in s for s in payload)
    assert not value("document.body.innerText.includes('Risultato finale verificato')")
    selected = '('+charts+')[1]'
    value('('+selected+').f.scrollIntoView({block:"start"})')
    geometry = "(()=>{const {f,p}="+selected+";const d=p._fullData[0],i=Math.floor(d.x.length/2),xa=p._fullLayout.xaxis,ya=p._fullLayout.yaxis;const r=f.getBoundingClientRect(),q=p.getBoundingClientRect();return {x:r.x+q.x+xa._offset+xa.c2p(d.x[i]),y:r.y+q.y+ya._offset+ya.c2p(d.y[i])}})()"
    pos = value(geometry)
    value("document.querySelector('[data-testid=stMain]').scrollTop+="+str(pos['y']-430))
    time.sleep(.3)
    pos = value(geometry)
    call('Input.dispatchMouseEvent', dict(type='mouseMoved', x=pos['x'], y=pos['y']))
    time.sleep(.4)
    readout = value('('+selected+').p.closest(".comparison").querySelector(".readout").innerText')
    assert 't = ' in readout and 'GRU' in readout, readout
    record('v080 actual pointer inspects all model trajectories with external cursor readout', readout=readout)
    before = value('('+charts+').map(o=>JSON.stringify(o.p.data))')
    click("Array.from(document.querySelectorAll('[data-testid=stCheckbox]')).find(e=>e.innerText.includes('Rivela risultato retrospettivo sperimentale'))?.querySelector('label')")
    settled()
    assert value("document.body.innerText.includes('Risultato finale verificato')")
    assert before == value('('+charts+').map(o=>JSON.stringify(o.p.data))')
    record('v080 retrospective reveal preserves every causal chart payload')
    choose('Cadenza causale', 'Compatibilità')
    settled()
    choose('Cadenza causale', '10 secondi')
    settled()
    record('v080 compatibility and configurable elapsed-time cadence work')
    for width in (960, 480, 1600):
        call('Emulation.setDeviceMetricsOverride', dict(width=width, height=1200, deviceScaleFactor=1, mobile=False))
        time.sleep(.6)
        assert value("Array.from(document.querySelectorAll('iframe')).every(f=>f.contentDocument.documentElement.scrollWidth<=f.clientWidth+2)")
        record('v080 responsive experimental replay '+str(width))
    screenshot('experimental_replay', 'v080')
    click("Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(e=>e.innerText.trim()==='Riferimento operativo')")
    settled()
    assert value("Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes('Motore di previsione'))?.querySelector('[role=combobox]')?.value==='SVR'")
    record('v080 original working SVR mode remains operational after experimental inspection')
