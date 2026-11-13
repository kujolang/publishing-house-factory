# Build launch-video candidates your team can inspect

VideoOps Factory gives small software teams a local, inspectable path from a sourced brief and registered assets to landscape or portrait video candidates. It creates an editable HyperFrames project, records elapsed time, and shows run evidence in a local Factory Floor. It is an early release with a narrow contract: screenshot-led, monochrome, silent clips with three to five scenes, a Kujo bumper, 30fps, and a 3–60-second duration. [local-inspectable-candidate-workflow, early-release-product-status, first-release-supported-output-scope]

Trying it requires macOS or Linux, Git, Node 26.12.1 or later 26.x, Python 3.10+, FFmpeg/ffprobe 6+ with libx264/AAC, and a Codex account. Minimal Ubuntu also needs libatomic1; native Windows is unsupported.

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

The available timing evidence is only two observations on one busy, resource-limited Linux host. Bare-Ubuntu readiness took 4m 49.765s and 5m 27.524s; with prerequisites installed, clone-to-readiness took 3m 21.327s and 3m 06.326s. Sign-in was additional, contention and swapping were not measured, and fresh macOS and Windows times are unknown. The commands and outputs were not independently tested for this article. Most importantly, a successful run ends at REVIEW_INCOMPLETE. A capable reviewer must inspect the exact candidate, and every edit requires a new review. [fresh-ubuntu-readiness-timings, prerequisites-installed-timings, timing-signin-and-platform-exclusions, busy-host-unmeasured-contention, successful-run-review-status, edits-require-new-review]
