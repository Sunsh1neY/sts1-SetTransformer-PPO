"""Launch one smoke-passed critic experiment with a memory admission check."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sts.train.resource_telemetry import memory_sample

def main():
    p=argparse.ArgumentParser();p.add_argument('--architecture',choices=('m3a','c_w128','c_d4'),required=True)
    args=p.parse_args()
    report=json.loads((ROOT/'runs'/('critic-smoke-'+args.architecture+'-v1')/'report.json').read_bytes())
    if report['status']!='passed':raise SystemExit('Minimal smoke did not pass')
    resource=memory_sample()
    if resource['available_ram_mb']<2048 or resource.get('commit_limit_mb',1e10)-resource.get('commit_used_mb',0)<4096:
        raise SystemExit('Insufficient RAM/commit headroom for another run: '+json.dumps(resource))
    out=ROOT/'runs'/('critic-'+args.architecture+'-v1')
    if out.exists():raise SystemExit('Run directory exists; refusing duplicate launch')
    log=ROOT/'runs'/('critic-'+args.architecture+'-service.log')
    with log.open('x',encoding='utf8') as stream:
        process=subprocess.Popen([sys.executable,'-B',str(ROOT/'scripts/run-critic-ablation.py'),
            '--architecture',args.architecture,'--backend-root',str(ROOT/'third_party/sts_lightspeed'),
            '--output',str(out)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_BREAKAWAY_FROM_JOB)
    print(json.dumps(dict(architecture=args.architecture,pid=process.pid,output=str(out),resources=resource)))

if __name__=='__main__':main()
