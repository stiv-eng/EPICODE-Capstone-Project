"""Real Chrome v0.6.1 workflow, invoked by smoke_app's CDP harness."""
import json
import time


def exercise(call,ready,choose,click,screenshot,base,artifacts):
    results=[]

    def evaluate(expression):
        result=call('Runtime.evaluate',{'expression':expression,'returnByValue':True})
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result['result'].get('value')

    def settled():
        time.sleep(.4)
        ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'")
        errors=evaluate("Array.from(document.querySelectorAll('[data-testid=stException]')).map(e=>e.innerText)")
        assert not errors,errors

    def navigate(route,text):
        click("Array.from(document.querySelectorAll('a')).find(e=>e.getAttribute('href')?.endsWith('/"+route+"'))")
        ready('document.body.innerText.includes('+json.dumps(text)+')')
        settled()

    def radio(label,option):
        click("Array.from(document.querySelectorAll('[data-testid=stRadio]')).find(e=>e.innerText.includes("+json.dumps(label)+")) && Array.from(Array.from(document.querySelectorAll('[data-testid=stRadio]')).find(e=>e.innerText.includes("+json.dumps(label)+")).querySelectorAll('label')).find(e=>e.innerText.trim()==="+json.dumps(option)+")")
        settled()

    def chart_check(name):
        settled()
        ready("document.querySelectorAll('[data-testid=stPlotlyChart]').length>0 && Array.from(document.querySelectorAll('[data-testid=stPlotlyChart]')).every(e=>e.querySelectorAll('.scatterlayer path').length>0)")
        charts=evaluate("Array.from(document.querySelectorAll('[data-testid=stPlotlyChart]')).map(e=>({height:e.getBoundingClientRect().height,paths:e.querySelectorAll('.scatterlayer path').length,gl:e.querySelectorAll('.gl-container canvas').length}))")
        assert charts and all(c['height']>100 and c['paths']>0 and c['gl']==0 for c in charts),(name,charts)
        for position in ('start','end','center'):
            evaluate("Array.from(document.querySelectorAll('[data-testid=stPlotlyChart]')).at(-1).scrollIntoView({block:"+json.dumps(position)+"})")
            time.sleep(.2)
            assert evaluate("Array.from(document.querySelectorAll('[data-testid=stPlotlyChart]')).every(e=>e.querySelectorAll('.scatterlayer path').length>0)")
        results.append({'check':name,'status':'passed','charts':charts})

    def advance_slider(label):
        element="Array.from(document.querySelectorAll('[data-testid=stSlider]')).find(e=>e.innerText.includes("+json.dumps(label)+"))?.querySelector('input[type=range],[role=slider]')"
        click(element)
        before=evaluate('('+element+').value || ('+element+').getAttribute("aria-valuenow")')
        for _ in range(3):
            call('Input.dispatchKeyEvent',{'type':'rawKeyDown','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
            call('Input.dispatchKeyEvent',{'type':'keyUp','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
            time.sleep(.35)
        settled()
        after=evaluate('('+element+').value || ('+element+').getAttribute("aria-valuenow")')
        assert before!=after,(label,before,after)
        return {'before':before,'after':after}

    call('Page.navigate',{'url':base})
    ready("document.body.innerText.includes('Apri Data Explorer')")
    settled();screenshot('home','v061')
    navigate('Data_Explorer','Sezione analitica')
    sections=['Signals','Driver Inputs','Vehicle Dynamics','Tyre Analysis','Cockpit','Position / Track Map']
    for source in ('original','GT7','ACGym'):
        if source!='original':
            choose('Dataset analizzato',source)
            settled()
        else:
            ready("document.body.innerText.includes('116,987')")
        for section in sections:
            radio('Sezione analitica',section)
            if section=='Cockpit':
                advance=advance_slider('Istante replay (s)')
                results.append({'check':source+' cockpit actual sample replay','status':'passed',**advance})
            elif source=='ACGym' and section=='Position / Track Map':
                body=evaluate('document.body.innerText')
                assert ('non disponibile' in body or 'unavailable' in body),body
                results.append({'check':source+' '+section+' capability fallback','status':'passed'})
            else:
                chart_check(source+' '+section+' scrolling')
            screenshot(source.lower()+'_'+section.split('/')[0].strip().lower().replace(' ','_'),'v061')
        if source=='GT7':
            radio('Sezione analitica','Signals')
            click("Array.from(document.querySelectorAll('[data-testid=stMultiSelect]')).find(e=>e.innerText.includes('Giri verificati'))?.querySelector('[role=combobox]')")
            ready("document.querySelector('[role=option]')!==null")
            click("document.querySelector('[role=option]')")
            call('Input.dispatchKeyEvent',{'type':'rawKeyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27})
            settled()
            # The multiselect's first option selects all available verified laps.
            assert evaluate("document.body.innerText.includes('Giri verificati') && document.body.innerText.includes('Lap ')")
            chart_check('GT7 multiple verified laps Signals')
            screenshot('gt7_selected_laps','v061')
            # Revisit sections repeatedly to exercise chart mounting and state retention.
            for section in ('Position / Track Map','Signals','Cockpit','Signals'):
                radio('Sezione analitica',section)
                if section!='Cockpit':chart_check('GT7 revisit '+section)
    navigate('overview','Statistiche dei segnali')
    choose('Dataset analizzato','GT7');settled()
    assert evaluate("document.querySelectorAll('[data-testid=stPlotlyChart]').length===0")
    screenshot('overview','v061')
    navigate('comparison','Canali confrontati')
    settled()
    assert evaluate("document.body.innerText.includes('Giro verificato A') && document.body.innerText.includes('Lap ')")
    chart_check('GT7 lap comparison')
    legend=evaluate("Array.from(document.querySelectorAll('.legend .legendtext')).map(e=>e.textContent)")
    assert len(legend)==2 and all('Lap ' in text for text in legend),legend
    results.append({'check':'single shared comparison legend','status':'passed','entries':legend})
    screenshot('gt7_lap_comparison','v061')
    choose('Sessione A','ACGym');settled()
    choose('Sessione B','ACGym');settled()
    chart_check('ACGym verified lap comparison')
    screenshot('acgym_comparison','v061')
    navigate('Data_Explorer','Sezione analitica')
    choose('Dataset analizzato','telemetry.parquet');settled()
    assert evaluate("document.body.innerText.includes('Intervallo di sessione (s)') && !Array.from(document.querySelectorAll('label')).some(e=>e.innerText.trim()==='Giri verificati')")
    radio('Sezione analitica','Signals');chart_check('original fallback after source changes')
    advance_slider('Intervallo di sessione (s)')
    navigate('ml','Feature causali')
    assert evaluate("document.body.innerText.includes('Addestra e valuta')")
    screenshot('ml_unchanged','v061')
    navigate('replay','Checkpoint trascorso')
    ready("document.querySelectorAll('[data-testid=stPlotlyChart]').length>=2")
    advance_slider('Checkpoint trascorso')
    assert not evaluate("document.body.innerText.includes('Risultato finale verificato')")
    screenshot('progressive_unchanged','v061')
    # Cockpit should also fit a narrow browser. This does not emulate a real phone GPU.
    navigate('Data_Explorer','Sezione analitica')
    radio('Sezione analitica','Cockpit')
    call('Emulation.setDeviceMetricsOverride',{'width':480,'height':960,'deviceScaleFactor':1,'mobile':False})
    time.sleep(.7)
    overflow=evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert not overflow,'Horizontal document overflow in narrow Cockpit'
    evaluate("Array.from(document.querySelectorAll('[data-testid=stMarkdownContainer]')).find(e=>e.innerText.includes('SPEED'))?.scrollIntoView({block:'center'})")
    time.sleep(.3)
    screenshot('cockpit_narrow','v061')
    results.append({'check':'480px cockpit viewport without document overflow','status':'passed'})
    (artifacts/'UI_BROWSER_V061.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(f'PASS: {len(results)} real-browser checks; all three sources, six sections, scrolling, replay, comparison, ML.',flush=True)
