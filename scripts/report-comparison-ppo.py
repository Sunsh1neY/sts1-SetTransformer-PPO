"""从实际四组记录生成训练曲线和中文报告，不替代原始评估数据。"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=Path)
    args = p.parse_args()
    summary = json.loads((args.run_dir / "summary.json").read_text(encoding="utf-8"))
    plan = json.loads((args.run_dir / "plan.json").read_text(encoding="utf-8"))
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    lines = ["# M3 MLP/Set PPO训练与固定环境对照", "", "本报告来自实际运行，工程、学习改善、架构差异分别判定。", "",
             f"运行目录：`{args.run_dir.as_posix()}`。状态：`{summary['status']}`。", "",
             f"正式训练及评估总耗时：{summary['elapsed_seconds']:.2f}秒；预算1800秒。GPU：{plan['gpu']}，PyTorch：{plan['torch_version']}。", "",
             f"每组预算：{plan['iterations_per_run']}轮、{plan['transitions_per_run']}个transition；MLP/Set各2组，8环境×64步，公共PPO参数一致。", "",
             "固定范围为27种中途卡组、两条件、五遭遇、A20；64逐牌位置，57触发容量外部截断。MLP381150参数、Set140222参数。", "",
             "## 实际结果", "", "| 模型/组 | 完成步数 | 初始胜局 | 最终胜局 | 最终截断 | 回报差95%组级区间 | 学习验收 |",
             "|---|---:|---:|---:|---:|---|---|"]
    for result in summary["runs"]:
        label = f"{result['kind']}-{result['group']}"
        folder = args.run_dir / label
        initial = json.loads((folder / "initial-evaluation.json").read_text(encoding="utf-8"))
        final = json.loads((folder / "final-evaluation.json").read_text(encoding="utf-8"))
        metrics = [json.loads(x) for x in (folder / "metrics.jsonl").read_text().splitlines()]
        ci = result["learning"]["cluster_bootstrap_95_bounds"]
        wins = lambda rows: sum(r["reward"] is not None and r["reward"] > 0 for r in rows)
        lines.append(f"| {label} | {result['transitions']} | {wins(initial)}/{len(initial)} | {wins(final)}/{len(final)} | {sum(r['truncated'] for r in final)} | [{ci[0]:.4f}, {ci[1]:.4f}] | {'通过' if result['learning']['improvement_pass'] else '未通过'} |")
        for ax, key in zip(axes.flat, ("mean_return", "value_loss", "entropy", "explained_variance")):
            xs, ys = zip(*[(m["steps"], m[key]) for m in metrics if m[key] is not None])
            ax.plot(xs, ys, label=label, linewidth=1.3, alpha=0.8)
            ax.set_xlabel("环境交互步数")
            ax.set_title({"mean_return": "训练批次自然终局平均回报", "value_loss": "价值损失", "entropy": "策略熵", "explained_variance": "价值解释方差"}[key])
            ax.grid(alpha=0.2)
    lines += ["", "胜局分母包含所有120个冻结开发场景。训练曲线中的平均回报仅包含自然结束的episode；截断另记，不能看曲线就判断收益。", "",
              "差值为最终减初始；先在每个来源run内平均，再按10个run组bootstrap5000次。截断完整回报未知，按[0,1.5]传播到差值区间，不补失败0，不排除困难样本。", "",
              "## Set相对MLP", ""]
    for row in summary.get("architecture_comparison", []):
        ci = row["set_minus_mlp"]["cluster_bootstrap_95_bounds"]
        lines.append(f"- 组{row['group']}：Set−MLP回报差区间 [{ci[0]:.4f}, {ci[1]:.4f}]。")
    lines += ["", "这些区间衡量固定开发来源组的场景差异，不覆盖总体玩家分布或充分的训练随机性。两组初始化均完整保留，不挑最好一次。4种卡组内容跨训练/开发侧，不宣称未见卡组泛化。Set不胜过MLP不等于工程失败。", "",
              "## 验收与证据边界", "",
              "源码快照source.zip、环境/配置指纹、冻结评估清单、initial/final checkpoint、逐轮metrics.jsonl、逐episode记录、TensorBoard和逐场初始/最终评估均保存在运行目录。", "",
              "容量边界、逐牌重复保留、字段遗漏拒绝、Set置换性质、手牌路由、非法动作mask及断点恢复由针对性测试与资源预检验证。训练没有正式Gate身份，学习理解仍需用户独立复述。", "",
              "后续扩展环境只继续Set，MLP留在本冻结范围；不能直接拿扩展Set分数与这里的MLP作架构比较。", ""]
    for ax in axes.flat:
        ax.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(args.run_dir / "training-curves.png", dpi=160)
    target = ROOT / "docs/comparison-ppo-report.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(target)
