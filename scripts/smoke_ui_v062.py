"""Chrome acceptance: actual scale/shape geometry, hover, icons and file upload."""
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]


def exercise(call,ready,choose,click,screenshot,base,artifacts):
    results=[]
    def value(expression):
        response=call('Runtime.evaluate',{'expression':expression,'returnByValue':True})
        if 'exceptionDetails' in response:raise RuntimeError(response['exceptionDetails'])
        return response['result'].get('value')
    def record(name,**evidence):
        results.append({'check':name,'status':'passed',**evidence})
        (artifacts/'UI_BROWSER_V062.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    def settled():
        time.sleep(.4)
        ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
        assert not value("Array.from(document.querySelectorAll('[data-testid=stException]')).map(e=>e.innerText)")
    def navigate(route,label):
        click("Array.from(document.querySelectorAll('a')).find(e=>e.getAttribute('href')?.endsWith('/"+route+"'))")
        ready('document.body.innerText.includes('+json.dumps(label)+')');settled()
    def radio(label,option):
        click("Array.from(document.querySelectorAll('[data-testid=stRadio]')).find(e=>e.innerText.includes("+json.dumps(label)+")) && Array.from(Array.from(document.querySelectorAll('[data-testid=stRadio]')).find(e=>e.innerText.includes("+json.dumps(label)+")).querySelectorAll('label')).find(e=>e.innerText.trim()==="+json.dumps(option)+")")
        settled()
    def snap(name):screenshot(name,'v062')
    def charts(name):
        ready("(Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout)).reduce((n,p)=>n+p.querySelectorAll('.scatterlayer path').length,0)>0")
        for block in ('start','end','center'):
            value("Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).at(-1).scrollIntoView({block:"+json.dumps(block)+"})")
            time.sleep(.15)
        assert value("Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).every(e=>e.querySelectorAll('.scatterlayer path').length>0)")
        record(name)
    def gg_check(label):
        ready("Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).some(e=>e._fullLayout?.title?.text?.includes('G-G'))")
        measured=value("(()=>{const p=Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).find(e=>e._fullLayout?.title?.text?.includes('G-G')); const x=p._fullLayout.xaxis,y=p._fullLayout.yaxis;return {xPixels:x._length,yPixels:y._length,xRange:x.range,yRange:y.range,pixelsPerUnitRatio:(x._length/(x.range[1]-x.range[0]))/(y._length/(y.range[1]-y.range[0]))}})()")
        assert abs(measured['pixelsPerUnitRatio']-1)<1e-6,measured
        assert abs(measured['xPixels']-measured['yPixels'])<2,measured
        value("Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).find(e=>e.innerText.includes('G-G')).scrollIntoView({block:'center'})")
        snap(label)
        record(label,**measured)
    def key(name,code):
        call('Input.dispatchKeyEvent',{'type':'rawKeyDown','key':name,'code':name,'windowsVirtualKeyCode':code})
        call('Input.dispatchKeyEvent',{'type':'keyUp','key':name,'code':name,'windowsVirtualKeyCode':code})
    def marker_check(label):
        ready("Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).some(e=>e._fullLayout?.meta?.vehicle_sample!==undefined)")
        measured=value("(()=>{const p=Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).find(e=>e._fullLayout?.meta?.vehicle_sample!==undefined);const m=p._fullLayout.meta; const shapes=Array.from(p.querySelectorAll('.shapelayer path'));const front=shapes[1]?.getBBox();const x=p._fullLayout.xaxis.l2p(m.vehicle_x)+p._fullLayout.xaxis._offset,y=p._fullLayout.yaxis.l2p(m.vehicle_y)+p._fullLayout.yaxis._offset; return {...m,shapes:shapes.length,front:front?{x:front.x+front.width/2-x,y:front.y+front.height/2-y}:null,bodyBounds:shapes[0]?{width:shapes[0].getBBox().width,height:shapes[0].getBBox().height}:null}})()")
        assert measured['shapes']==6,measured
        import math
        front=measured['front'];angle=measured['vehicle_theta']
        dot=(front['x']*math.cos(angle)-front['y']*math.sin(angle))/math.hypot(front['x'],front['y'])
        assert dot>.9,(dot,measured)
        assert 'estimated' in measured['orientation_basis']
        record(label,**measured,front_alignment=dot)
        snap(label)
        return measured
    def iframe(axis='lap_elapsed_s',source='GT7'):
        condition="f.contentDocument?.querySelector('#telemetry')?._fullLayout?.meta?.comparison_axis==="+json.dumps(axis)+" && f.contentDocument.querySelector('#telemetry')._fullLayout.meta.selection_labels.every(s=>s.includes("+json.dumps(source)+"))"
        ready("Array.from(document.querySelectorAll('iframe')).some(f=>"+condition+")")
        return "Array.from(document.querySelectorAll('iframe')).find(f=>"+condition+")"
    def hover_check(label,row):
        frame=iframe('relative_s' if 'window' in label else 'lap_elapsed_s','ACGym' if 'acgym' in label else 'GT7')
        value('('+frame+").scrollIntoView({block:'center'})")
        time.sleep(.3)
        position=value("(()=>{const f="+frame+",p=f.contentDocument.querySelector('#telemetry');const d=p._fullData.find(t=>t.yaxis==='y"+('' if row==1 else str(row))+"');const x=p._fullLayout[d.xaxis.replace('x','xaxis')], y=p._fullLayout[d.yaxis.replace('y','yaxis')];const i=Math.floor(d.x.length*.45);const r=f.getBoundingClientRect();return {x:r.x+x._offset+x.c2p(d.x[i]),y:r.y+y._offset+y.c2p(d.y[i]),channel:d.meta.channel};})()")
        call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':10,'y':10})
        call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':position['x'],'y':position['y']})
        ready('('+frame+").contentDocument.querySelector('#readout').dataset.hoveredChannel==="+json.dumps(position['channel']))
        measured=value("(()=>{const f="+frame+",doc=f.contentDocument;const a=doc.querySelector('#telemetry').getBoundingClientRect(), b=doc.querySelector('#readout').getBoundingClientRect();return {text:doc.querySelector('#readout').innerText,chartRight:a.right,readoutLeft:b.left,rows:doc.querySelectorAll('.reading').length,legendEntries:doc.querySelectorAll('.legend .legendtext').length,floatingLabels:doc.querySelectorAll('.hoverlayer .hovertext,.hoverlayer .legend').length}})()")
        assert measured['readoutLeft']>=measured['chartRight'] and measured['rows']==2 and measured['legendEntries']==2,measured
        assert measured['floatingLabels']==0 and 't = ' in measured['text'],measured
        snap(label);record(label,**measured)

    call('Page.navigate',{'url':base});ready("document.body.innerText.includes('Apri Data Explorer')");settled()
    for route,icon in [('overview','📈'),('comparison','📉')]:
        actual=value("Array.from(document.querySelectorAll('a')).find(e=>e.getAttribute('href')?.endsWith('/"+route+"'))?.innerText")
        assert icon in actual,(route,actual)
        record('sidebar icon '+route,rendered=actual)
    snap('home_icons')
    navigate('Data_Explorer','Sezione analitica')
    assert value("document.body.innerText.includes('GT7 Trial Mountain')")
    # Inspect real option labels before any explicit upload has occurred.
    click("Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes('Dataset analizzato'))?.querySelector('[role=combobox]')")
    ready("document.querySelector('[role=option]')!==null")
    options=value("Array.from(document.querySelectorAll('[role=option]')).map(e=>e.innerText)")
    assert not any('telemetry.parquet' in item for item in options)
    key('Escape',27);record('default GT7 and original absent from built-in catalog',options=options)
    for source in ('GT7','ACGym'):
        if source=='ACGym':choose('Dataset analizzato','ACGym');settled()
        for section in ('Signals','Driver Inputs','Vehicle Dynamics','Tyre Analysis','Cockpit','Position / Track Map'):
            radio('Sezione analitica',section)
            if section=='Vehicle Dynamics':
                gg_check(source.lower()+'_gg_desktop')
                if source=='GT7':
                    for width in (960,480):
                        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1100,'deviceScaleFactor':1,'mobile':False});time.sleep(.7)
                        gg_check('gt7_gg_'+str(width))
                    call('Emulation.setDeviceMetricsOverride',{'width':1600,'height':1200,'deviceScaleFactor':1,'mobile':False});time.sleep(.6)
                charts(source+' dynamics scrolling')
            elif section=='Position / Track Map':
                if source=='ACGym':
                    assert value("document.body.innerText.includes('Track visualization unavailable')")
                    record('ACGym missing coordinates explained');snap('acgym_no_position')
                else:
                    element="Array.from(document.querySelectorAll('[data-testid=stSlider]')).find(e=>e.innerText.includes('Campione selezionato'))?.querySelector('input[type=range],[role=slider]')"
                    click(element);key('Home',36);settled()
                    first=marker_check('gt7_vehicle_start')
                    key('End',35);settled()
                    last=marker_check('gt7_vehicle_end')
                    assert first['vehicle_sample']!=last['vehicle_sample']
                    key('Home',36);key('PageUp',33);settled()
                    marker_check('gt7_vehicle_middle')
                    # Pure data zoom: pixel-sized artwork must keep its screen size.
                    before=marker_check('gt7_vehicle_before_zoom')
                    value("(()=>{const p=Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).find(e=>e._fullLayout?.meta?.vehicle_sample!==undefined);const m=p._fullLayout.meta;return p.ownerDocument.defaultView.Plotly.relayout(p,{'xaxis.range':[m.vehicle_x-200,m.vehicle_x+200],'yaxis.range':[m.vehicle_y-200,m.vehicle_y+200]})})()")
                    time.sleep(.5)
                    after=marker_check('gt7_vehicle_zoom')
                    assert abs(before['bodyBounds']['width']-after['bodyBounds']['width'])<.2
                    record('vehicle fixed pixel size under zoom')
            elif section=='Cockpit':
                element="Array.from(document.querySelectorAll('[data-testid=stSlider]')).find(e=>e.innerText.includes('Istante replay'))?.querySelector('input[type=range],[role=slider]')"
                click(element);key('ArrowRight',39);settled()
                assert value("document.body.innerText.includes('Campione sorgente')")
                record(source+' Cockpit slider');snap(source.lower()+'_cockpit')
            else:charts(source+' '+section);snap(source.lower()+'_'+section.lower().replace(' ','_'))
    navigate('comparison','Canali confrontati')
    choose('Sessione A','GT7');settled();choose('Sessione B','GT7');settled()
    for row in (1,2,3):hover_check('gt7_lap_hover_'+str(row),row)
    radio('Modalità confronto','Finestre di sessione')
    for row in (1,3):hover_check('gt7_window_hover_'+str(row),row)
    choose('Sessione A','ACGym');settled();choose('Sessione B','ACGym');settled()
    hover_check('acgym_lap_hover',1)
    navigate('Data_Explorer','Sezione analitica')
    radio('Sorgente','Carica file')
    ready("document.querySelector('input[type=file]')!==null")
    root=call('DOM.getDocument',{'depth':-1})['root']['nodeId']
    node=call('DOM.querySelector',{'nodeId':root,'selector':'input[type=file]'})['nodeId']
    call('DOM.setFileInputFiles',{'nodeId':node,'files':[str(ROOT/'data/raw/telemetry.parquet')]})
    ready("document.body.innerText.includes('116,987') && document.body.innerText.includes('Intervallo di sessione (s)')")
    settled();radio('Sezione analitica','Signals');charts('original explicit Parquet upload Signals')
    radio('Sezione analitica','Position / Track Map');charts('original explicit upload source trajectory')
    assert value("document.body.innerText.includes('Orientation estimated') || document.body.innerText.includes('Orientation unavailable')")
    snap('original_uploaded_position');record('original actual browser file upload and audited mapping')
    stationary=artifacts/'stationary.csv'
    stationary.write_text('elapsed_s,pos_x,pos_y\n0,12,-8\n0.1,12,-8\n0.2,12,-8\n',encoding='utf-8')
    root=call('DOM.getDocument',{'depth':-1})['root']['nodeId']
    node=call('DOM.querySelector',{'nodeId':root,'selector':'input[type=file]'})['nodeId']
    call('DOM.setFileInputFiles',{'nodeId':node,'files':[str(stationary)]})
    ready("document.body.innerText.includes('stationary.csv')")
    settled()
    ready("Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).some(e=>e._fullLayout?.meta?.vehicle_x===12)")
    neutral=value("(()=>{const p=Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout).find(e=>e._fullLayout?.meta?.vehicle_x===12);return {meta:p._fullLayout.meta,shapes:p._fullLayout.shapes.length}})()")
    assert neutral['meta']['vehicle_theta'] is None and neutral['meta']['vehicle_y']==-8 and neutral['shapes']==0
    snap('stationary_neutral_position');record('stationary actual coordinates with neutral indicator',**neutral)
    navigate('ml','Feature causali');snap('ml_unchanged')
    assert value("document.body.innerText.includes('Addestra e valuta') && (Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout)).length===0")
    record('ML startup does not train')
    navigate('replay','Checkpoint trascorso');ready("(Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[])).filter(p=>p._fullLayout)).length>=2")
    assert not value("document.body.innerText.includes('Risultato finale verificato')")
    snap('progressive_unchanged');record('Progressive Prediction hidden target preserved')
    print(f'PASS: {len(results)} Chrome v0.6.2 checks including rendered scales, heading, hover and upload.',flush=True)
