"""Serve canonical resumed curves on the existing dashboard port."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--generation',type=int,default=1);args=p.parse_args()
view=ROOT/'runs/critic-dashboard-view'
paths={'M0':ROOT/'runs/a-v2-ppo-v1/tensorboard/a-v2-ppo-v1',
       'M2a-complete':view/'m2a-complete'}
for name in ('m3a','c_w128','c_d4'):
    paths[name]=ROOT/'runs'/('critic-'+name+'-resume-v'+str(args.generation))/'tensorboard'/(name+'-v1')
with (view/('tensorboard-resume-v'+str(args.generation)+'.log')).open('x',encoding='utf8') as f:
    process=subprocess.Popen([sys.executable,'-m','tensorboard.main','--host','127.0.0.1',
        '--port','6008','--reload_interval','5','--logdir_spec',
        ','.join(name+':'+str(path) for name,path in paths.items())],cwd=ROOT,
        stdout=f,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_BREAKAWAY_FROM_JOB)
print(json.dumps(dict(pid=process.pid,url='http://127.0.0.1:6008/')))
