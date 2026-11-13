# Verification

Run `npm run verify` after setup. Unit tests cover source containment, symlinks, missing sources, provenance URL schemes, exact excerpt matching, unknown claim references, extra proposal fields, HTML escaping and package drift.

Real-tool integration tests use explicitly synthetic model proposals with the installed Kujo tools. They exercise StoryDesk intake, Dossier evidence, GalleyPack versions and drift checks, BluePencil reviews, VersionSeal requests, the canonical approval pause, wrong-checksum rejection, local leases, missing-adapter blocking and disabled publication phases. These tests do not claim live writing quality.

The live example and installation measurements are recorded in the accompanying evidence file after verification. Setup timing excludes prerequisite installation, cloning, account sign-in and model generation. The development host is shared and busy; CPU contention and memory pressure were not measured. No clean-machine or universal setup-time promise is made.

The first release is a working local campaign factory with explicit publication and human-review limits. Browser checks validate the viewer and escaped landing template; they do not replace editorial review.
