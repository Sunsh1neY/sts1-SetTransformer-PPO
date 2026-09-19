# TensorBoard monitoring plan v1

One event writer, one run directory, one local web page. All scalar x-axes use training environment transitions; evaluation does not advance that counter. Training metrics describe each completed rollout or its completed episodes; dev metrics describe the fixed 288-case evaluation and must not be read as the same sampling distribution.

| Namespace | Contents | Frequency |
|---|---|---|
| `train/ppo/` | Policy/value loss, entropy, approximate KL, clip fraction, LR, gradient norm | Every 1,024 transitions |
| `train/episodes/` | Completed episodes, win rate, terminal reward, exit HP, potion use, truncations | Each rollout; missing means no applicable episodes |
| `train/sampling/` | Natural/augmentation reset counts and proportions; transition proportions | Every rollout |
| `train/groups/` | Natural/augmentation PPO diagnostics and episode results | Every rollout |
| `dev/overall/` | Component-macro reward, win rate, exit HP, potion use, truncation rate | Initialization and updates 64/128/192/256 |
| `dev/strata/` | Natural/augmentation, Act, entry HP, encounter, augmentation family | Same fixed evaluations |
| `system/` | Phase, training steps, eval progress, elapsed time, collection/update timing, CUDA memory | Phase changes and rollout/eval progress |
| `holdout/` | Final paired initial/selected comparison and component-bootstrap interval | Only after checkpoint selection |

No fabricated zeros for missing scores. A truncated evaluation cannot produce the complete terminal-reward selection metric. The Text tab contains the protocol/configuration. Raw JSONL episodes and atomic status.json remain the primary audit trail. Flush events every few seconds. Bind TensorBoard to 127.0.0.1 only; keep the server available after the run for inspection.
