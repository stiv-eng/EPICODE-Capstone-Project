"""Run the actual local v0.6 explorer read from Git, without changing the checkout.

The archived page is executed in an ignored artifact script. Its original SVG/GL
choices and eager tabs remain intact. Existing local data and current source
registration helper are reused; no baseline source or dataset is overwritten.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def exercise(call,ready,choose,click,screenshot,base,artifacts):
    def value(expression):
        result=call('Runtime.evaluate',{'expression':expression,'returnByValue':True})
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result['result'].get('value')
    call('Page.addScriptToEvaluateOnNewDocument',{'source':"window.telemetryLostContexts=0; document.addEventListener('webglcontextlost',()=>window.telemetryLostContexts++,true);"})
    call('Page.navigate',{'url':base})
    ready("document.body.innerText.includes('116,987') && document.querySelectorAll('[data-testid=stPlotlyChart]').length>=2")
    value("window.telemetryLostContexts=0; document.addEventListener('webglcontextlost',()=>window.telemetryLostContexts++,true)")
    click("Array.from(document.querySelectorAll('[role=tab]')).find(e=>e.innerText==='Segnali')")
    ready("document.querySelectorAll('[data-testid=stMultiSelect]').length>0")
    for _ in range(4):
        click("document.querySelector('[data-testid=stMultiSelect] [role=combobox]')")
        ready("document.querySelector('[role=option]')!==null")
        click("document.querySelector('[role=option]')")
        time.sleep(.7)
        ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
    call('Input.dispatchKeyEvent',{'type':'rawKeyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27})
    for _ in range(3):
        for block in ('start','end','center'):
            value("document.querySelector('[data-testid=stPlotlyChart]').scrollIntoView({block:"+json.dumps(block)+"})")
            time.sleep(.4)
        for label in ('Posizione','Segnali'):
            click("Array.from(document.querySelectorAll('[role=tab]')).find(e=>e.innerText==="+json.dumps(label)+")")
            time.sleep(.4)
    screenshot('v06_baseline_eight_channels','v061')
    value("document.querySelector('[data-testid=stPlotlyChart]').scrollIntoView({block:'end'})")
    time.sleep(.5)
    screenshot('v06_baseline_eight_channels_bottom','v061')
    result=value("({lostEvents:window.telemetryLostContexts,canvases:document.querySelectorAll('.gl-container canvas').length,charts:document.querySelectorAll('[data-testid=stPlotlyChart]').length,exception:document.querySelector('[data-testid=stException]')?.innerText||null})")
    result['limitation']='Headless local Chrome; intermittent device-specific disappearance may not reproduce. Archived page uses current source registration helper only.'
    (artifacts/'RENDERING_BASELINE_V061.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Baseline browser observation: '+json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',type=Path,required=True)
    browser=parser.parse_args().browser
    source=subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}','show','49639f4:pages/00_Data_Explorer.py'],cwd=ROOT).decode('utf-8')
    artifacts=ROOT/'artifacts'
    artifacts.mkdir(exist_ok=True)
    script=artifacts/'v06_explorer_baseline.py'
    script.write_text("import streamlit as st\nst.set_page_config(layout='wide')\n"+
                      f"exec(compile({source!r}, 'v06_baseline_explorer', 'exec'), {{'__file__': {str(ROOT/'pages/00_Data_Explorer.py')!r}}})\n",encoding='utf-8')
    from smoke_app import smoke
    smoke(browser,str(script),'baseline')
