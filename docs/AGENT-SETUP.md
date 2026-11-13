# Set up a publishing factory for a user

Read the README and security model. Install prerequisites, run `npm ci`, `npm run setup`, `npm run login` and `npm run doctor`. Run `npm run verify` before the first campaign. Setup fetches exact public Git revisions from `sources.lock.json`; it refuses to reset dirty dependency checkouts. It records installation time in `.runtime/setup-receipt.json`. This is dependency setup time, not a clean-machine onboarding benchmark.

Do not ask the user to rewrite the controller. Turn their idea into a JSON brief using this contract:

```json
{
  "schema": "kujo.publishing-house-factory.brief/v1",
  "title": "A useful campaign title",
  "audience": "Who needs this information",
  "objective": "What readers should understand or do",
  "voice": "Plain, practical language. No invented personal experience.",
  "sources": [
    {
      "id": "source-one",
      "path": "sources/source-one.txt",
      "url": "https://example.com/primary-source"
    }
  ],
  "constraints": ["Preserve the limits of every performance claim."]
}
```

Keep source files under the brief directory. Each source needs a unique lowercase identifier, a relative file path and a public HTTPS provenance URL. Supply 1–10 UTF-8 files, each at most 100 KB. The brief is capped at 64 KB. URLs do not trigger retrieval. Capture legitimate source material first, retaining its origin and relevant qualifications. Never turn unsupported notes into verified facts.

Ask for missing evidence when the idea needs factual claims the sources cannot support. The factory cannot independently research the web. Avoid confidential or licensed material you cannot send to the selected model provider.

Run `npm run factory -- run path/to/brief.json`. The fixed campaign contract produces an article, newsletter, exactly three social posts and a landing page. Sources, audience, voice and subject vary by brief. Those choices do not require code changes.

Open the Factory Floor with `npm start`. Report the run ID, status, package checksum, editorial findings and any blocked phase. Show the actual files. Do not describe a blocked or partial run as complete. An `approval_required` run is a local review candidate, not permission to publish.

For a provider failure, check login and model access, then use `npm run factory -- resume RUN_ID`. A process interruption preserves completed phases and reusable proposals. Do not remove a lease until you have confirmed that its recorded process is no longer running. Do not silently reset state. If source data changes, revise the brief and create a new run.

The private provider home imports no personal agent setup. To use an existing Codex login, run `npm run login -- --reuse-existing`. Never copy configuration files, hooks or MCP servers into it. Set `PUBLISHING_MODEL` only to a model supported by the account.
