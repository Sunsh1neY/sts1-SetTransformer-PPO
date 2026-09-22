"""Read-only TensorBoard display copies join the two historical M2a segments."""
from pathlib import Path
import shutil
import subprocess
import sys
import json

ROOT=Path(__file__).resolve().parents[1]
view=ROOT/'runs/critic-dashboard-view'
merged=view/'m2a-complete'
merged.mkdir(parents=True,exist_ok=True)
sources=[ROOT/'runs/m2a-source-context-v1/tensorboard/m2a-source-context-v1',
         ROOT/'runs/m2a-source-context-continuation-v2/tensorboard/m2a-continuation']
for folder in sources:
    for source in folder.glob('events.out.tfevents.*'):
        target=merged/source.name
        if target.exists():
            if target.read_bytes()!=source.read_bytes():raise ValueError('Display copy conflict')
        else:shutil.copy2(source,target)
paths={'M0':ROOT/'runs/a-v2-ppo-v1/tensorboard/a-v2-ppo-v1','M2a-complete':merged}
for name in ('m3a','c_w128','c_d4'):
    paths[name]=ROOT/'runs'/('critic-'+name+'-v1')/'tensorboard'/(name+'-v1')
spec=','.join(name+':'+str(path) for name,path in paths.items())
with (view/'tensorboard.log').open('x',encoding='utf8') as log:
    process=subprocess.Popen([sys.executable,'-m','tensorboard.main','--host','127.0.0.1',
        '--port','6008','--reload_interval','5','--logdir_spec',spec],cwd=ROOT,
        stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_BREAKAWAY_FROM_JOB)
print(json.dumps(dict(pid=process.pid,url='http://127.0.0.1:6008/',
    caveat='M2a display merges existing events only; unrecorded continuation tags are not fabricated.')))
