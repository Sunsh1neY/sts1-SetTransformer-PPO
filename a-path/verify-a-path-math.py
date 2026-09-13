#!/usr/bin/env python3
"""A 路径独立数学验收；不加载游戏、不替代仓库集成测试。

标准库部分检查概率契约。安装 torch 时额外检查精确熵和 Pointer 梯度。
运行：python verify-a-path-math.py [--require-autograd] [--report path.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
from pathlib import Path
from typing import Sequence


def close(actual: float, expected: float, label: str) -> None:
    if not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10):
        raise AssertionError(f"{label}: actual={actual!r}, expected={expected!r}")


def entropy(probs: Sequence[float]) -> float:
    if not probs or any(not math.isfinite(p) or p < 0 for p in probs):
        raise ValueError("概率必须是非空、有限、非负序列")
    close(sum(probs), 1.0, "概率归一化")
    return -sum(p * math.log(p) for p in probs if p > 0)


def softmax(logits: Sequence[float]) -> list[float]:
    if not logits or any(not math.isfinite(x) for x in logits):
        raise ValueError("该核验函数只接受非空、有限logits")
    maximum = max(logits)
    weights = [math.exp(x - maximum) for x in logits]
    total = sum(weights)
    return [weight / total for weight in weights]


def standard_checks(fixture: dict) -> list[str]:
    names: list[str] = []
    case = fixture["joint_probability_case"]
    p1 = [row["p_source"] for row in case["sources"]]
    conditional = [row["target_probs"] for row in case["sources"]]
    joint = [pu * pj for pu, ps in zip(p1, conditional) for pj in ps]
    expected = case["expected_joint_probs"]
    if len(joint) != len(expected):
        raise AssertionError("联合动作数不同")
    for index, (actual, target) in enumerate(zip(joint, expected)):
        close(actual, target, f"联合概率[{index}]")
    close(sum(joint), 1.0, "完整动作归一化")
    names.append("来源和条件目标组成完整归一化分布")

    flat_entropy = entropy(joint)
    chain_entropy = entropy(p1) + sum(pu * entropy(ps) for pu, ps in zip(p1, conditional))
    close(flat_entropy, chain_entropy, "熵链式分解")
    close(flat_entropy, case["expected_joint_entropy_nats"], "黄金联合熵")
    names.append("精确联合熵与完整动作枚举一致")

    selected = fixture["selected_action_ratio_case"]
    old_logp = math.log(selected["old_source_probability"]) + math.log(selected["old_target_probability"])
    new_logp = math.log(selected["new_source_probability"]) + math.log(selected["new_target_probability"])
    close(old_logp, selected["expected_old_joint_log_probability"], "旧联合logp")
    close(math.exp(new_logp-old_logp), selected["expected_ratio"], "联合ratio")
    names.append("联合logp相加及联合ratio")

    for row in case["sources"]:
        if not row["requires_target"]:
            if row["target_probs"] != [1.0]:
                raise AssertionError("无目标分支须为退化概率1")
            close(math.log(row["target_probs"][0]), 0.0, "无目标logp")
            close(entropy(row["target_probs"]), 0.0, "无目标熵")
    names.append("无目标分支logp和熵为零")

    row = [math.log(.7), math.log(.3)]
    before, after = softmax(row), softmax([value+17.0 for value in row])
    for x, y in zip(before, after):
        close(x, y, "目标行平移不变")
    names.append("目标logits整行平移不改变条件概率")

    # 反例：目标行全零时，全局 raw b+t 会按目标数放大来源质量。
    wrong_joint = softmax([0.0, 0.0, 0.0])
    close(wrong_joint[0]+wrong_joint[1], 2/3, "错误方案来源总质量")
    correct_joint = [.5*.5, .5*.5, .5]
    close(correct_joint[0]+correct_joint[1], .5, "A路径来源总质量")
    if math.isclose(sum(wrong_joint[:2]), sum(correct_joint[:2])):
        raise AssertionError("应当识别raw b+t全局归一化的反例")
    names.append("识别raw b+t全局softmax与A路径不等价")

    greedy = fixture["sequential_greedy_counterexample"]
    close(greedy["source_probs"][0]*max(greedy["source_a_target_probs"]), .306, "顺序贪心")
    close(greedy["source_probs"][1], .4, "联合MAP")
    if not .4 > .306:
        raise AssertionError("反例失败")
    names.append("顺序贪心不等于joint MAP")

    ratio_source, ratio_target = 1.15, 1.15
    close(ratio_source*ratio_target, 1.3225, "ratio乘积")
    if not (ratio_source < 1.2 and ratio_target < 1.2 and ratio_source*ratio_target > 1.2):
        raise AssertionError("联合clipping反例失败")
    names.append("联合ratio与分别clipping的差异")
    return names


def autograd_checks() -> tuple[list[str], str]:
    import torch
    names: list[str] = []
    dtype = torch.float64
    b = torch.tensor([math.log(.4), math.log(.2), math.log(.3), math.log(.1)], dtype=dtype, requires_grad=True)
    t = torch.tensor([[math.log(.7), math.log(.3)], [0., 0.],
                      [math.log(.25), math.log(.75)], [0., 0.]], dtype=dtype, requires_grad=True)
    l1 = b.log_softmax(-1)
    l2a, l2p = t[0].log_softmax(-1), t[2].log_softmax(-1)
    ljoint = torch.cat((l1[0]+l2a, l1[1:2], l1[2]+l2p, l1[3:4]))
    p1 = l1.exp()
    hflat = -(ljoint.exp()*ljoint).sum()
    hsource = -(p1*l1).sum()
    hchain = hsource-p1[0]*(l2a.exp()*l2a).sum()-p1[2]*(l2p.exp()*l2p).sum()
    torch.testing.assert_close(hflat, hchain, rtol=1e-10, atol=1e-10)
    gflat = torch.autograd.grad(hflat, (b,t), retain_graph=True)
    gchain = torch.autograd.grad(hchain, (b,t), retain_graph=True)
    for actual, expected in zip(gflat, gchain):
        torch.testing.assert_close(actual, expected, rtol=1e-10, atol=1e-10)
    names.append("精确联合熵对来源与目标参数的梯度匹配枚举oracle")

    # PPO首次更新rho=1：所选完整动作A->X，Advantage=0.4。
    old_logp = ljoint[0].detach()
    ratio = (ljoint[0]-old_logp).exp()
    loss = torch.maximum(-.4*ratio, -.4*ratio.clamp(.8, 1.2))
    gb, gt = torch.autograd.grad(loss, (b,t))
    torch.testing.assert_close(gb, torch.tensor([-.24,.08,.12,.04], dtype=dtype), rtol=1e-10, atol=1e-10)
    expected_gt = torch.zeros_like(t)
    expected_gt[0] = torch.tensor([-.12,.12], dtype=dtype)
    torch.testing.assert_close(gt, expected_gt, rtol=1e-10, atol=1e-10)
    names.append("完整动作PPO同时训练来源和已选来源的目标分支")

    generator = torch.Generator(device="cpu").manual_seed(20260913)
    q = torch.randn(5, generator=generator, dtype=dtype, requires_grad=True)
    k = torch.randn(3,5, generator=generator, dtype=dtype, requires_grad=True)
    delta = torch.tensor([.1,.2,-.3], dtype=dtype)
    scores = k @ q / math.sqrt(5)
    gq, gk = torch.autograd.grad((scores*delta).sum(), (q,k))
    torch.testing.assert_close(gq, (delta[:,None]*k.detach()).sum(0)/math.sqrt(5), rtol=1e-10, atol=1e-10)
    torch.testing.assert_close(gk, delta[:,None]*q.detach()[None,:]/math.sqrt(5), rtol=1e-10, atol=1e-10)
    names.append("Pointer的Query/Key局部反向传播公式")
    return names, str(torch.__version__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-autograd", action="store_true", help="缺少torch时失败而不是跳过自动求导核验")
    parser.add_argument("--report", type=Path, help="保存本次数学核验的JSON报告")
    args = parser.parse_args()
    fixture_path = Path(__file__).resolve().with_name("a-path-acceptance-cases.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    checks = standard_checks(fixture)
    skipped: list[str] = []
    torch_version = None
    if importlib.util.find_spec("torch") is None:
        if args.require_autograd:
            raise RuntimeError("要求自动求导核验，但当前解释器没有安装torch")
        skipped.append("torch自动求导核验：未安装torch")
    else:
        extra, torch_version = autograd_checks()
        checks.extend(extra)
    result = {
        "scope": "standalone_a_path_math_only",
        "project_integration_tested": False,
        "game_environment_tested": False,
        "gpu_training_tested": False,
        "python_version": platform.python_version(),
        "torch_version": torch_version,
        "passed_count": len(checks),
        "passed_checks": checks,
        "skipped_checks": skipped,
        "status": "passed" if not skipped else "passed_with_explicit_skips",
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output+"\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
