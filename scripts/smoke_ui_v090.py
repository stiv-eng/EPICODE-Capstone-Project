"""Actual Chrome lap-analysis checks following every retained v082 workflow."""
import json
import tempfile
import time

from scripts.smoke_ui_v082 import exercise as previous


def exercise(call,ready,choose,click,screenshot,base,artifacts):
    previous(call,ready,choose,click,screenshot,base,artifacts)
    records=json.loads((artifacts/'UI_BROWSER_V082.json').read_text(encoding='utf-8'))
    def value(expression,await_promise=False):
        response=call('Runtime.evaluate',dict(expression=expression,returnByValue=True,awaitPromise=await_promise))
        if 'exceptionDetails' in response:raise RuntimeError(response['exceptionDetails'])
        return response['result'].get('value')
    def settled():
        time.sleep(.5)
        ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
        assert not value("Array.from(document.querySelectorAll('[data-testid=stException]')).length")
    def record(name,**data):
        records.append(dict(check=name,status='passed',**data))
        (artifacts/'UI_BROWSER_V090.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
        print('PASS:',name,flush=True)
    charts="Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[]).filter(p=>p._fullLayout).map(p=>({f,p})))"
    navigate="Array.from(document.querySelectorAll('a')).find(a=>a.getAttribute('href')?.endsWith('/lap-analysis'))"
    call('Page.navigate',dict(url=base))
    ready("document.body.innerText.includes('Apri Data Explorer')");settled()
    click(navigate);ready("document.body.innerText.includes('Sessione del giro analizzato')");settled()
    choose('Dataset analizzato','GT7');settled()
    ready('('+charts+').length===4')
    assert value("document.body.innerText.includes('Allineamento spaziale valido')")
    record('v090 actual GT7 lap analysis uses recorded geometry and valid spatial alignment')

    def facts():
        # Chrome can overwrite an existing filename. Each real download gets a
        # distinct folder so observing a stale file cannot satisfy this check.
        from pathlib import Path
        download_dir=Path(tempfile.mkdtemp(prefix='facts-download-',dir=artifacts.resolve()))
        call('Browser.setDownloadBehavior',dict(behavior='allow',downloadPath=str(download_dir)))
        selector="Array.from(document.querySelectorAll('[data-testid=stDownloadButton]')).find(e=>e.innerText.includes('Esporta fatti JSON'))?.querySelector('button,a')"
        click(selector)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            downloaded=set(download_dir.glob('telemetry_lap_analysis_v090*.json'))
            if downloaded:
                break
            time.sleep(.1)
        assert downloaded,'Actual JSON browser download did not finish'
        f=json.loads(next(iter(downloaded)).read_text(encoding='utf-8'))
        return dict(schema=f['schema_version'],status=f['status'],laps=f['laps'],
            geometry=dict(closed=f['geometry']['closed'],corners=sum(s['kind']=='corner' for s in f['geometry']['sections']),
                apices=[s['curvature_weighted_apex_proxy'] for s in f['geometry']['sections'] if s['kind']=='corner'],
                threshold=f['config']['geometry']['radius_threshold_m']),
            sum=sum(s['delta_s'] for s in f['section_deltas']),error=f.get('reconciliation',{}).get('error_s'),
            interpretations=f['interpretations'])
    initial=facts()
    assert initial['schema']=='deterministic-lap-analysis/1.0' and initial['status']=='valid'
    assert initial['geometry']['closed'] and initial['geometry']['threshold']==150.
    assert abs(initial['sum']-initial['laps']['measured_lap_delta_s'])<1e-6
    assert not initial['interpretations']
    record('v090 actual JSON download contains measured facts, validity, weighted apex and reconciled deltas',
        lap_delta_s=initial['laps']['measured_lap_delta_s'],section_error_s=initial['error'],corners=initial['geometry']['corners'])
    assert value('('+charts+')[0].p._fullLayout.yaxis.scaleanchor')=='x'
    distance="("+charts+").filter(o=>o.p._fullLayout.meta?.cursor_unit==='m')"
    assert value(distance+'.length')==2
    selected='('+distance+')[1]'
    value('('+selected+').f.scrollIntoView({block:"start"})')
    geometry="(()=>{const {f,p}="+selected+";const d=p._fullData[0],i=Math.floor(d.x.length/2),xa=p._fullLayout.xaxis,ya=p._fullLayout.yaxis;const r=f.getBoundingClientRect(),q=p.getBoundingClientRect();return {x:r.x+q.x+xa._offset+xa.c2p(d.x[i]),y:r.y+q.y+ya._offset+ya.c2p(d.y[i])}})()"
    point=value(geometry)
    value("document.querySelector('[data-testid=stMain]').scrollTop+="+str(point['y']-430))
    time.sleep(.3);point=value(geometry)
    before=value('('+distance+').map(o=>JSON.stringify(o.p.data))')
    value("window.analysisHoverRuns=0;window.analysisObserver=new MutationObserver(ms=>{for(const m of ms)if(m.attributeName==='data-test-script-state'&&m.target.getAttribute(m.attributeName)!=='notRunning')window.analysisHoverRuns++;});window.analysisObserver.observe(document.querySelector('[data-testid=stApp]'),{attributes:true})")
    call('Input.dispatchMouseEvent',dict(type='mouseMoved',**point));time.sleep(.4)
    readout=value('('+selected+').p.closest(".comparison").querySelector(".readout").innerText')
    assert 's = ' in readout and ' m ' in readout and 't = ' not in readout,readout
    for _ in range(10):call('Input.dispatchMouseEvent',dict(type='mouseMoved',**point))
    time.sleep(.2)
    assert before==value('('+distance+').map(o=>JSON.stringify(o.p.data))') and value('window.analysisHoverRuns')==0
    cursor=value('('+distance+').flatMap(o=>Array.from(o.p.closest(".comparison").querySelectorAll(".time-cursor")).map(l=>+l.dataset.time))')
    assert len(cursor)>=2 and max(cursor)-min(cursor)<1e-7
    record('v090 actual shared spatial cursor uses metres, preserves data and triggers no Python rerun',readout=readout,cursor_positions_m=cursor)
    choose('Giro analizzato','Lap 11');settled()
    changed=facts()
    assert abs(changed['laps']['measured_lap_delta_s']-1.835)<1e-8
    assert changed['geometry']['apices']==initial['geometry']['apices']
    record('v090 changing analyzed lap preserves common reference corner/apex definitions')
    choose('Giro di riferimento','Lap 13');settled()
    choose('Giro analizzato','Lap 14');settled()
    reversed_facts=facts()
    assert abs(reversed_facts['laps']['measured_lap_delta_s']+.094)<1e-8
    record('v090 reference swapping reverses measured lap delta')
    choose('Giro di riferimento','Lap 14');settled()
    choose('Giro analizzato','Lap 13');settled()
    click("Array.from(document.querySelectorAll('[data-testid=stExpander] summary')).find(e=>e.innerText.includes('Parametri geometrici'))")
    field="Array.from(document.querySelectorAll('[data-testid=stNumberInput]')).find(e=>e.innerText.includes('Soglia raggio curva'))?.querySelector('input')"
    def set_radius(number):
        click(field)
        call('Input.dispatchKeyEvent',dict(type='keyDown',key='a',modifiers=2,windowsVirtualKeyCode=65))
        call('Input.dispatchKeyEvent',dict(type='keyUp',key='a',modifiers=2,windowsVirtualKeyCode=65))
        call('Input.insertText',dict(text=str(number)))
        call('Input.dispatchKeyEvent',dict(type='keyDown',key='Enter',windowsVirtualKeyCode=13))
        call('Input.dispatchKeyEvent',dict(type='keyUp',key='Enter',windowsVirtualKeyCode=13));settled()
    set_radius(200)
    threshold=facts()
    assert threshold['geometry']['threshold']==200 and threshold['geometry']['corners']!=initial['geometry']['corners']
    assert abs(threshold['sum']-threshold['laps']['measured_lap_delta_s'])<1e-6
    set_radius(150)
    record('v090 configurable radius consistently refreshes geometry, KPIs and section decomposition')
    click("Array.from(document.querySelectorAll('[data-testid=stCheckbox]')).find(e=>e.innerText.includes('maximum-curvature'))?.querySelector('label')")
    settled()
    assert value('('+charts+')[0].p._fullData.some(t=>t.name===\'Maximum-curvature point\')')
    record('v090 maximum curvature remains diagnostic alongside primary weighted apex proxy')
    from motorsport_ui.telemetry import source_catalog
    label=next(v for k,v in source_catalog(include_acgym=True).items() if k.startswith('barcelona:20240304_AB/'))
    choose('Dataset analizzato',label);settled()
    choose('Giro analizzato','Lap 6');settled()
    barcelona=facts()
    assert barcelona['status']=='valid' and barcelona['geometry']['corners']>0
    assert abs(barcelona['sum']-barcelona['laps']['measured_lap_delta_s'])<1e-6
    record('v090 actual Barcelona LD coordinates and engineering KPI comparison work',corners=barcelona['geometry']['corners'],delta_s=barcelona['laps']['measured_lap_delta_s'])
    screenshot('barcelona_lap_analysis','v090')
    for width in (480,960,1600):
        call('Emulation.setDeviceMetricsOverride',dict(width=width,height=1200,deviceScaleFactor=1,mobile=False));time.sleep(.5)
        assert value("Array.from(document.querySelectorAll('iframe')).every(f=>f.contentDocument.documentElement.scrollWidth<=f.clientWidth+2)")
        record('v090 responsive lap analysis '+str(width))
    # The original attachment has no validated complete lap; it must never be
    # substituted with a synthetic circuit merely to fill this new page.
    click("Array.from(document.querySelectorAll('a')).find(a=>a.getAttribute('href')?.endsWith('/Data_Explorer'))")
    ready("document.body.innerText.includes('Sezione analitica')");settled()
    click("Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(e=>e.innerText.trim()==='Carica file')")
    ready("document.querySelector('input[type=file]')!==null")
    root=call('DOM.getDocument',dict(depth=-1))['root']['nodeId']
    node=call('DOM.querySelector',dict(nodeId=root,selector='input[type=file]'))['nodeId']
    from pathlib import Path
    call('DOM.setFileInputFiles',dict(nodeId=node,files=[str(Path(__file__).resolve().parents[1]/'data/raw/telemetry.parquet')]))
    ready("document.body.innerText.includes('116,987')");settled()
    click(navigate);ready("document.body.innerText.includes('Servono giri completi verificati')");settled()
    assert value('('+charts+').length')==0
    record('v090 unsupported original attachment has explicit unavailable analysis and no fabricated track')
