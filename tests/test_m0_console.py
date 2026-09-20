"""Opt-in live integration checks in a separate loopback console process."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_no_training_operations():
    source=(ROOT/'tools/battle-console/server.py').read_text(encoding='utf-8')
    for forbidden in ('from sts.train','torch.optim','.backward(','torch.save('):
        assert forbidden not in source


@pytest.mark.skipif(os.environ.get('M0_CONSOLE_INTEGRATION')!='1',reason='Requires local CUDA and frozen artifacts')
def test_live_console():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    proc=subprocess.Popen([sys.executable,'-B',str(ROOT/'scripts/m0-console.py'),'--port',str(port)],
        cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    url=f'http://127.0.0.1:{port}'
    def get(path):
        with urllib.request.urlopen(url+path,timeout=10) as r:return r.read()
    token=None
    def post(data,auth=True):
        headers={'Content-Type':'application/json'}
        if auth:headers['X-Console-Token']=token
        req=urllib.request.Request(url+'/api/command',data=json.dumps(data).encode(),headers=headers)
        with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
    try:
        for _ in range(40):
            if proc.poll() is not None:raise RuntimeError('Console startup failed')
            try:page=get('/').decode();break
            except urllib.error.URLError:time.sleep(.5)
        else:raise TimeoutError('Console startup timed out')
        token=re.search("TOKEN='([^']+)'",page).group(1)
        catalog=json.loads(get('/api/catalog'))['cases'];assert len(catalog)==288
        models=json.loads(get('/api/models'));assert len(models['models'])==7
        assert models['current']['id']=='selected' and models['current']['iteration']==256
        switched=post({'op':'model-select','model':'initial'})
        assert not switched['active'] and switched['model']['iteration']==0
        switched=post({'op':'model-select','model':'final'})
        assert switched['model']['iteration']==256
        with pytest.raises(urllib.error.HTTPError):post({'op':'model-select','model':'unregistered'})
        assert json.loads(get('/api/state'))['model']['id']=='final'
        post({'op':'model-select','model':'selected'})
        with pytest.raises(urllib.error.HTTPError) as err:post({'op':'reset','key':catalog[0]['key']},auth=False)
        assert err.value.code==403
        with pytest.raises(urllib.error.HTTPError):post({'op':'reset','key':'not-dev'})
        s=post({'op':'reset','key':catalog[0]['key']});revision=s['revision']
        s=post({'op':'manual','revision':revision,'action':s['actions'][0]['id']})
        assert s['history'][0]['actor']=='manual' and 'route' in s['history'][0]
        with pytest.raises(urllib.error.HTTPError):post({'op':'model','revision':revision})
        s=post({'op':'reset','key':catalog[0]['key']})
        while not s['done']:s=post({'op':'model','revision':s['revision']})
        expected=next(json.loads(line) for line in (ROOT/'runs/a-v2-ppo-v1/dev-0256-episodes.jsonl').read_text().splitlines() if json.loads(line)['state_hash']==catalog[0]['key'])
        assert len(s['history'])==expected['steps']
        assert s['result']['reward']==pytest.approx(expected['reward'])
        assert s['result']['terminated'] and not s['actions']
        assert post({'op':'shutdown'})['stopped']
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
