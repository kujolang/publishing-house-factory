# Security model

This is a local, single-user factory for a trusted installation. It is not a multi-tenant service or a sandbox for arbitrary programs.

Source documents and briefs are untrusted data. The model runs in a temporary directory with a private Codex configuration home, read-only sandbox, shell/apps/browser tools disabled and web search disabled. The runner supplies canonical role contracts, validates structured responses and rejects tool-use events. Only trusted repository code writes artifacts or invokes allowlisted Kujo tools. No model-authored code or command is executed. Workcell is unnecessary for this route because workers cannot submit executable work; adding code execution would require a separate isolation design and tests.

Source files must be regular UTF-8 files inside the brief directory, with no symlink components. Intake limits file count and size. Sources are copied and hashed before model calls. Source URLs are provenance only; the factory does not fetch them. Do not supply confidential material unless your model provider and account are approved to receive it. Prompt injection can still distort prose or judgments; deterministic validation and human review limit consequences but cannot guarantee editorial truth.

Model proposals have bounded schemas. Claim support must match preserved text, and documents may cite only known claims. The HTML compiler escapes all supplied text. The read-only viewer binds to localhost, checks Host headers, serves only allowlisted run artifacts and has no mutation endpoints. It does not serve the provider home. Anyone who can access the OS account or change trusted repository files can bypass these local controls.

Authentication lives in `.runtime/provider/`, with a private directory and restricted auth file. The provider process receives a small environment and no publication credentials. Sources, prompts and proposals remain in ignored local runs. Review them before sharing any evidence export.

The adapter rejects publication and post-publication phases, even if an operator approval reference is inserted. VersionSeal records a request only. There is no CMS, newsletter, social or Git delivery adapter. PressWire is installed for canonical operator compatibility but is not invoked for effects. A future delivery route must verify the full package, exact human authority and actual destination; never treat the operator's routing reference as authority on its own.

Report vulnerabilities privately through the repository owner's GitHub contact. Do not put credentials or unpublished source text in a public issue.
