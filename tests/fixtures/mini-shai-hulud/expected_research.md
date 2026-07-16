#### Proposed Research (reference artifact)

Hypothesis: this payload's durable behaviors (gating to a Linux GitHub Actions runner, scraping Runner.Worker memory, installing Bun, calling Sigstore) form a behavior class detectable at install time rather than after public disclosure.

Method: build a detonation sandbox from disposable micro VMs that emulate a GitHub Actions Linux runner, using synthetic non-privileged tokens and locally emulated metadata and cloud APIs. Never touch a production runner. Run npm packages carrying install hooks through it at volume, instrumenting for /proc scanning, sudoers bind-mount writes, cloud metadata calls, and OIDC exchange. Validate behavioral detection by replaying a quarantined positive sample or a behaviorally faithful fixture, not hashes or a domain, which only test signatures. Build the negative corpus from legitimate preinstall, install, and postinstall packages that share the hard primitives: Bun, OIDC, Sigstore, cloud SDKs, /proc access. Treat PyPI as a separate comparative workstream, since the @antv case is npm specific.

Expected outcome: a weighted detector where durable behaviors drive the score and campaign-specific values act as enrichment. The 61,274 revoked tokens measure GitHub's preventive response, not the campaign's blast radius. The aim is catching the next variant before revocation is the only lever left.
