# Reward and potion revision: initial audit

Date: 2026-09-18
Status: initial audit retained for provenance; the owner subsequently approved the proposed coefficients and terminal settlement in I8. See ../reward-potion-v2-report.md for implementation evidence.
Branch: codex/reward-potion-v2, based on 3a56708. The main checkout's uncommitted I7 documentation remains untouched.

## Approved objective

Use R = B * I(victory) + alpha * (HP_end - HP_start) / max_HP_start - lambda * potion_uses. Allow healing gains and charge potion use on both victory and defeat. Preserve historical battle_reward_v1 and introduce an explicit new version; do not relabel old results. No training, pool expansion, dataset acquisition, or relic expansion is started here.

## Current source findings

- sts/env/a-path-training-pool.json: starting maximum HP is 75; full-basic starts at 75 HP with no potions, wounded-equipped at 45 HP with Block Potion and Weak Potion. Slots alone are not a general bound on use count after future potion-generation support.
- sts/env/full_card_public.py, PublicBattleEnv._decode_result: reward is checked against [0, 1.5], nonterminal reward must be zero, and outcome is inferred from positive reward. A new reward must use explicit backend outcome, not reward sign.
- sts/train/apath.py, APathTrainer.collect: potion usage is counted from successful normal actions numbered at least 51. This is a diagnostic action count, not a general acquisition/consumption ledger. Selection continuation, invalid actions, and automatic consumption require explicit coverage where supported.
- patches/lightspeed-enemy-potion.patch, executeDecision: the existing victory path applies Burning Blood healing before computing reward and exports outcome, player HP, maximum HP, and exit effects. The new endpoint should preserve this settlement boundary unless the owner changes it.
- third_party/sts_lightspeed/src/combat/BattleContext.cpp: Feed can increase maximum HP. The no-cards/no-damage check can produce PLAYER_LOSS while the player still has HP. Therefore neither a universal normalized-HP upper bound of one nor zero HP for every loss is established.
- sts/train/apath.py, fingerprint: reward configuration and any new reward implementation must be added to checkpoint identity. Existing recovery checks must not be weakened.

These are source-inspection findings, not new runtime or learning evidence. The ignored backend source is a local implementation reference; no proprietary source is copied into this report.

## Candidate for review

Start the numerical discussion with B=2, alpha=1, lambda=0.05. This is a candidate, not an activated default or a certified bound. At starting max HP 75, one potion costs the same reward as 3.75 HP. At unchanged victory probability, using one potion is favorable if it saves more than 3.75 net HP. If other terms are fixed, a 2.5 percentage-point improvement in victory probability offsets one potion cost. Neither statement establishes long-run potion value.

Examples (end HP includes accepted exit effects): 45->45 victory/no potion: 2; 45->30 victory/no potion: 1.8; 45->40 victory/one potion: 1.883333; 45->0 defeat/no potion: -0.6; 45->0 defeat/one potion: -0.65.

For a verified domain with normalized HP delta in [L,U] and potion uses in [0,K], nonnegative alpha and lambda, B > alpha*(U-L) + lambda*K is sufficient to separate every victory from every failure. The domain bounds must be proven for admitted scenes, including maximum-HP growth and non-death failures. Do not apply a bound from today's pool to future relic/potion expansion.

## Proposed settlement, pending review

Keep zero intermediate reward and pay the complete formula once at genuine termination, including actual HP change and potion cost on failure. Capture starting HP/max HP from the declared pre-combat entry state; use end HP after supported exit effects. External truncations are incomplete episodes, receive no fabricated terminal outcome, and bootstrap from the actual final observation. Accumulated entry state and potion events must survive active-environment replay. A later decision to distribute costs across steps changes value targets and requires explicit documentation even at gamma=1.

## Implementation and acceptance after review

Register the owner-approved contract before amending spec-v6. Implement explicit outcome handling, auditable initial/final HP and potion events, new reward metadata and fingerprinting, and trainer/evaluation/recovery compatibility. Test equal damage at different starting HP, healing, maximum-HP growth, winning potion use, losing potion use, illegal actions, terminal single payment, external truncation, reset, and replay. Run small real environment checks without launching training. Report separately what is implemented, tested, runtime-validated, and still awaiting calibration or owner decisions.
