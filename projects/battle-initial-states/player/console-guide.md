# Frozen M0 interactive console

Current entry point after consolidation: [tools/battle-console](../../../tools/battle-console/README.md). The old `sts2-initial-states` worktree is retired. Use `C:\Users\19091\Desktop\sts2\tools\battle-console\start.cmd` or main's root `start-m0-console.cmd`. The sections below describing the old worktree path are historical setup evidence, not the current launch location.

## Start and reopen

1. Open `C:\Users\19091\Desktop\sts2-initial-states` in File Explorer.
2. Double-click `start-m0-console.cmd`.
3. Wait for model loading. The launcher opens `http://127.0.0.1:8767/` in the default browser. If the correct service already runs, it reopens it without starting another model process.

Once the service is running, bookmark the URL. After reboot or shutdown, the URL alone cannot start Python: use the launcher again. No terminal command is normally needed. Keep the existing GPU environment and backend at their current paths.

## Operate

- Search by encounter, natural/augmentation, or state hash, select a dev initial state and start/reset.
- Model step executes one sampled joint action. Auto run repeatedly executes actions until paused or terminal.
- Pause stops future requests; an already submitted action may finish first.
- While paused, click a complete legal-action button to intervene. Target names/slots are included in the button; selection decisions appear as their legal choices.
- Return to automatic execution at any point. The model remains frozen; no optimization or learning occurs.
- Manual execution consumes the original model sampling draw before replacing it, matching the diagnostic replay convention. The action log labels human/model actions and the original model proposal.
- Reset uses the same environment seed 0 and policy seed 700000. Repeating it is a reproducibility test, not independent statistical evidence.
- Export downloads the current public state and action log with plain routes. It is not a full per-step observation recording or an importable simulator snapshot.
- Refresh restores the active session paused. All tabs share one session; use one active tab. Revision checks reject stale actions.
- Close the local model service using the page button to release its resources. Closing only the browser leaves the service running. Shutdown loses the in-memory battle; export first if needed.

## Boundaries and troubleshooting

The service binds only to loopback port 8767. It checks host headers and a per-process token for mutations, exposes no arbitrary files, and only admits the 288 fixed dev states. Holdout/training states cannot be reset through this console. Model/backend/corpus launch fingerprints and checkpoint fingerprints are verified at startup. No trainer, optimizer, backward call, checkpoint save, or corpus write is used.

The original offline player remains separate on port 8766. This console does not yet offer undo, branching, custom scenes/seeds, native-game control or multi-seed batch tests.

## Verified checks

Eleven tests passed across the console, diagnostic replay and player suites, including a separate temporary-port live CUDA service. Live checks cover all 288 catalog entries, unauthorized request rejection, non-dev reset rejection, stale revision rejection, manual-to-model handoff, a full model-only episode matching its frozen dev result, and graceful shutdown. Desktop browser checks cover scenario search, manual Reaper intervention, action attribution, automatic execution and terminal controls. Mobile interactions were explicitly excluded from verification at the owner's request.

Launcher logs are in `runs/m0-console-service/`. If launch fails, its window displays the log location and remains open. Do not loosen fingerprint checks if files changed. The service requires the original CUDA environment; it does not silently switch sampling devices.
