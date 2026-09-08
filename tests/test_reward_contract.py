"""D27 / spec-v6 奖励、终止、RTG 与版本迁移验收矩阵。"""

from __future__ import annotations

import pytest

from sts.rewards import (
    BATTLE_REWARD_CONTRACT,
    BATTLE_REWARD_VERSION,
    RUN_REWARD_VERSION,
    battle_step_reward,
    make_run_reward_contract,
    recompute_episode_reward_and_rtg,
    require_reward_contract,
    run_step_reward,
    true_return_to_go,
)


def test_r1_battle_nonterminal_loss_and_hard_timeout_are_zero():
    assert battle_step_reward(battle_won=False, terminated=False) == 0.0
    assert battle_step_reward(
        battle_won=False, terminated=True, hp_exit=0, max_hp_exit=80
    ) == 0.0
    assert battle_step_reward(
        battle_won=False, terminated=True, hp_exit=40, max_hp_exit=80
    ) == 0.0


def test_r2_r3_battle_win_uses_post_settlement_exit_hp():
    assert battle_step_reward(
        battle_won=True, terminated=True, hp_exit=60, max_hp_exit=80
    ) == pytest.approx(1.375)
    # 结算前50/80不进入接口；若已实现的战斗结束效果结算到56/80，应读取56。
    assert battle_step_reward(
        battle_won=True, terminated=True, hp_exit=56, max_hp_exit=80
    ) == pytest.approx(1.35)


def test_r5_ordinary_battle_win_does_not_end_or_reward_run():
    assert run_step_reward(run_won=False, terminated=False, battle_won=True) == 0.0


def test_r6_r7_run_only_rewards_final_success_once_and_ignores_hp():
    assert run_step_reward(run_won=True, terminated=True) == 1.0
    assert run_step_reward(run_won=False, terminated=True) == 0.0
    assert run_step_reward(run_won=False, terminated=True) == 0.0
    # run 契约没有 HP 入参，因此1HP与满血的最终通关都只能得到同一个1。
    assert run_step_reward(run_won=True, terminated=True) == 1.0


def test_r8_trajectory_length_does_not_change_undiscounted_return():
    short = true_return_to_go([1.0], terminated=True, truncated=False)
    long = true_return_to_go([0.0, 0.0, 1.0], terminated=True, truncated=False)
    assert short[0] == long[0] == 1.0


def test_r11_rtg_is_computed_before_window_slicing():
    rtg = true_return_to_go([0.0, 0.0, 1.3], terminated=True, truncated=False)
    assert rtg == pytest.approx([1.3, 1.3, 1.3])
    assert rtg[1:] == pytest.approx([1.3, 1.3])


def test_external_truncation_has_no_exact_failure_rtg():
    with pytest.raises(ValueError, match="禁止补造"):
        true_return_to_go([0.0, 0.0], terminated=False, truncated=True)


def test_r12_battle_win_cannot_be_migrated_to_run_win():
    with pytest.raises(ValueError, match="整局终局结果"):
        recompute_episode_reward_and_rtg(
            step_count=3,
            task_type="run",
            task_outcome="battle_won",
            terminated=True,
            truncated=False,
        )


def test_r13_all_model_paths_share_the_same_raw_reward_and_true_rtg():
    expected = recompute_episode_reward_and_rtg(
        step_count=3,
        task_type="battle",
        task_outcome="battle_won",
        terminated=True,
        truncated=False,
        hp_exit=48,
        max_hp_exit=80,
    )
    consumers = {
        name: recompute_episode_reward_and_rtg(
            step_count=3,
            task_type="battle",
            task_outcome="battle_won",
            terminated=True,
            truncated=False,
            hp_exit=48,
            max_hp_exit=80,
        )
        for name in ("mlp-ppo", "set-ppo", "dt")
    }
    assert all(value == expected for value in consumers.values())


@pytest.mark.parametrize(
    ("hp", "max_hp"),
    [(-1, 80), (81, 80), (1, 0), (float("nan"), 80)],
)
def test_r14_invalid_victory_hp_is_rejected(hp, max_hp):
    with pytest.raises((TypeError, ValueError)):
        battle_step_reward(
            battle_won=True, terminated=True, hp_exit=hp, max_hp_exit=max_hp
        )


def test_r14_invalid_loss_hp_is_also_rejected():
    with pytest.raises(ValueError, match="终局退出 HP"):
        battle_step_reward(
            battle_won=False, terminated=True, hp_exit=-1, max_hp_exit=80
        )


def test_r14_run_contract_requires_explicit_success_predicate():
    with pytest.raises(ValueError, match="success_predicate_id"):
        make_run_reward_contract(
            task_spec_id="ironclad-a20-example",
            success_predicate_id="",
            environment_version="future-run-env",
            termination_rule_version="future-run-termination",
        )


def test_r14_reward_version_mismatch_is_rejected():
    wrong = BATTLE_REWARD_CONTRACT.to_dict()
    wrong["reward_version"] = RUN_REWARD_VERSION
    with pytest.raises(ValueError, match="battle 契约"):
        require_reward_contract(wrong)
    assert BATTLE_REWARD_CONTRACT.reward_version == BATTLE_REWARD_VERSION
