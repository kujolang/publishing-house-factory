# An inspectable path to launch-video candidates

VideoOps Factory turns a sourced brief and registered assets into landscape or portrait video candidates while retaining an editable HyperFrames project, elapsed-time records, and local run evidence. Its first-release scope is deliberately narrow: screenshot-led, monochrome, silent clips with three to five scenes, a Kujo bumper, 30fps, and a 3–60-second duration. [local-inspectable-candidate-workflow, early-release-product-status, first-release-supported-output-scope]

This is candidate generation, not autonomous approval. Successful runs end at REVIEW_INCOMPLETE; a capable reviewer must inspect the exact video, and any edit creates a new candidate requiring a new review. [successful-run-review-status, edits-require-new-review]


---

# What setup actually requires

The documented VideoOps Factory example requires macOS or Linux, Git, Node 26.12.1 or later 26.x, Python 3.10+, FFmpeg/ffprobe 6+ with libx264/AAC, and a Codex account. Minimal Ubuntu also needs libatomic1, and native Windows is unsupported.

Use the documented setup sequence:

git clone https://github.com/kujolang/videoops-factory.git
cd videoops-factory
npm ci
npm run setup
npm run login
npm run doctor
npm run verify
npm start

Then open http://127.0.0.1:4381. In another terminal, run either documented example:

npm run factory -- run examples/launch-brief.json
npm run factory -- run examples/social-brief.json [setup-platforms-and-prerequisites, repository-and-setup-command-sequence, local-viewer-address, example-run-commands]

These instructions may download dependencies and a browser. They were captured from the README but were not independently executed for the reviewed article. [repository-and-setup-command-sequence]


---

# Treat the setup timings as observations, not promises

Two fresh-Ubuntu trials reached verified readiness in 4m 49.765s and 5m 27.524s. With system prerequisites already installed, clone-to-readiness took 3m 21.327s and 3m 06.326s. Codex sign-in was additional. [fresh-ubuntu-readiness-timings, prerequisites-installed-timings, timing-signin-and-platform-exclusions]

Those are two observations from one busy, resource-limited Linux host—not a general benchmark. Other applications and limited memory were owner-reported; CPU contention, memory pressure, and swapping were not recorded, so their effects are unknown. Fresh macOS and Windows installation times were not measured. [timing-signin-and-platform-exclusions, busy-host-unmeasured-contention]
