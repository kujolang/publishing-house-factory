# Example campaign

`videoops-launch.json` asks the factory to explain VideoOps Factory, qualify its setup observations and show readers how to try it. Supply your own subject and source packet using the same brief contract.

The two text files in `sources/` preserve the README and onboarding document from `kujolang/videoops-factory` commit `dcf2dc4fa7311f59ba3dd16f58a227439a155979`. The brief contains exact upstream URLs. These are source snapshots, not current product guarantees; update both provenance and source text when using a newer release. The factory records their hashes at intake.

Run the example with:

```sh
npm run factory -- run examples/videoops-launch.json
```

Model calls use your Codex account. The example creates a local review package and stops before publication. It does not make a video, send a newsletter or post to social accounts.
