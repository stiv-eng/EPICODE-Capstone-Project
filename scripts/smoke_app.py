"""Start a temporary local server, check HTTP health and optionally capture Chrome.

No external telemetry services are accessed. The child Streamlit process is
terminated when the check finishes. Screenshots are local ignored artifacts.
"""
import argparse
import base64
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def capture(browser, base, artifacts):
    # This optional check uses the already installed websockets package. CDP
    # waits for rendered content in real time; virtual-time CLI screenshots can
    # capture Streamlit's loading placeholders before Python finishes.
    from websockets.sync.client import connect
    with tempfile.TemporaryDirectory(prefix='telemetry-browser-', dir=artifacts) as profile:
        chrome = subprocess.Popen([
            str(browser), '--headless', '--disable-gpu', '--no-first-run',
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

                def call(method, params=None):
                    nonlocal sequence
                    sequence += 1
                    connection.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
                    while True:
                        message = json.loads(connection.recv(timeout=10))
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

                def screenshot(name):
                    image = call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
                    path = artifacts/f'{name}_v05.png'
                    path.write_bytes(base64.b64decode(image['data']))
                    print(f'Captured {path}', flush=True)

                def choose(label,text):
                    html=call('Runtime.evaluate',{'expression':"Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).map(e=>e.outerHTML)",'returnByValue':True})
                    (artifacts/'browser_select_controls.json').write_text(json.dumps(html,indent=2),encoding='utf-8')
                    def click(expression):
                        script='(()=>{const r=('+expression+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()'
                        result=call('Runtime.evaluate',{'expression':script,'returnByValue':True})
                        coordinates=result['result']['value']
                        call('Input.dispatchMouseEvent',{'type':'mousePressed','button':'left','clickCount':1,**coordinates})
                        call('Input.dispatchMouseEvent',{'type':'mouseReleased','button':'left','clickCount':1,**coordinates})
                    element="Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(e=>e.innerText.includes("+json.dumps(label)+")).querySelector('[role=combobox]')"
                    click(element)
                    ready("Array.from(document.querySelectorAll('[role=option]')).some(e=>e.innerText.includes("+json.dumps(text)+"))")
                    click("Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText.includes("+json.dumps(text)+"))")

                call('Emulation.setDeviceMetricsOverride', {'width': 1600, 'height': 1200,
                                                          'deviceScaleFactor': 1, 'mobile': False})
                call('Page.navigate', {'url': base})
                ready("document.body.innerText.includes('Apri Data Explorer')")
                screenshot('home')
                call('Page.navigate', {'url': base+'/Data_Explorer'})
                ready("document.body.innerText.includes('116,987') && document.body.innerText.includes('Dataset e qualità')")
                screenshot('explorer')
                for name, label in [('signals', 'Segnali'), ('position', 'Posizione')]:
                    call('Runtime.evaluate', {'expression': "Array.from(document.querySelectorAll('[role=tab]')).find(t=>t.innerText==="+json.dumps(label)+").click()"})
                    ready("Array.from(document.querySelectorAll('[data-testid=stPlotlyChart]')).some(e=>e.getBoundingClientRect().height>100)")
                    call('Runtime.evaluate', {'expression': "Array.from(document.querySelectorAll('[data-testid=stPlotlyChart]')).find(e=>e.getBoundingClientRect().height>100).scrollIntoView({block:'start'})"})
                    time.sleep(.5)
                    screenshot(name)
                for name,route,expected in [
                    ('overview','overview','Statistiche dei segnali'),
                    ('inputs','inputs','Eventi osservati / completi'),
                    ('dynamics','dynamics','Diagramma G-G'),
                    ('tyres','tyres','Famiglia pneumatici'),
                    ('comparison','comparison','Canali confrontati'),
                    ('trajectory','position','Campione selezionato nella finestra'),
                ]:
                    call('Page.navigate',{'url':base+'/'+route})
                    ready('document.body.innerText.includes('+json.dumps(expected)+')')
                    ready("Array.from(document.querySelectorAll('[data-testid=stPlotlyChart]')).some(e=>e.getBoundingClientRect().height>100)")
                    time.sleep(.4)
                    screenshot(name)
                if (ROOT/'data/raw/gt7_trial_mountain_962c/data/laps/lap_015.parquet').exists():
                    call('Page.navigate',{'url':base+'/overview'})
                    ready("document.body.innerText.includes('Statistiche dei segnali')")
                    choose('Dataset analizzato','GT7')
                    ready("document.body.innerText.includes('GT7 Trial Mountain / Porsche 962 C') && document.body.innerText.includes('Giri verificati e feature candidate')")
                    screenshot('gt7_overview')
                    call('Page.navigate',{'url':base+'/comparison'})
                    ready("document.body.innerText.includes('Canali confrontati')")
                    choose('Sessione A','GT7')
                    ready("document.body.innerText.includes('Sessione B')")
                    choose('Sessione B','GT7')
                    call('Runtime.evaluate',{'expression':"Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(e=>e.innerText.includes('Giri verificati')).click()"})
                    ready("document.body.innerText.includes('Giro verificato A') && document.body.innerText.includes('shared track-distance reference')")
                    ready("document.querySelectorAll('[data-testid=stPlotlyChart]').length>0")
                    screenshot('gt7_lap_comparison')
        finally:
            chrome.terminate()
            try:
                chrome.wait(timeout=8)
            except subprocess.TimeoutExpired:
                chrome.kill()
                chrome.wait()


def smoke(browser=None):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    artifacts = ROOT/'artifacts'
    artifacts.mkdir(exist_ok=True)
    with (artifacts/'smoke_server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py',
            '--server.headless=true', '--server.address=127.0.0.1',
            f'--server.port={port}', '--server.fileWatcherType=none',
        ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
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
                capture(browser, base, artifacts)
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
    smoke(parser.parse_args().browser)
