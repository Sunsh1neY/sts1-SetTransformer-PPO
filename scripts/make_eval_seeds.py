"""生成 eval_seeds.json —— v4 §6.1：第 1 周生成并提交进版本控制，此后不可改动。

种子约定（非随机抽取，完全可审计）：
- 评估种子 = [0, 1000) 全量整数，与"评估 seed < 1000"的隔离规则一致；
- 训练种子必须 >= 100000（训练采样区间与评估互斥）；
- 评估为配对协议（v4 §6.2）：全部策略面对同一批种子的相同初始牌序与敌人。

为什么不用随机抽取：固定规则生成的种子集在任何机器上字节级一致，
不需要"当时用了什么 master seed"的额外记录，审计零成本。

警告：本文件或 eval_seeds.json 的任何字节改动都会改变 sha256，
使全部历史实验结论失去可比性 —— 不要这么做（docs/decisions.md D8）。
"""
import hashlib
import json
from pathlib import Path

N_EVAL_SEEDS = 1000
TRAIN_SEED_FLOOR = 100_000
CREATED = "2026-09-03"  # 固定写入，不用 date.today()：重新生成必须字节级一致


def main() -> None:
    payload = {
        "schema_version": 1,
        "created": CREATED,
        "rule": "seeds = list(range(1000)); fixed by convention, not randomly drawn",
        "n_seeds": N_EVAL_SEEDS,
        "seed_min": 0,
        "seed_max_exclusive": N_EVAL_SEEDS,
        "train_seed_floor": TRAIN_SEED_FLOOR,
        "spec_ref": "spec-v4.md §6.1 种子隔离 / §6.2 配对比较",
        "seeds": list(range(N_EVAL_SEEDS)),
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    out = Path(__file__).resolve().parent.parent / "eval_seeds.json"
    out.write_text(text, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"written: {out}")
    print(f"sha256 : {digest}")


if __name__ == "__main__":
    main()
