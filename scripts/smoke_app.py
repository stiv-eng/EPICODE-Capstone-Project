"""Start a temporary local server, check HTTP health and optionally capture Chrome.

No external telemetry services are accessed. The child Streamlit process is
terminated when the check finishes. Screenshots are local ignored artifacts.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))  # Support both `python scripts/...` and `python -m scripts...`.


def capture(browser, base, artifacts, scenario='v062'):
    # This optional check uses the already installed websockets package. CDP
    # waits for rendered content in real time; virtual-time CLI screenshots can
    # capture Streamlit's loading placeholders before Python finishes.
    from websockets.sync.client import connect
    with tempfile.TemporaryDirectory(prefix='telemetry-browser-', dir=artifacts, ignore_cleanup_errors=True) as profile:
        chrome = subprocess.Popen([
            str(browser), '--headless', '--no-first-run',
            '--no-default-browser-check', '--remote-debugging-port=0',
            f'--user-data-dir={profile}', '--window-size=1600,1200', 'about:blank',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            port_file = Path(profile)/'DevToolsActivePort'
            deadline = time.monotonic()+15
            while not port_file.exists():
                if chrome.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Chrome debugging endpoint unavailable')
                time.sleep(.2)
            port = int(port_file.read_text().splitlines()[0])
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=3) as response:
                targets = json.load(response)
            target = next(t for t in targets if t['type'] == 'page')
            with connect(target['webSocketDebuggerUrl'], max_size=16*1024*1024) as connection:
                sequence = 0
                events=[]

                def call(method, params=None):
                    nonlocal sequence
                    sequence += 1
                    connection.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
                    while True:
                        message = json.loads(connection.recv(timeout=10))
                        if message.get('method') in ('Log.entryAdded','Runtime.consoleAPICalled','Runtime.exceptionThrown'):
                            events.append(message)
                        if message.get('id') == sequence:
                            if 'error' in message:
                                raise RuntimeError(message['error'])
                            return message.get('result', {})

                def ready(expression):
                    deadline = time.monotonic()+40
                    while time.monotonic() < deadline:
                        result = call('Runtime.evaluate', {'expression': expression, 'returnByValue': True})
                        if result.get('result', {}).get('value'):
                            return
                        time.sleep(.25)
                    body = call('Runtime.evaluate', {'expression': 'document.body.innerText', 'returnByValue': True})
                    raise RuntimeError(f'Browser did not render expected content: {body}')

                def screenshot(name,version='v05'):
                    image = call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
                    path = artifacts/f'{name}_{version}.png'
                    path.write_bytes(base64.b64decode(image['data']))
                    print(f'Captured {path}', flush=True)

                def click_element(expression):
                    ready('Boolean('+expression+')')
                    call('Runtime.evaluate',{'expression':'('+expression+").scrollIntoView({block:'center'})"})
                    time.sleep(.15)  # Allow responsive iframe height/layout to settle before the real click.
                    script='(()=>{const r=('+expression+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()'
                    coordinates=call('Runtime.evaluate',{'expression':script,'returnByValue':True})['result']['value']
                    call('Input.dispatchMouseEvent',{'type':'mousePressed','button':'left','clickCount':1,**coordinates})
                    call('Input.dispatchMouseEvent',{'type':'mouseReleased','button':'left','clickCount':1,**coordinates})

                def choose(label,text):
                    html=call('Runtime.evaluate',{'expression':"Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).map(e=>e.outerHTML)",'returnByValue':True})
                    (artifacts/'browser_select_controls.json').write_text(json.dumps(html,indent=2),encoding='utf-8')
                    element="Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes("+json.dumps(label)+"))?.querySelector('[role=combobox]')"
                    click_element(element)
                    visible=call('Runtime.evaluate',{'expression':"Array.from(document.querySelectorAll('[role=option]')).some(e=>e.innerText.includes("+json.dumps(text)+"))",'returnByValue':True})
                    if not visible.get('result',{}).get('value'):
                        call('Runtime.evaluate',{'expression':'('+element+').focus()'})
                        call('Input.dispatchKeyEvent',{'type':'keyDown','key':'a','code':'KeyA','modifiers':2,'windowsVirtualKeyCode':65})
                        call('Input.dispatchKeyEvent',{'type':'keyUp','key':'a','code':'KeyA','modifiers':2,'windowsVirtualKeyCode':65})
                        call('Input.insertText',{'text':text})
                    ready("Array.from(document.querySelectorAll('[role=option]')).some(e=>e.innerText.includes("+json.dumps(text)+"))")
                    click_element("Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText.includes("+json.dumps(text)+"))")
                    time.sleep(.5)
                    ready("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")

                call('Emulation.setDeviceMetricsOverride', {'width':1600,'height':1200,'deviceScaleFactor':1,'mobile':False})
                call('Runtime.enable')
                call('Log.enable')
                if scenario=='v090':
                    from scripts.smoke_ui_v090 import exercise
                elif scenario=='fixtures':
                    from functools import partial
                    from scripts.smoke_ui_v082 import exercise as shared_exercise
                    exercise=partial(shared_exercise,fixture_only=True)
                elif scenario=='uploads':
                    from scripts.smoke_ui_v062 import exercise
                else:
                    from scripts.smoke_ui_v082 import exercise
                try:
                    exercise(call,ready,choose,click_element,screenshot,base,artifacts)
                finally:
                    (artifacts/f'browser_console_{scenario}.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
        finally:
            chrome.terminate()
            try:
                chrome.wait(timeout=8)
            except subprocess.TimeoutExpired:
                chrome.kill()
                chrome.wait()


def smoke(browser=None,entrypoint='streamlit_app.py',scenario='v082'):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    artifacts = ROOT/('artifacts/v090' if scenario=='v090' else 'artifacts/v082')/scenario
    artifacts.mkdir(parents=True,exist_ok=True)
    with (artifacts/'smoke_server.log').open('w', encoding='utf-8') as log:
        environment=dict(os.environ)
        # Verification runs with prediction dependencies and local model access
        # forbidden. No ignored model files are moved or deleted for this test.
        guard = artifacts/'import_guard'
        guard.mkdir(exist_ok=True)
        (guard/'sitecustomize.py').write_text('from scripts.analysis_guard import install\ninstall()\n',encoding='utf-8')
        environment['PYTHONPATH'] = os.pathsep.join([str(guard), str(ROOT), environment.get('PYTHONPATH','')])
        server = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', entrypoint,
            '--server.headless=true', '--server.address=127.0.0.1',
            f'--server.port={port}', '--server.fileWatcherType=none',
        ], cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        try:
            base = f'http://127.0.0.1:{port}'
            deadline = time.monotonic() + 25
            while True:
                try:
                    with urllib.request.urlopen(base+'/_stcore/health', timeout=1) as response:
                        assert response.status == 200
                        assert response.read() == b'ok'
                    break
                except OSError:
                    if server.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Streamlit did not become healthy; see artifacts/smoke_server.log')
                    time.sleep(.25)
            with urllib.request.urlopen(base, timeout=3) as response:
                assert response.status == 200
            print('PASS: Streamlit HTTP homepage and health endpoint return 200.')
            if browser:
                capture(browser, base, artifacts,scenario)
        finally:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, help='Optional local Chrome/Chromium executable')
    parser.add_argument('--release',choices=['v082','v090','uploads','fixtures'],default='v090')
    options=parser.parse_args()
    entrypoint=('scripts/hover_fixture_app.py' if options.release=='fixtures'
                else 'streamlit_app.py')
    smoke(options.browser,entrypoint=entrypoint,scenario=options.release)
