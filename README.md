# Entity-Centric Reinforcement Learning for STS1 Combat

A first research project for understanding Transformers through implementation and experiments in **Slay the Spire 1** Ironclad combat.

**Current question:** Within a fixed, validated combat distribution, does the current Set Transformer + PPO policy improve over its own untrained initialization?

The immediate goal is a clear, inspectable research starting point. Establishing Set superiority over MLP, implementing full runs, and completing Decision Transformer are not prerequisites for this stage.

## Start here

1. [Research overview](docs/research-overview.md): question, method, evidence, and limitations.
2. [Documentation map](docs/README.md): current references, pending work, and historical material.
3. [Setup and validation](docs/setup.md): existing build and check commands, with reproduction limits.
4. [Next steps](docs/plans/README.md): relics and broader Act 1/2 combat fidelity after this cleanup.

The active specification remains [spec-v6.md](spec-v6.md), read with its dated amendments and the [decision log](docs/decisions.md). Its early progress tables are historical snapshots. New entry documents are English; existing detailed Chinese specifications and evidence remain valid during gradual migration. The local folder name `sts2` is historical; this project studies **STS1**.

## Current implementation and scope

The **A path** is the main development path, integrated into local `main` at `de951cd`. It uses four SAB layers, width 64, four attention heads, FF128, and single-seed PMA. The policy first chooses a source or special action, then a legal conditional target. One complete action uses joint log probability, one PPO ratio, and exact joint entropy.

```text
scripts/run-a-path-ppo.py
  -> sts/train/apath.py       APathTrainer: rollout, GAE, joint PPO
  -> sts/env/apath.py         APathEnv: registered training scenes
  -> sts/env/ironclad.py      IroncladEnv -> full-card C++ backend
  -> sts/models/apath.py     encoding, batching, APathActorCritic
  -> complete action route -> one environment step
```

[Agent](sts/agents/apath.py) and [integration evidence](docs/a-path-main-integration-report.md) provide the entry points for deeper inspection. Legacy Unified/Comparison/MLP modules remain for historical experiments and compatibility; they are not the default A-path training route.

| Boundary | Current scope |
|---|---|
| Registered A-path training pool | 39 deck contents, 33 source groups, two conditions, five encounters: 390 initial configurations |
| Sampling | Uniform source group, then group member, condition and encounter; independent environment seed; global rollout shuffle for PPO |
| Broader diagnostic environment | 75 Ironclad card classes / 150 versions, 44 Act 1/2 encounters, plus MAW and TRANSIENT |
| Admission | Broad `IroncladEnv` access is diagnostic; only the registered A-path pool is admitted for current training |
| Not established | Complete original-game equivalence, unrestricted relic support, full-run play, or generalization across the broader environment |

The integration report records 1,379 CPU tests, a separate C++ fixture, CUDA update/recovery verification, and 390 reset/forward/action/next-observation checks. These are **historical engineering results**, not freshly rerun checks or proof of learning. The archived A-path run has been located; its status record reports completion within limits, but result recomputation and checkpoint recovery remain separate work. See the [inventory](docs/repository-inventory.md).

## Earlier comparison

The frozen MLP/Set study used 27 deck configurations, five encounters and two initializations per model, with 70,656 transitions per run. The report records improvement over each policy's initialization; Set-minus-MLP intervals include zero. This limited study does not establish an architecture advantage or equivalence. Parameter counts differ and some deck contents overlap across training/development. [Original report](docs/comparison-ppo-report.md).

## Fixed experimental rules

- `battle_reward_v1`: zero nonterminal reward; first victory earns `1 + 0.5 * exit_hp / max_hp`; genuine defeat earns zero; gamma is 1 and beta is 0. This is not a lexicographic win-rate-first objective.
- True termination does not bootstrap. External truncation bootstraps from the final pre-reset observation; GAE does not cross resets. Truncations and errors are not fabricated defeats.
- Legal actions come from the environment. Public semantic inputs exclude seeds, hidden draw order, and routing slot identities.
- `eval_seeds.json` remains immutable. Evaluation seeds are in `[0, 1000)` and training environment seeds are at least `100000`.
- New training requires an explicit scope and budget. The historical four-hour allowance does not restart during documentation cleanup.

## Archives and reproducibility

[archive/](archive/README.md) holds tracked historical documents. Root-level v4/v5 specifications are now archived and legacy snapshot tools read those explicit archive paths. Some supporting historical documents remain at stable paths; the documentation map identifies these exceptions.

`runs/`, checkpoints, `third_party/`, and most of `reference/` are ignored by Git. A clone does not contain the local experiments or backend binaries. The existing desktop archive stays in place; [recovery instructions](docs/desktop-repo-cleanup-2026-09-14.md) preserve its original contract boundaries. A clean-clone evaluation/report reproduction package is **not yet verified**. This cleanup neither launches training nor publishes artifacts.
