# Special relic review queue

Date: 2026-09-19. Historical proposal queue. Owner decisions in [the consolidated decision record](relic-import-decisions-2026-09-19.md) and I11 supersede the pending statuses below. None of these proposals grants training admission.

The full audit identified 24 Act 1/2 candidates requiring review before their implementation. Ordinary second-batch work proceeds independently. Each proposal still needs a concrete per-relic schema/test patch plan when selected; approval of a category must not be interpreted as approval of arbitrary hidden fields or fallback actions.

| Group / relics | Proposed direction | Owner decision required |
|---|---|---|
| Bottled Flame, Bottled Lightning, Bottled Tornado | Preserve exact master-card instance binding; resolve a relation without embedding slot numbers | Approve relation representation and required source/initialization fields |
| Gambling Chip, Nilry's Codex, Toolbox | Environment-supplied legal choices with explicit decline/finish semantics and continuation | Approve selection/action grammar and generated-card scope |
| Frozen Eye, Runic Dome | Version the actual information available to the policy | Approve observable draw order / masked enemy-intent contract; do not simulate by leaving old information accessible |
| Potion Belt | Explicit capacity and action routing extension | Approve supported capacity, masks, slot mapping and recovery version |
| Prismatic Shard | Separate non-Ironclad card/orb scope | Approve whether to expand that scope or keep such scenes unadmitted |
| Dead Branch, Enchiridion | Verified generation pool and complete resulting card/selection closure | Approve generation scope; no silent substitution or dropping generated cards |
| Necronomicon | Explicit used_this_turn and existing replay context; preserve curse effect | Approve replay/state/deck prerequisites |
| Lizard Tail | Persistent spent state and lethal interception before true termination | Approve resurrection lifecycle and reward/potion interaction tests |
| Sacred Bark | Validate every supported potion branch, including future automatic-use cases | Approve potion-mechanism coverage; identity alone does not certify all potion effects |
| Strange Spoon | Correct exhaust replacement and declared RNG stream | Approve automatic-play/exhaust scope and restoration requirements |
| Unceasing Top | Expose only necessary public suppression state; preserve draw/selection queues | Approve decision-boundary and generated-action closure |
| Snecko Eye | Explicit cost randomization and public cost semantics | Approve draw/cost/history scope and recovery tests |
| Runic Pyramid | Correct retained-hand lifecycle and full hand-capacity handling | Approve retention/capacity contract and resource bounds |
| Velvet Choker | Count actual played cards; mask only true legal player actions | Approve automatic/repeated-play counting and action-rule contract |
| Blue Candle, Medical Kit | Environment-owned curse/status play legality and exhaust/HP effects | Approve newly playable card closure |
| Mutagenic Strength | Resolve acquisition-order interaction with Artifact before encoding | Approve the public ordering representation if required by the verified mechanism |
| Orange Pellets | Small attack/skill/power progress state plus verified debuff-removal scope | Approve event-type fields and scope; no generic untyped counter |

These are code-interface decisions, not proposals to change the game's rules. A proposed representation must follow original evidence. Until the owner reviews the relevant design, scenes requiring an unsupported item are rejected intact; ownership is never silently removed.
