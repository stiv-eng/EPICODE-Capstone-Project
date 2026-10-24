"""Actual Chrome pointer/axis tests for the shared offline hover component."""
import json
import time


def exercise(call,ready,choose,click,screenshot,base,artifacts,fixture_only=False,barcelona=False,ml_only=False):
    results=[]
    def value(expression):
        r=call('Runtime.evaluate',{'expression':expression,'returnByValue':True})
        if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')
    def record(name,**evidence):
        results.append(dict(check=name,status='passed',**evidence))
        (artifacts/('UI_BROWSER_V071.json' if barcelona else 'UI_BROWSER_V063.json')).write_text(json.dumps(results,indent=2),encoding='utf-8',newline='\n')
        print('PASS:',name,flush=True)
    def settled():
        time.sleep(.5)
        ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
        assert not value("Array.from(document.querySelectorAll('[data-testid=stException]')).map(e=>e.innerText)")
    def navigate(route,text):
        click("Array.from(document.querySelectorAll('a')).find(e=>e.getAttribute('href')?.endsWith('/"+route+"'))")
        ready('document.body.innerText.includes('+json.dumps(text)+')');settled()
    def radio(label,option):
        click("Array.from(document.querySelectorAll('[data-testid=stRadio]')).find(e=>e.innerText.includes("+json.dumps(label)+")) && Array.from(Array.from(document.querySelectorAll('[data-testid=stRadio]')).find(e=>e.innerText.includes("+json.dumps(label)+")).querySelectorAll('label')).find(e=>e.innerText.trim()==="+json.dumps(option)+")")
        settled()
    # Same-origin component frames are inspected through the real browser DOM.
    allcharts="Array.from(document.querySelectorAll('iframe')).flatMap(f=>Array.from(f.contentDocument?.querySelectorAll('.js-plotly-plot')||[]).filter(p=>p._fullLayout).map(p=>({f,p})))"
    def chart(index=0):
        ready('('+allcharts+').length>'+str(index))
        ready('('+allcharts+').every(o=>o.f.contentDocument.body.dataset.ready==="true")')
        return '('+allcharts+')['+str(index)+']'
    def hover(name,index=0,trace_index=0,fraction=.45,expected_panels=None):
        selected=chart(index)
        value('('+selected+').f.scrollIntoView({block:"start"})')
        # Align the desired subplot in the outer Streamlit scroll container.
        geometry="(()=>{const {f,p}="+selected+";const d=p._fullData.filter(t=>t.meta?.channel&&(t.type==='box'||t.type==='bar'||Array.from(t.x||[]).some(Number.isFinite)))["+str(trace_index)+"],a=p._fullLayout;if(['histogram','bar','box'].includes(d.type)){const paths=Array.from(p.querySelectorAll('.barlayer .point path,.boxlayer .box')).filter(e=>e.getBoundingClientRect().height>1&&e.getBoundingClientRect().width>1);const r=f.getBoundingClientRect(),b=paths[Math.floor(paths.length*.45)].getBoundingClientRect();return {x:r.x+b.x+b.width/2,y:r.y+b.y+b.height/2,channel:d.meta.channel}}const xa=a[(d.xaxis||'x').replace('x','xaxis')],ya=a[(d.yaxis||'y').replace('y','yaxis')];let i=Math.floor(d.x.length*"+str(fraction)+");for(let n=0;n<d.x.length;n++){const j=(i+n)%d.x.length;if(Number.isFinite(d.x[j])&&Number.isFinite(d.y[j])){i=j;break;}}const r=f.getBoundingClientRect(),q=p.getBoundingClientRect();return {x:r.x+q.x+xa._offset+xa.c2p(d.x[i]),y:r.y+q.y+ya._offset+ya.c2p(d.y[i]),time:d.x[i],channel:d.meta.channel}})()"
        pos=value(geometry)
        value("document.querySelector('[data-testid=stMain]').scrollTop+="+str(pos['y']-430))
        time.sleep(.25);pos=value(geometry)
        call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':5,'y':5})
        call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':pos['x'],'y':pos['y']})
        time.sleep(.3)
        state=value("(()=>{const {f,p}="+selected+";const panel=p.closest('.comparison'),r=panel.querySelector('.readout'),b=r.getBoundingClientRect(),a=p.getBoundingClientRect();return {text:r.innerText,mode:p._fullLayout.meta.hover_mode,rows:Array.from(r.querySelectorAll('.reading')).map(e=>({id:e.dataset.selectionId,color:e.style.borderColor,time:e.dataset.sampleTime,text:e.innerText})),lines:Array.from(panel.querySelectorAll('.time-cursor')).map(e=>({x:+e.getAttribute('x1'),y:+e.getAttribute('y1'),time:+e.dataset.time,axis:e.dataset.axis})),native:p.querySelectorAll('.hoverlayer .hovertext,.hoverlayer .legend').length,outside:b.left>=a.right||b.top>=a.bottom,point:panel.querySelectorAll('.point-focus').length,channel:r.dataset.hoveredChannel}})()")
        assert state['outside'] and state['native']==0,state
        assert 'N/D'!=state['text'].strip() and ('t = ' in state['text'] if state['mode']=='time' else state['point']>0 or 'Punto grafico' in state['text']),state
        if expected_panels is not None:assert len(state['lines'])==expected_panels,state
        if state['mode']=='time':
            errors=value("(()=>{const {p}="+selected+";return Array.from(p.parentNode.querySelectorAll('.time-cursor')).map(e=>{const a=p._fullLayout[e.dataset.axis.split(':')[0].replace('x','xaxis')];return Math.abs(+e.getAttribute('x1')-(a._offset+a.c2p(+e.dataset.time)))})})()")
            assert max(errors,default=0)<.05,errors
            state['pixelErrors']=errors
        record(name,**state)
        record(name+' rendering budget',figures=value('('+allcharts+').length'),
               components=value("document.querySelectorAll('iframe').length"),
               heap_bytes=value('performance.memory?.usedJSHeapSize'),
               runtime=value('('+selected+').f.contentDocument.body.dataset.runtimeSource'),
               runtime_load_ms=value('Number(('+selected+').f.contentDocument.body.dataset.runtimeLoadMs)'),
               plot_ready_ms=value('Number(('+selected+').f.contentDocument.body.dataset.plotReadyMs)'),
               hover_frame_ms=value('Number(('+selected+').p.dataset.hoverLatencyMs||0)'),
               figure_payload_bytes=value('JSON.stringify(('+selected+').p.data).length'))
        return state
    def snapshot(name):screenshot(name,'v071' if barcelona else 'v063')
    if fixture_only:
        call('Page.navigate',{'url':base});ready("document.body.innerText.includes('Offline legacy chart fixtures')");settled()
        for i in range(3):hover('Offline legacy type fixture '+str(i),i)
        clockless=hover('Clockless Signals use source index without temporal cursor',3)
        assert clockless['mode']=='xy' and not clockless['lines'] and 'Campione sorgente' in clockless['text']
        snapshot('legacy_types')
        return
    if not ml_only:
        call('Page.navigate',{'url':base});ready("document.body.innerText.includes('Apri Data Explorer')");settled()
        navigate('Data_Explorer','Sezione analitica')
        for source in (('GT7','ACGym','Barcelona') if barcelona else ('GT7','ACGym')):
            if source=='ACGym':choose('Dataset analizzato','ACGym');settled()
            if source=='Barcelona':choose('Dataset analizzato','Barcelona GP');settled()
            for section in ('Signals','Driver Inputs','Vehicle Dynamics','Tyre Analysis','Cockpit','Position / Track Map'):
                radio('Sezione analitica',section)
                if section=='Cockpit':
                    click("Array.from(document.querySelectorAll('[data-testid=stCheckbox]')).find(e=>e.innerText.includes('Mostra tracce di contesto'))?.querySelector('label')");settled()
                if source in ('ACGym','Barcelona') and section=='Position / Track Map':
                    assert value("document.body.innerText.includes('Track visualization unavailable')")
                    record('ACGym unavailable XY explained');continue
                hover(source+' '+section)
                if section=='Vehicle Dynamics':
                    count=value('('+allcharts+').length')
                    for index in range(1,count):hover(source+' dynamics chart '+str(index),index)
                    gg=value("(()=>{const {p}=("+allcharts+").find(o=>o.p._fullLayout.title?.text?.includes('G-G'));const x=p._fullLayout.xaxis,y=p._fullLayout.yaxis;return {width:x._length,height:y._length,ratio:(x._length/(x.range[1]-x.range[0]))/(y._length/(y.range[1]-y.range[0]))}})()")
                    assert abs(gg['ratio']-1)<1e-6,gg;record(source+' equal GG geometry',**gg)
                if section=='Position / Track Map':
                    marker=value('('+chart()+').p._fullLayout.meta');assert marker['vehicle_theta'] is not None;record('GT7 preserved vehicle orientation',**marker)
                if section in ('Signals','Position / Track Map','Vehicle Dynamics'):snapshot(source+'_'+section.split(' ')[0])
        navigate('comparison','Sessione A')
        choose('Sessione A','GT7');choose('Sessione B','GT7');settled()
        # Four selected channels, using the real Streamlit control.
        multi="Array.from(document.querySelectorAll('[data-testid=stMultiSelect]')).find(e=>e.innerText.includes('Canali'))"
        click('('+multi+").querySelector('input')")
        ready("document.querySelector('[role=option]')!==null")
        options=value("Array.from(document.querySelectorAll('[role=option]')).map(e=>e.innerText)")
        candidate=next((x for x in options if 'rpm' in x),options[0])
        click("Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText==="+json.dumps(candidate)+")")
        call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Escape','windowsVirtualKeyCode':27});settled()
        initial=hover('GT7 comparison four channels',expected_panels=4)
        ids=[r['id'] for r in initial['rows']];colors=[r['color'] for r in initial['rows']]
        f=chart()
        # Adversarial event order and unavailable samples supplement real pointer checks.
        ordered=value("(()=>{const {f,p}="+f+";const points=p._fullData.filter(t=>t.meta.channel===p._fullData[0].meta.channel).map(t=>({data:t,x:20,y:0})).reverse();p.emit('plotly_hover',{points});return Array.from(p.parentNode.parentNode.querySelectorAll('.reading')).map(e=>e.dataset.selectionId)})()")
        assert ordered==ids;record('Shuffled hover points preserve selection rows',ids=ordered)
        policy=value("(()=>{const {f}="+f+";const t={x:[0,.1,.2,10,10.1],y:[1,2,NaN,4,5],meta:{tolerance:.051}};return {gap:f.contentWindow.nearest(t,5),missing:f.contentWindow.nearest(t,.2),observed:f.contentWindow.nearest(t,.1)}})()")
        assert policy['gap'] is None and policy['missing'] is None and policy['observed']['y']==2
        record('Gap and null samples never interpolate',**policy)
        missing=value("(()=>{const {f,p}="+f+";const traces=p._fullData.filter(t=>t.meta.channel===p._fullData[0].meta.channel);const time=Array.from(traces[0].x).find(x=>f.contentWindow.nearest(traces[0],x)&&!f.contentWindow.nearest(traces[1],x));if(time===undefined)return null;f.contentWindow.updateTime(time,{chart:p},traces[0].meta.channel);return Array.from(p.parentNode.parentNode.querySelectorAll('.reading')).map(e=>({id:e.dataset.selectionId,text:e.querySelector('.value').innerText}))})()")
        assert missing and [r['id'] for r in missing]==ids and missing[0]['text']!='N/D' and missing[1]['text']=='N/D',missing
        record('Unavailable second selection keeps its fixed row',rows=missing)
        for ti,frac in [(1,.2),(2,.7),(3,.85)]:
            s=hover('GT7 comparison channel '+str(ti),trace_index=ti,fraction=frac,expected_panels=4)
            assert [r['id'] for r in s['rows']]==ids and [r['color'] for r in s['rows']]==colors
        snapshot('comparison_cursor')
        # Relayout applies actual Plotly zoom/pan; axis transforms are rechecked.
        value("(()=>{const {f,p}="+f+";f.contentWindow.Plotly.relayout(p,{'xaxis.range':[10,90],'xaxis2.range':[10,90],'xaxis3.range':[10,90],'xaxis4.range':[10,90]});})()")
        time.sleep(.4);hover('GT7 zoom cursor alignment',fraction=.4,expected_panels=4)
        value("(()=>{const {f,p}="+f+";f.contentWindow.Plotly.relayout(p,{'xaxis.range':[20,100],'xaxis2.range':[20,100],'xaxis3.range':[20,100],'xaxis4.range':[20,100]});})()")
        time.sleep(.4);hover('GT7 pan cursor alignment',fraction=.5,expected_panels=4)
        before=value('JSON.stringify(('+f+').p.data)')
        value("window.hoverRuns=0;window.hoverObserver=new MutationObserver(ms=>{for(const m of ms)if(m.attributeName==='data-test-script-state'&&m.target.getAttribute(m.attributeName)!=='notRunning')window.hoverRuns++;});window.hoverObserver.observe(document.querySelector('[data-testid=stApp]'),{attributes:true})")
        value('('+f+').p.focus()')
        key_before=value('('+f+').p.parentNode.querySelector(".time-cursor").dataset.time')
        call('Input.dispatchKeyEvent',{'type':'keyDown','key':'ArrowRight','windowsVirtualKeyCode':39})
        time.sleep(.2)
        assert before==value('JSON.stringify(('+f+').p.data)') and value('window.hoverRuns')==0
        assert key_before!=value('('+f+').p.parentNode.querySelector(".time-cursor").dataset.time')
        record('Keyboard sample inspection leaves figure data and Python idle unchanged')
        # Test actual hover throughput without emitting application state messages.
        start=time.perf_counter()
        for i in range(20):
            call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':650+i*5,'y':430})
        time.sleep(.2)
        assert value('window.hoverRuns')==0 and before==value('JSON.stringify(('+f+').p.data)')
        record('Twenty pointer updates without rerun or numerical mutation',elapsed_s=time.perf_counter()-start)
        retained=value('('+f+').p.parentNode.parentNode.querySelector(".readout").innerText')
        call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':5,'y':5});time.sleep(.2)
        assert retained==value('('+f+').p.parentNode.parentNode.querySelector(".readout").innerText')
        record('Last readout retained on leave')
        for width in (960,480,1600):
            call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1200,'deviceScaleFactor':1,'mobile':False});time.sleep(.6)
            hover('comparison responsive '+str(width),fraction=.4,expected_panels=4)
            assert value("Array.from(document.querySelectorAll('iframe')).every(f=>f.contentDocument.documentElement.scrollWidth<=f.clientWidth+2)")
            snapshot('comparison_'+str(width))
        click('('+multi+").querySelector('input')")
        ready("Array.from(document.querySelectorAll('[role=option]')).some(e=>e.innerText==='gear')")
        click("Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText==='gear')")
        call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Escape','windowsVirtualKeyCode':27});settled()
        changed=hover('Changed channels preserve cursor and identity',expected_panels=5)
        assert [r['id'] for r in changed['rows']]==ids and [r['color'] for r in changed['rows']]==colors
        radio('Modalità confronto','Finestre di sessione')
        hover('GT7 time windows',expected_panels=5)
        choose('Sessione A','ACGym');choose('Sessione B','ACGym');settled()
        radio('Modalità confronto','Giri verificati')
        hover('ACGym verified comparison',expected_panels=5)
        click("Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes('Sessione B'))?.querySelector('[role=combobox]')")
        ready("Array.from(document.querySelectorAll('[role=option]')).filter(e=>e.innerText.includes('ACGym')).length>1")
        click("Array.from(document.querySelectorAll('[role=option]')).filter(e=>e.innerText.includes('ACGym'))[1]");settled()
        cross=hover('Compatible ACGym recordings retain distinct selection identities',expected_panels=5)
        assert cross['rows'][0]['id'][2:]!=cross['rows'][1]['id'][2:]
        if barcelona:
            choose('Sessione A','Barcelona GP');choose('Sessione B','Barcelona GP');settled()
            hover('Barcelona verified comparison',expected_panels=5)
    else:
        call('Page.navigate',{'url':base});ready("document.body.innerText.includes('Apri Data Explorer')");settled()
    navigate('ml','Machine Learning')
    if barcelona:
        assert value("Array.from(document.querySelectorAll('[data-testid=stMetric]')).some(e=>e.innerText.includes('Giri validati')&&e.innerText.includes('205'))")
        assert value("document.body.innerText.includes('103')&&document.body.innerText.includes('66')&&document.body.innerText.includes('36')")
        record('Barcelona inclusive population and frozen split visible',laps=205)
    button="Array.from(document.querySelectorAll('button')).find(e=>e.innerText.includes('Addestra e valuta'))"
    click(button);settled()
    ready('('+allcharts+').length>=2')
    for i in range(value('('+allcharts+').length')):hover('ML chart '+str(i),i)
    if barcelona:
        assert value("document.body.innerText.includes('SVR')")
        visible_mae=value("(()=>{const rows=("+chart()+").p._fullData.flatMap(t=>Array.from(t.x||[]).map((x,i)=>Math.abs(x-t.y[i]))).filter(Number.isFinite);return rows.reduce((a,b)=>a+b,0)/rows.length})()")
        assert abs(visible_mae-15.393290962555847)<1e-8,visible_mae
        radio('Partizione di valutazione','validation')
        choose('Modello da ispezionare','Random Forest');settled()
        hover('Barcelona validation Random Forest scatter')
        choose('Modello da ispezionare','Ridge');settled()
        hover('Barcelona validation Ridge scatter')
        radio('Partizione di valutazione','test')
        assert value("Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes('Modello da ispezionare'))?.querySelector('[role=combobox]')?.value==='SVR'")
        record('Barcelona training action reuses frozen evaluation; validation and selected-only test distinguished')
    snapshot('ML_external')
    navigate('replay','Progressive Prediction')
    for i in range(2):hover('Replay causal chart '+str(i),i)
    payload=value('('+allcharts+').map(o=>JSON.stringify(o.p.data))')
    assert all('target_s' not in x and 'actual_s' not in x for x in payload)
    assert not value("document.body.innerText.includes('Risultato finale verificato')")
    record('Replay hidden target absent from hover payload')
    if barcelona:
        (artifacts/'replay_controls.html').write_text(value('document.documentElement.outerHTML'),encoding='utf-8')
        slider="document.querySelector('[role=slider],input[type=range]')"
        click(slider)
        call('Input.dispatchKeyEvent',{'type':'keyDown','key':'End','windowsVirtualKeyCode':35})
        call('Input.dispatchKeyEvent',{'type':'keyUp','key':'End','windowsVirtualKeyCode':35})
        settled()
        ready("Array.from(document.querySelectorAll('[data-testid=stMetric]')).some(e=>e.innerText.includes('Tempo osservato')&&parseFloat(e.querySelector('[data-testid=stMetricValue]')?.innerText)>=59.9&&parseFloat(e.querySelector('[data-testid=stMetricValue]')?.innerText)<=60.1)")
        hover('Barcelona progressive 60-second causal signal')
        hover('Barcelona progressive prediction history',1)
        before=value('('+allcharts+').map(o=>JSON.stringify(o.p.data))')
        click("Array.from(document.querySelectorAll('[data-testid=stCheckbox]')).find(e=>e.innerText.includes('Mostra valutazione retrospettiva'))?.querySelector('label')")
        settled();assert value("document.body.innerText.includes('Risultato finale verificato')")
        assert before==value('('+allcharts+').map(o=>JSON.stringify(o.p.data))')
        record('Barcelona retrospective target reveal leaves causal chart payload unchanged')
    snapshot('replay_causal')
    perf=value("({heap:performance.memory?.usedJSHeapSize,figures:("+allcharts+").length,components:document.querySelectorAll('iframe').length,runtimeResources:Array.from(document.querySelectorAll('iframe')).flatMap(f=>f.contentWindow.performance.getEntriesByType('resource').filter(r=>r.name.includes('plotly.min.js')).map(r=>({name:r.name,transfer:r.transferSize,bytes:r.decodedBodySize})))})")
    record('Final browser performance',**perf)
