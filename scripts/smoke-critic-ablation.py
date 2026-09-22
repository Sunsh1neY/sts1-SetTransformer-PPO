"""One tiny real collector/update/checkpoint/dev path per approved critic variant."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG",":4096:8")
import sys,json,time,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"third_party/sts_lightspeed/build"))
import torch
from sts.models.architectures.critic_variants import MODELS
from sts.models.architectures.m2a_source_context.model import M2aActorCritic
from sts.models.apath import batch_samples
from sts.train.critic_ablation import CriticTrainer
from sts.train.corpus_evaluation import evaluate

def main():
    p=argparse.ArgumentParser();p.add_argument("--architecture",choices=MODELS,required=True)
    args=p.parse_args()
    out=ROOT/"runs"/("critic-smoke-"+args.architecture+"-v1")
    out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.manual_seed(834100);reference=M2aActorCritic()
    trainer=CriticTrainer(architecture=args.architecture,group=100,device="cuda",
        num_envs=2,num_steps=8,total_transitions=16,
        corpus_dir=ROOT/"projects/battle-initial-states/corpora/a-v2",corpus_scope="smoke-only")
    paired=0
    for key,value in reference.state_dict().items():
        if not key.startswith(("critic_","value_head.")):
            assert torch.equal(value,trainer.model.state_dict()[key].cpu()),key
            paired+=1
    batch=batch_samples(trainer.observations,"cuda")
    trainer.model.zero_grad(set_to_none=True)
    trainer.model.value_only(batch).sum().backward()
    gradient=trainer.model.critic_pool_seed.grad
    assert gradient is not None and torch.isfinite(gradient).all()
    assert (gradient.abs().sum(-1)>0).all(),"Every critic seed must reach Value"
    if args.architecture=="c_w128":assert trainer.model.critic_input.weight.grad.abs().sum()>0
    if args.architecture=="c_d4":assert trainer.model.critic_blocks[3].qkv.weight.grad.abs().sum()>0
    trainer.model.zero_grad(set_to_none=True)
    metrics,episodes=trainer.iteration_step(time.monotonic()+600)
    assert trainer.env_steps==16 and trainer.iteration==1
    for key in ("policy_loss","value_loss","entropy","approx_kl","grad_norm"):
        assert __import__("math").isfinite(metrics[key]),key
    trainer.save(out/"checkpoint.pt")
    restored=CriticTrainer.load(out/"checkpoint.pt")
    for key,value in trainer.model.state_dict().items():
        assert torch.equal(value,restored.model.state_dict()[key]),key
    with torch.no_grad():
        a=trainer.model(batch)[0].probs;b=restored.model(batch)[0].probs
        assert torch.equal(a,b)
    cases=json.loads((ROOT/"runs/a-v2-ppo-v1/evaluation-cases.json").read_bytes())["audit-dev"][:1]
    result=evaluate(restored.model,restored.corpus,cases,time.monotonic()+120,lambda *a:None)
    assert result[0]["terminated"] and not result[0]["truncated"]
    report=dict(status="passed",architecture=args.architecture,
        parameter_count=sum(p.numel() for p in trainer.model.parameters()),
        paired_noncritic_tensors=paired,metrics=metrics,dev_episode=result[0],
        scope="16 smoke transitions only; formal initialization discarded and rebuilt")
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps(report),flush=True)

if __name__=="__main__":main()
