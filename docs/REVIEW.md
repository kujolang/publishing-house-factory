# Review and recovery

A successful local campaign ends at the canonical operator's `approval_required` state. The package says `AWAITING_HUMAN_REVIEW`. These are the same boundary: model checks passed, but a human has not approved publication.

Review the article, every adaptation, the source packet, claim mapping and BluePencil findings. Check meaning, factual support, attribution, rights, voice and suitability for the intended audience. Exact excerpts and file hashes cannot make those judgments for you.

Run `npm run factory -- verify RUN_ID` before reviewing or exporting a package. The manifest binds sources, proposals, prior phase evidence and outputs. Changing or deleting any listed file fails verification. GalleyPack also checks its bound artifacts. The VersionSeal request binds the manifest checksum but grants no authority.

The shipped CLI has no approval or publication command. The adapter also rejects publication phases when called directly. Keep that boundary until a specific destination adapter has been configured and tested. Approval must cover the complete current package, intended destination and action. Changed bytes need new review and new authority.

## Recovery

| Situation | Action |
| --- | --- |
| Missing source | Fix the brief before starting. No provider call is needed. |
| Provider timeout or unavailable model | Check login/model access, then resume the run. |
| Operator process interrupted | Confirm it is stopped; inspect the lease before removing a stale lock, then resume. |
| Primary review requests changes | The adapter allows two writer revisions and reviews each version independently. |
| Review still blocks | Inspect the findings, improve the source packet or brief, and start a new run. |
| Adaptation review requests changes | The adapter allows two revisions and retains each version and review. If changes remain, improve the brief and start a new run. |
| Source or output hash changes | Preserve the evidence and start a new run. Do not rewrite an old checksum. |
| Canonical tool committed just before a crash | A repeated immutable ID may block if its factory receipt was not written. Inspect the tool's real record; preserve the run rather than forcing an overwrite. |

Local leases protect cooperating processes on one filesystem. This is not distributed scheduling or authenticated multi-user approval. The included tests distinguish synthetic model proposals from live account-backed calls.
