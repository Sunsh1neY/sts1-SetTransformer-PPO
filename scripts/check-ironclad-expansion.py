"""校验全卡进度账与冻结边界；待验收项不能被当作准入。"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check():
    contract = json.loads((ROOT / "sts/env/ironclad-expansion-contract.json").read_text(encoding="utf-8"))
    coverage = json.loads((ROOT / "sts/env/ironclad-expansion-coverage.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "sts/env/ironclad-registry.json").read_text(encoding="utf-8"))
    by_name = {r["name"]: r for r in registry["cards"]}
    assert len(by_name) == len({r["id"] for r in registry["cards"]}) == len(registry["cards"])
    rows = coverage["versions"]
    keys = {(r["name"], r["upgrade_count"]) for r in rows}
    assert len(rows) == len(keys) == 150
    assert len({name for name, _ in keys}) == 75
    assert all((name, up) in keys for name, _ in keys for up in (0, 1))
    assert sum(r["legacy_admitted"] for r in rows) == 69
    expected = {"E2": 24, "E3": 13, "E4": 20, "E5": 12, "E6": 12}
    assert {stage: sum(r["milestone"] == stage for r in rows) for stage in expected} == expected
    for row in rows:
        if row["expanded_admitted"]:
            assert row["name"] in by_name and row["upgrade_count"] <= by_name[row["name"]]["max_upgrade"]
            assert row["evidence"], f"准入缺证据：{row}"
            assert all((ROOT / path).is_file() for path in row["evidence"])
    public = json.loads((ROOT / "sts/env/public-battle-contract.json").read_text(encoding="utf-8"))
    assert all(by_name[r["name"]] == r for r in public["cards"]), "旧项目ID或升级范围被改写"
    for path, expected_hash in contract["frozen_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected_hash, f"冻结文件改变：{path}"
    assert contract["reward_version"] == "battle_reward_v1" and contract["gamma"] == 1
    assert not contract["training_admitted"], "正式扩展训练需另行冻结并更新验收程序"
    return {"target_versions": len(rows), "legacy_admitted": 69,
            "expanded_admitted": sum(r["expanded_admitted"] for r in rows),
            "frozen_files": len(contract["frozen_sha256"])}


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False))
