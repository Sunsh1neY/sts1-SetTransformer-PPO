"""验证工具的回归：坏进程、缺失证据和同类实体不能被误报为通过。"""

from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import diff_harness
import runlogger_replay


@pytest.fixture
def snapshots():
    model = {
        "player": {"hp": 69, "hp_max": 80, "energy": 2, "block": 5, "buffs": {}},
        "monsters": [
            {"idx": i, "id": "JAW_WORM", "hp": hp, "hp_max": 44,
             "block": 0, "buffs": {}, "intent": "JAW_WORM_CHOMP"}
            for i, hp in enumerate((30, 40))
        ],
        "piles": {"hand": ["strike"], "drawPile": [], "discardPile": ["defend"]},
        "rng": {"ai": 2, "shuffle": 1, "misc": 0, "monster_hp": 2,
                "card_random": 0, "potion": 0},
    }
    logged = {
        "hp_current": 69, "hp_max": 80,
        "combat_state": {
            "player": {"energy": 2},
            "monsters": [
                {"id": "JawWorm", "hp_current": hp, "hp_max": 44, "intent": "ATTACK"}
                for hp in (30, 40)
            ],
            "hand": ["打击"], "draw_pile": [], "discard_pile": ["防御"],
        },
        "seeds": dict(model["rng"]),
    }
    return model, logged


def test_日志缺失状态保留未验证_不按零比较(snapshots):
    model, logged = snapshots
    unverified = set()
    assert runlogger_replay.compare_snapshot(model, logged, unverified) == []
    assert unverified == {
        "player.block", "player.buffs", "monster[0].block", "monster[0].buffs",
        "monster[1].block", "monster[1].buffs",
    }


def test_玩家血量差异必须报告(snapshots):
    model, logged = snapshots
    model["player"]["hp"] -= 1
    assert any("player.hp:" in item for item in runlogger_replay.compare_snapshot(model, logged))


def test_同类敌人第一只差异不能被覆盖(snapshots):
    model, logged = snapshots
    model["monsters"][0]["hp"] -= 1
    assert any("monster[0].hp:" in item for item in runlogger_replay.compare_snapshot(model, logged))


def test_同类敌人数量差异必须报告(snapshots):
    model, logged = snapshots
    model["monsters"].pop(0)
    assert any("怪物数" in item for item in runlogger_replay.compare_snapshot(model, logged))


def test_实际记录的格挡和状态必须比较(snapshots):
    model, logged = snapshots
    logged["combat_state"]["player"].update(block=2, buffs={"WEAK": 2})
    logged["combat_state"]["monsters"][0].update(block=3, buffs={"VULNERABLE": 1})
    diffs = runlogger_replay.compare_snapshot(model, logged)
    for field in ("player.block", "player.buffs", "monster[0].block", "monster[0].buffs"):
        assert any(field in item for item in diffs)


@pytest.mark.parametrize("runner", [lambda: diff_harness.probe_run(100000),
                                    lambda: diff_harness.run_stream("quit\n")])
def test_子进程非零退出必须报告退出码(monkeypatch, runner):
    failed = subprocess.CompletedProcess([], 3221225781, b"", b"")
    monkeypatch.setattr(diff_harness.subprocess, "run", lambda *args, **kwargs: failed)
    with pytest.raises(RuntimeError, match="3221225781.*DLL"):
        runner()


def test_探针子进程包含已有运行时目录(monkeypatch):
    def fake_run(*args, **kwargs):
        assert kwargs["env"]["PATH"].startswith(diff_harness.BUILD_DIR)
        return subprocess.CompletedProcess([], 0, b"NO_BATTLE", b"")
    monkeypatch.setattr(diff_harness.subprocess, "run", fake_run)
    assert diff_harness.check_seed(100000, verbose=False) == "skip"


def test_解析失败不能当作范围外跳过(monkeypatch):
    monkeypatch.setattr(diff_harness, "probe_run", lambda seed: "")
    assert diff_harness.check_seed(100000, verbose=False) == "fail"


@pytest.mark.parametrize("outcomes, exit_code", [
    (["pass", "skip"], 0), (["skip", "skip"], 1), (["pass", "fail"], 1),
])
def test_差分退出状态区分失败和跳过(monkeypatch, outcomes, exit_code):
    results = iter(outcomes)
    monkeypatch.setattr(diff_harness, "check_seed", lambda seed: next(results))
    assert diff_harness.main(["100000", "2"]) == exit_code


def test_缺少终局快照不能计入一致(monkeypatch):
    run = {"seed_ui": "1", "class": "IRONCLAD", "ascension": 0,
           "events": [{"_type": "action:end_turn", "_order": 1}], "floors": []}
    monkeypatch.setattr(runlogger_replay, "run_stream", lambda commands: "<< end\n")
    stats = runlogger_replay.replay_log(run, verbose=False)
    assert stats["pass"] == 0 and stats["skip"] == 1
    assert any("终局或截断处未验证" in issue for issue in stats["issues"])


def test_日志零可比较样本返回失败(monkeypatch):
    monkeypatch.setattr(runlogger_replay, "replay_file", lambda path: {
        "lightspeed": {"pass": 0, "diff": 0, "skip": 1}, "ours": None,
    })
    assert runlogger_replay.main(["unused.run.log"]) == 1
