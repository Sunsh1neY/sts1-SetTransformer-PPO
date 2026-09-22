"""Explicit restart of one interrupted experiment without overwriting its history."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sts.train.resource_telemetry import memory_sample
p=argparse.ArgumentParser();p.add_argument('--architecture',choices=('m3a','c_w128','c_d4'),required=True)
p.add_argument('--generation',type=int,default=1)
a=p.parse_args()
if a.generation<1:raise SystemExit('Generation must be positive')
parent=ROOT/'runs'/('critic-'+a.architecture+('-v1' if a.generation==1 else '-resume-v'+str(a.generation-1)))
out=ROOT/'runs'/('critic-'+a.architecture+'-resume-v'+str(a.generation))
if out.exists():raise SystemExit('Resume output exists; refusing duplicate launch')
r=memory_sample()
if r['available_ram_mb']<2048 or r['commit_limit_mb']-r['commit_used_mb']<4096:
    raise SystemExit('Insufficient memory headroom: '+json.dumps(r))
with (ROOT/'runs'/('critic-'+a.architecture+'-resume-service-v'+str(a.generation)+'.log')).open('x',encoding='utf8') as f:
    process=subprocess.Popen([sys.executable,'-B',str(ROOT/'scripts/resume-critic-ablation.py'),
        '--architecture',a.architecture,'--parent',str(parent),'--output',str(out),
        '--backend-root',str(ROOT/'third_party/sts_lightspeed')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_BREAKAWAY_FROM_JOB)
print(json.dumps(dict(architecture=a.architecture,pid=process.pid,output=str(out),memory=r)))
