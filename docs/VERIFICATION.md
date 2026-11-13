# Verification

Run `npm run verify` after setup. Unit tests cover source containment, symlinks, missing sources, provenance URL schemes, exact excerpt matching, unknown claim references, extra proposal fields, HTML escaping and package drift.

Real-tool integration tests use explicitly synthetic model proposals with the installed Kujo tools. They exercise StoryDesk intake, Dossier evidence, GalleyPack versions and drift checks, BluePencil reviews, VersionSeal requests, the canonical approval pause, wrong-checksum rejection, local leases, missing-adapter blocking and disabled publication phases. These tests do not claim live writing quality.

The [machine-readable evidence](verification.json) records the completed live run, phase timings, review history, fresh-checkout test and browser checks. The [sample campaign](example-campaign/README.md) contains unchanged outputs from that run. Setup timing excludes prerequisite installation, cloning, account sign-in and model generation. The development host is shared and busy; CPU contention and memory pressure were not measured. No clean-machine or universal setup-time promise is made.

The first release is a working local campaign factory with explicit publication and human-review limits. Browser checks validate the viewer and escaped landing template; they do not replace editorial review.

## Recorded results — November 13, 2026

- All 12 tests passed with the real pinned Kujo tools. The integration test also checks adaptation revision history and separate drift detection for the final copies and versioned artifacts.
- The final live campaign took **4m 50.731s** in the measured invocation. It used 12 model calls, including two article revisions and one adaptation revision, then stopped at `approval_required`. No publication effect occurred.
- The independent reviewers rejected overbroad timing language, an ambiguous relationship between example commands and output formats, and incomplete trial instructions. The retained reviews and revised outputs show the actual corrections; these were not staged failures.
- A fresh checkout of the implementation installed dependencies and passed verification in **28.108s** on the same host. This used a local Git clone, existing prerequisites and host caches. It excludes remote top-level cloning, OS/prerequisite installation, sign-in and generation. Do not advertise it as a clean-machine onboarding time.
- Desktop Chrome and a 390px mobile emulation opened all six artifact links, rendered the landing page, and reported no horizontal overflow or page-script errors. The viewer rejected an unexpected Host header and denied the provider-file route. No physical-phone test is claimed.

Two earlier development campaigns were retained as blocked runs: one exposed adapter contract mismatches during implementation, and one found incomplete setup instructions before adaptation revisions were added. A separate earlier live campaign reached human review in 3m 39.968s. These observations describe development runs, not guaranteed completion times or editorial quality certification.
