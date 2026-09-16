"""检查 v6 章节、当前入口、本地链接与不可变评估种子。"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec-v6.md"
CURRENT_DOCUMENTS = (
    "AGENTS.md",
    "README.md",
    "docs/README.md",
    "docs/research-overview.md",
    "docs/setup.md",
    "docs/repository-inventory.md",
    "docs/document-catalog.md",
    "docs/plans/README.md",
    "docs/decisions.md",
    "docs/learning-path-v2.md",
    "docs/mechanics.md",
    "docs/mlp-smoke-plan.md",
    "docs/observation-contract.md",
    "docs/week-4-plan.md",
    "docs/week-5-6-plan.md",
)


def main() -> int:
    text = SPEC.read_text(encoding="utf-8")
    errors: list[str] = []
    for number in range(13):
        count = len(re.findall(rf"^## {number}\. ", text, re.MULTILINE))
        if count != 1:
            errors.append(f"主章节 {number} 数量错误：{count}")
    for marker in (
        "### 4.4 奖励",
        "#### 4.4.1 完整爬塔 `run_reward_v1`",
        "#### 4.4.2 独立战斗 `battle_reward_v1`",
        "#### 4.4.3 真终止、外部截断与异常",
        "#### 4.4.4 真实 RTG、DT 数据与势能研究边界",
        "#### 4.4.5 数据与版本迁移",
        "### 5.6 v6 奖励验收矩阵",
        "### 7.6 S3 rollout 与 PPO 更新契约",
        "## 附 D：v5 → v6 奖励任务书落点",
    ):
        if marker not in text:
            errors.append(f"缺少章节：{marker}")
    for token in (
        "task_spec_id",
        "success_predicate_id",
        "battle_won",
        "run_won",
        "termination_reason",
        "bootstrap_mask",
        "trace_mask",
        "beta=0",
    ):
        if token not in text:
            errors.append(f"缺少契约词：{token}")
    if text.count("```") % 2:
        errors.append("spec-v6 代码围栏未闭合")
    if "按需一次校准并锁定血量系数" in text:
        errors.append("v6 仍含旧的默认 HP 系数校准授权")
    if "已冻结为历史方案" not in (ROOT / "archive/spec-v5.md").read_text(encoding="utf-8")[:500]:
        errors.append("spec-v5 未标记冻结")
    for name in CURRENT_DOCUMENTS:
        content = (ROOT / name).read_text(encoding="utf-8")
        if "spec-v6" not in content:
            errors.append(f"当前入口未同步 v6：{name}")
    for name in ("spec-v6.md", *CURRENT_DOCUMENTS):
        content = (ROOT / name).read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]\n]+\]\(([^)]+)\)", content):
            if "://" in target or target.startswith("#"):
                continue
            local = target.split("#", 1)[0]
            if not ((ROOT / name).parent / local).exists():
                errors.append(f"失效链接 {name}: {local}")
    expected_hash = "38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c"
    if hashlib.sha256((ROOT / "eval_seeds.json").read_bytes()).hexdigest() != expected_hash:
        errors.append("eval_seeds.json 哈希发生变化")
    print("PASS" if not errors else "FAIL")
    print(f"spec-v6 行数：{len(text.splitlines())}")
    print(f"当前入口文档：{len(CURRENT_DOCUMENTS)}")
    for error in errors:
        print(error)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
