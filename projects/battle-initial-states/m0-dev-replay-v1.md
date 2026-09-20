# M0 frozen dev diagnostic replay

## Scope and implementation

The owner authorized a standalone frozen-weight dev replay and concrete suspicious-decision investigation. This is not a new PPO experiment, budget renewal, architecture change, or holdout evaluation.

Entry point: `scripts/replay-m0-dev.py`. It imports the model and admitted environment directly, never the trainer or optimizer. It checks all recorded launch fingerprints, loads `selected.pt` strictly at update 256, disables parameter gradients, uses the original CUDA deterministic settings and original dev seeds, and checks model tensors, checkpoint bytes and dependencies again at completion. Existing output directories are rejected. Output must be outside the frozen training run.

Run command (use a new output path):

```powershell
& 'C:/Users/19091/Desktop/sts2/.venv-gpu/Scripts/python.exe' -B scripts/replay-m0-dev.py --backend-root C:/Users/19091/Desktop/sts2/third_party/sts_lightspeed --output C:/Users/19091/Desktop/sts2-initial-states/runs/m0-dev-diagnostic-v3 --max-probes 40
```

The diagnostic cap is 900 seconds by default, with at most 40 probes for this execution. Neither is a training budget. The CLI permits at most 48 probes and 1800 seconds.

## Verified runtime evidence

- 20 purposively selected dev cases: 5 persistent Champ/Guardian failures, 6 low-HP failure children plus their 6 winning parents, and 3 checkpoint-sensitive failures.
- All 20 reproduced historical win, reward, episode length, termination, truncation, potion use and exit-HP ratio. This validates the recorded terminal results, not equality with an unavailable historical action trace.
- Each original replay saves full public observations, model-facing semantic hashes, all legal routes with source/conditional/joint probabilities, sampled actions, value predictions and observed terminal RTG residuals.
- 31 single-action alternatives completed, with 5 winning alternatives across 3 distinct states. Original outcomes for those states were defeats.
- Probe prefixes replay the original policy RNG and verify both semantic observation hashes and sampled routes before the forced step. The original draw is consumed at that step; one alternative is forced; frozen stochastic policy sampling resumes thereafter.
- All frozen dependency and weight checks passed after execution. No training updates, checkpoint writes, or holdout episodes occurred.
- Six diagnostic unit/integration tests passed. The local-artifact selection test skips when the ignored original run is absent.

The probe screen considered the earliest two decisions with alternatives, plus earliest/latest flagged decisions, per losing case. For each selected decision it tested the highest-probability non-END_TURN alternative excluding the sampled route. This is bounded screening, not an exhaustive search or an unbiased action-quality estimate.

## Concrete findings

### Champ: low-probability sampled actions, not simply wrong top-ranked actions

State `14f1fe88b80e82a2bef0d82d3a01f0abdfd330fade50f8b224bb33f6a6329808`:

- Step 1: HP 80/80, energy 3, block 10. Champ has a public DEFEND_BUFF intent and zero displayed attack damage.
- Original sampled Spot Weakness+ has joint probability 0.086141. Reaper has probability 0.745684.
- The next original observation shows energy reduced to 2 and no Strength status gained. This is a directly observed local effect, not a claim that no relic/card-play side effects exist.
- Replacing only this action with Reaper changes the terminal reward from -1.000 to +1.125 and produces victory.
- At step 2 of the original prefix, sampled Defend has probability 0.045414 while Reaper has 0.860246. Replacing that step also produces victory with reward +1.125.

This is evidence for a sampled-policy bad path in this case. The actor already ranks a winning alternative above the sampled action. It does not establish that greedy evaluation is generally superior or justify changing the frozen evaluation policy.

### Slime Boss: a high-probability source/ordering candidate

State `12bb998cdced8ca734998415795c710c2e7fdffeeee207c73a4431eec7b3c9da`, step 2:

- Original Carnage+ probability 0.857820; alternative Pommel Strike+ probability 0.136662.
- Replacing that single action changes defeat/reward -0.690 to victory/reward +1.550.
- Both act on the same sole boss target at this decision. This witness concerns source/ordering, not choosing among enemy targets.

Unlike the Champ example, the winning alternative was lower ranked. Investigate the downstream draw/energy/order trajectory before assigning the cause to a query architecture.

### Hexaghost: ordering sensitivity, not proof of a bad potion

State `2eed621d9475c2af727159e1bb869e0d96db33deff373d524556616c95740a51`:

- Step 1 originally uses SpeedPotion (probability 0.991832); forcing Anger (0.002092) instead yields victory, reward +1.870 versus original -0.463333.
- Both completed trajectories use one potion. Therefore this does not support the claim that using the potion itself is wrong.
- Alternatively, keeping step 1 and replacing step-2 Bash (0.177831) with Anger (0.436999) also yields victory.

These are ordering-sensitive single-seed witnesses. Later policy and simulator RNG consumption can diverge after the intervention; the probes do not hold later hidden events fixed or estimate expected Q-values.

### Low HP: an actionable observation, not yet a winning counterexample

State `285a727401caa289036be6094fc1dc844cf20a646c550a85e3a98d22045ed109`, Shelled Parasite, HP 6/68:

1. Pommel Strike, energy 4 -> 3.
2. Shockwave, energy 3 -> 1.
3. Pommel Strike (probability 0.999456), energy 1 -> 0.
4. END_TURN is the only legal action; block remains zero. The displayed enemy intent is 15 x 1, and the observed episode terminates in defeat.

At the forced END_TURN state V=+0.398301 while the realized terminal reward is -0.088235. This is a concrete residual at an imminent-death state, not a calibrated estimate of systematic critic error. The bounded early-action probes found no winning alternative for this child; neither feasibility nor optimal play has been established.

## What the evidence does not establish

- Only one end-turn-with-legal-alternative flag occurred in these 20 traces; its probe still lost. There is no support here for premature END_TURN as the dominant failure mode.
- Five winning probes are only three distinct states; do not treat them as five independent wins or a success rate on the full dev corpus.
- The subset intentionally oversamples failures. Do not report its mean return or value residual as a dev score/calibration metric.
- Full baseline traces are saved; counterfactual artifacts currently retain intervention details and terminal results, not full counterfactual action traces. They can be reproduced from the script and original prefix.
- Counterfactual wins establish alternative realized trajectories, not globally optimal actions or a guaranteed expected advantage.
- No evidence yet distinguishes an actor query bottleneck from optimization, stochastic sampling, representation, or critic-training effects. M0 remains frozen.

## Artifact navigation and attempt history

- Completed evidence: `runs/m0-dev-diagnostic-v3/manifest.json`, `summary.json`, `probes.json`, and one full-hash JSON trace per case.
- First attempt (`m0-dev-diagnostic-v1`) stopped after encountering NumPy observation serialization; its incomplete summary is retained. Array serialization was corrected and tested.
- The first successful narrow screen (`m0-dev-diagnostic-v2`) reproduced all 20 cases and tested one flagged END_TURN alternative, without a win.
- The final screen (`m0-dev-diagnostic-v3`) added early-choice and rare-sample probes and semantic prefix checks; it completed all 31 available probes. The `v2/v3` suffixes are diagnostic execution attempts, not new model versions.

Next diagnostic priority: save and compare the full winning counterfactual traces and repeat a small prespecified set of these interventions over policy sampling seeds. Keep these as dev-only diagnostic experiments, not a replacement for the frozen official evaluation.
