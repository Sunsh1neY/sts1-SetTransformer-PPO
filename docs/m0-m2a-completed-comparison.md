# M0 versus completed M2a: selected dev checkpoints

Both selected models are update256 at262144 transitions. M2a's original run
stopped at229; a separately authorized continuation completed the remaining27.
This comparison uses the dev-selected models, not the old M2a update192 holdout.

| Component-macro metric | M0 | M2a | M2a minus M0 |
|---|---:|---:|---:|
| Reward | 1.41969534 | 1.42618863 | +0.00649329 |
| Win rate | 83.3899156% | 83.3405761% | -0.0493395 pp |
| Exit HP ratio including defeats | 0.50590883 | 0.51338891 | +0.00748008 |

Case keys, environment seed, policy seed and component labels match across288
dev states and13 components. Raw wins are225 versus223:210 both win,15 M0-only,
13 M2a-only and50 both lose. Component weighting explains the difference between
raw case counts and macro rates.

Direct paired component bootstrap (10000 resamples, seed190919) gives95%
intervals of[-0.0976484,+0.1086288] for reward and[-4.33863,+4.24359] percentage
points for win-rate difference. The calculation first averages paired state
differences within component, then samples components equally. It does not
measure variation across independent training initializations; these are also
selection-set outcomes, not untouched test evidence.

Conclusion: a tiny reward point-estimate improvement, no reliable overall M2a
improvement established under the fixed interaction budget. Do not claim
equivalence or infer that the added context cannot help. Holdout for M2a@256 has
not been run; M2a@192's old holdout must not be substituted.

Sources: runs/a-v2-ppo-v1/dev-0256-episodes.jsonl and
runs/m2a-source-context-continuation-v2/dev-0256-episodes.jsonl; their summaries,
run status and original checkpoint-selection rules. Analysis date:2026-09-22.
