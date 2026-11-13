# Build launch-video candidates your team can inspect

Small software teams can use VideoOps Factory to move from a sourced campaign brief and registered assets to landscape or portrait video candidates without losing sight of how the work was produced. The repository describes a local workflow that builds an editable HyperFrames project, records elapsed time, and presents evidence in a local Factory Floor. The result is meant for inspection, not automatic approval. [local-inspectable-candidate-workflow]

VideoOps Factory is a standalone, local, early release, not a universal workflow engine. Its model calls are sequential and tool-free. According to the repository, they cannot edit the renderer or execute instructions embedded in a brief, while the viewer displays actual run records rather than simulating approval. The current contract is deliberately narrow: screenshot-led, monochrome launch clips with three to five scenes, a Kujo bumper, 30fps, and silent output lasting 3–60 seconds. Footage timelines, other editing styles, and automatic narrated campaigns require an explicit extension. [early-release-product-status, sequential-tool-free-model-proposals, first-release-supported-output-scope]

To try the example, you need macOS or Linux, Git, Node 26.12.1 or a later 26.x release, Python 3.10 or later, FFmpeg/ffprobe 6 or later with libx264/AAC, and a Codex account. Minimal Ubuntu also needs libatomic1. Native Windows is unsupported, so Windows users need a compatible Linux environment. [setup-platforms-and-prerequisites]

Clone and start the project with the documented sequence:

git clone https://github.com/kujolang/videoops-factory.git
cd videoops-factory
npm ci
npm run setup
npm run login
npm run doctor
npm run verify
npm start

Then open http://127.0.0.1:4381. These instructions may download dependencies and a browser; they were captured from the README but were not independently executed for this article. [repository-and-setup-command-sequence, local-viewer-address]

In another terminal, run either documented example:

npm run factory -- run examples/launch-brief.json
npm run factory -- run examples/social-brief.json

Each command creates a separate, fresh run. The documented example campaign produces two intentionally silent, 12-second candidates: one at 1920×1080 and one at 1080×1920. Model calls use your Codex account, and this example route performs no paid media generation; that does not imply Codex access is free or that every extension avoids paid generation. [example-run-commands, example-output-and-provider-cost-scope]

The available setup timings are limited to two observations in one tested Linux environment. The fresh Ubuntu trials reached verified readiness in 4m 49.765s and 5m 27.524s. With system prerequisites already installed, clone-to-readiness took 3m 21.327s and 3m 06.326s. Codex sign-in was additional. The trials ran on one busy, resource-limited host, so the results are not a general performance promise. Other applications and limited memory were owner-reported; CPU contention, memory pressure, and swapping were not recorded, and their effects are unknown. Fresh macOS and Windows installation times were not measured. [fresh-ubuntu-readiness-timings, prerequisites-installed-timings, timing-signin-and-platform-exclusions, busy-host-unmeasured-contention]

A successful run stops at REVIEW_INCOMPLETE and supplies output/draft.mp4 with metadata, frames, checks, proposals, and handoffs. Rendering and technical checks cannot establish that the candidate looks or sounds right. A capable reviewer must inspect the exact file before promotion, and any edit creates a new candidate that needs a new review. [successful-run-review-status, edits-require-new-review, verification-command-scope]
