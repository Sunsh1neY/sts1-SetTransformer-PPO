"""Start or reopen the local frozen M0 console without duplicate servers."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parents[2]
URL='http://127.0.0.1:8767/'
def healthy():
    try:
        with urllib.request.urlopen(URL+'api/health',timeout=2) as response:
            data=json.load(response)
            return data.get('app')=='frozen-m0-console-v1' and bool(data.get('root')) and Path(data['root']).resolve()==ROOT
    except Exception:return False
if healthy():
    webbrowser.open(URL);print('Opened existing console: '+URL);sys.exit(0)
logs=ROOT/'runs/m0-console-service';logs.mkdir(parents=True,exist_ok=True)
stamp=time.strftime('%Y%m%d-%H%M%S')
with (logs/(stamp+'.log')).open('w',encoding='utf-8') as log:
    process=subprocess.Popen([sys.executable,'-B',str(ROOT/'tools/battle-console/server.py')],cwd=ROOT,
        stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_BREAKAWAY_FROM_JOB)
for _ in range(60):
    if process.poll() is not None:raise SystemExit('Server exited. Inspect '+str(logs/(stamp+'.log')))
    if healthy():webbrowser.open(URL);print('Console ready: '+URL);break
    time.sleep(1)
else:raise SystemExit('Startup not confirmed. Inspect '+str(logs/(stamp+'.log')))
