# Battle initial-state project

This folder holds the small-corpus pilot plan and its audit. It is a project inside the existing repository, not a separate simulator or training system.

Current deliverable: [small-corpus pilot audit](small-corpus-pilot-audit.md), dated 2026-09-19.

The owner selected MaT1g3R/Slay-the-Spire-data for a pipeline pilot before deciding whether to process SlayTheData.7z. This recording pass audits that direction; it does not implement the pipeline or admit training data.

## File ownership

- Keep new project-specific plans, source inventories, compact manifests, rejection ledgers and reports here. Add project-local extraction/validation tools and tests only when implemented.
- Keep shared environment, model, reward and trainer implementations in the existing `sts/` packages. Call those implementations instead of copying them here.
- Reuse the existing ignored `reference/public-run-corpus/` cache by reference. Put future raw sources and bulky generated evidence under ignored `reference/battle-initial-states/`; compact tracked manifests should point to them by repository-relative path and hash.
- Preserve historical documents and artifacts in place. No empty implementation directories have been created.
- Record adopted governing changes in `docs/decisions.md` before changing `spec-v6.md`. This folder does not supersede either file.

The supplied original plan remains untouched in the relic worktree. The audit records its exact path and SHA-256.
