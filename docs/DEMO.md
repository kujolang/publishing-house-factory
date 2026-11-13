# Publishing House Factory demo

This 53-second walkthrough shows what a publishing team gets from one sourced brief: an article, a newsletter, three social posts and a landing page. ElevenLabs Siren narrates the actual interface, with a quiet original Kujo music bed and a Kujo K bumper in Departure Mono. There are no added captions or scene labels.

[Download the phone version](media/publishing-house-factory-demo-mobile.mp4) · [Download the 1080p original](media/publishing-house-factory-demo.mp4) · [Editable HyperFrames source](media/publishing-house-demo-source.zip) · [Narration](media/narration.txt) · [Media manifest](media/manifest.json)

## What the video shows

The cut opens with six campaign previews, follows the connected agent stations, shows an actual review correction, and opens finished drafts. The first four scenes record browser interactions with retained evidence from run `20261113-065550-16f495f8`. They are an edited walkthrough of a completed campaign, not a live replay of agents working.

The example campaign explains VideoOps Factory; Publishing House Factory produced it. The first adaptation review requested missing setup instructions. The next version passed model review. Both decisions remain visible in the review desk, alongside three article reviews. Passing model review does not authorize publication. The campaign remains at `approval_required`, and the shipped tool has no publishing adapter.

## Explore the floor

Select a station to inspect its role and handoff. Open Campaign outputs to read the six drafts. Use Review desk to follow the rejected versions and passing revisions. The floor reads local run records every five seconds; it does not animate invented progress. It also handles unfinished and blocked runs.

The closing bumper says “Build your next factory with Kujo,” followed by `kujolang.ai`. The source archive includes the composition, recordings, original voice takes, font license, timing plan and review notes. Open its `project` directory with HyperFrames to edit it.

## Verification and limits

The 1080p export uses 1920×1080 at 30fps, H.264 video and AAC audio. The phone preview uses 1280×720, H.264 Main level 3.1, yuv420p and AAC-LC. Both files use faststart for browser playback.

Technical checks cover HyperFrames lint and browser validation, full video decode, frame inspection and audio measurements. UI checks cover station selection, output dialogs, review history, mobile width, empty and historical runs, and escaping untrusted titles. See the [media manifest](media/manifest.json) and [playback evidence](media/playback-verification.json) for the retained results.

Listening is not attested. Frame inspection and technical checks are not independent human creative approval. Phone playback is tested through browser emulation, not a physical device.
