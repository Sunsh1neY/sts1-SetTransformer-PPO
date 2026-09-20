"""Loopback-only frozen M0 interactive dev console. No training or holdout access."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

ROOT=Path(__file__).resolve().parents[2]
APP=Path(__file__).resolve().parent
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8767)
    parser.add_argument('--backend-root',type=Path,default=ROOT/'third_party/sts_lightspeed')
    args=parser.parse_args()
    sys.path.insert(0,str(args.backend_root/'build'))
    import torch
    from sts.env.acorpus import ACorpus,ACorpusSmokeEnv
    from sts.env.lightspeed import _load_backend
    from sts.models.apath import APathActorCritic,encode,batch_samples,TASKS
    spec=importlib.util.spec_from_file_location('labels',ROOT/'scripts/build-m0-player.py')
    labels=importlib.util.module_from_spec(spec);spec.loader.exec_module(labels)
    corpus_path=ROOT/'projects/battle-initial-states/corpora/a-v2'
    corpus=ACorpus(corpus_path)
    run=ROOT/'runs/a-v2-ppo-v1'
    fp=json.loads((run/'fingerprint.json').read_bytes())
    for key,value in fp.items():
        path=Path(_load_backend().__file__) if key=='backend' else corpus_path/key[7:] if key.startswith('corpus/') else ROOT/key
        if hashlib.sha256(path.read_bytes()).hexdigest()!=value:raise ValueError('Fingerprint mismatch: '+key)
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    device='cuda'
    registry=json.loads((APP/'models.json').read_bytes())
    models={m['id']:m for m in registry['models']}
    def load_model(model_id):
        if model_id not in models:raise ValueError('Unregistered model')
        entry=models[model_id]
        path=(ROOT/entry['checkpoint']).resolve()
        if ROOT not in path.parents or path.suffix!='.pt':raise ValueError('Invalid checkpoint path')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Checkpoint SHA256 mismatch')
        if entry['architecture']!=APathActorCritic.model_version:raise ValueError('Unsupported model architecture')
        checkpoint=torch.load(path,map_location='cpu',weights_only=False)
        if checkpoint['fingerprint']!=fp:raise ValueError('Checkpoint fingerprint mismatch')
        candidate=APathActorCritic().to(device)
        candidate.load_state_dict(checkpoint['model'],strict=True)
        candidate.eval().requires_grad_(False)
        return candidate,dict(id=model_id,label=entry['label'],sha256=entry['sha256'],
            iteration=checkpoint['iteration'],architecture=entry['architecture'])
    model,model_info=load_model(registry['default'])
    allowed={k:r for k,r in corpus.rows.items() if r['provenance']['partition']=='audit-dev'}
    token=secrets.token_urlsafe(32)
    session={};revision=0
    def inspect():
        obs=session['obs']
        actions=[];value=None
        if not session['done']:
            sample=encode(obs)
            with torch.no_grad():dist,v=model(batch_samples([sample],device))
            value=v.item();session.update(sample=sample,dist=dist)
            for u,routes in enumerate(sample.routes):
                for j,route in enumerate(routes):
                    c=dict(route=route,task=TASKS[sample.tasks[u]])
                    actions.append(dict(id=f'{u}:{j}',label=labels.action_label(c,obs),
                        probability=dist.probs[0,u,j].item(),source_probability=dist.source_probs[0,u].item(),
                        target_probability=dist.target_probs[0,u,j].item()))
        return dict(revision=revision,model=model_info,active=True,done=session['done'],state_hash=session['key'],
            player=obs['player'],hand=obs['hand'],enemies=obs['enemies'],potions=obs['potions'],
            relics=obs['relics'],value=value,actions=actions,history=session['history'],result=session.get('result'))
    def command(data):
        nonlocal revision,model,model_info
        op=data['op']
        if op=='model-select':
            candidate,info=load_model(data['model'])
            model,model_info=candidate,info
            session.clear();revision+=1
            return dict(active=False,model=model_info,revision=revision)
        if op=='reset':
            key=data['key']
            if key not in allowed:raise ValueError('Only fixed dev states are permitted')
            env=ACorpusSmokeEnv(corpus,scope='experiment-protocol-v1')
            obs=env.reset(corpus.scene(key),0,purpose='evaluation')
            session.clear();session.update(key=key,env=env,obs=obs,done=False,history=[],
                rng=torch.Generator(device=device).manual_seed(700000))
        elif op in ('model','manual'):
            if not session or session['done']:raise ValueError('No active battle')
            if data.get('revision')!=revision:raise ValueError('Stale decision; refresh before acting')
            sample,dist=session['sample'],session['dist']
            manual=None
            if op=='manual':
                a,b=map(int,data['action'].split(':'))
                if not (0<=a<len(sample.routes) and 0<=b<len(sample.routes[a])):raise ValueError('Illegal action')
                manual=(a,b)
            with torch.no_grad():u,j=dist.sample(session['rng'])
            u,j=u.item(),j.item()
            proposed=labels.action_label(dict(route=sample.route(u,j),task=TASKS[sample.tasks[u]]),session['obs'])
            if op=='manual':
                u,j=manual
            route=sample.route(u,j)
            label=labels.action_label(dict(route=route,task=TASKS[sample.tasks[u]]),session['obs'])
            obs,reward,term,trunc,info=session['env'].step(route)
            session['history'].append(dict(step=len(session['history'])+1,actor=op,action=label,
                model_proposal=proposed,probability=dist.probs[0,u,j].item(),
                route={k:v for k,v in route.items() if k not in ('snapshot','decision_id')}))
            session.update(obs=obs,done=term or trunc)
            if term or trunc:session['result']=dict(terminated=term,truncated=trunc,reward=reward,
                outcome=info.get('task_outcome'),potion_uses=info['reward_accounting']['potion_uses'])
        else:raise ValueError('Unknown operation')
        revision+=1
        return inspect()
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,payload,kind='application/json'):
            body=payload.encode() if isinstance(payload,str) else json.dumps(payload,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def valid_host(self):return self.headers.get('Host') in (f'127.0.0.1:{args.port}',f'localhost:{args.port}')
        def do_GET(self):
            if not self.valid_host():return self.reply(403,{'error':'Host rejected'})
            if self.path=='/':
                html=(APP/'console.html').read_text(encoding='utf-8')
                return self.reply(200,html.replace('__TOKEN__',token),'text/html')
            if self.path=='/api/catalog':
                return self.reply(200,dict(cases=[dict(key=k,encounter=r['state']['encounter'],act=r['state']['act'],
                    hp=r['state']['player']['hp'],max_hp=r['state']['player']['max_hp'],
                    kind='augmentation' if 'augmentation' in r['evidence'] else 'natural') for k,r in sorted(allowed.items())]))
            if self.path=='/api/models':return self.reply(200,{'models':list(models.values()),'current':model_info})
            if self.path=='/api/state':return self.reply(200,inspect() if session else {'active':False,'model':model_info,'revision':revision})
            if self.path=='/api/health':return self.reply(200,{'app':'frozen-m0-console-v1','dev_cases':len(allowed),'root':str(ROOT),'model':model_info})
            self.reply(404,{'error':'Not found'})
        def do_POST(self):
            if not self.valid_host() or self.headers.get('X-Console-Token')!=token:return self.reply(403,{'error':'Request rejected'})
            if self.path!='/api/command':return self.reply(404,{'error':'Not found'})
            try:
                length=int(self.headers.get('Content-Length',0))
                if not 0<length<8192:raise ValueError('Invalid body size')
                data=json.loads(self.rfile.read(length))
                if data.get('op')=='shutdown':
                    import threading
                    self.reply(200,{'stopped':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                result=command(data)
                self.reply(200,result)
            except Exception as exc:self.reply(400,{'error':str(exc)})
    print(f'Frozen M0 console ready: http://127.0.0.1:{args.port}/',flush=True)
    HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
