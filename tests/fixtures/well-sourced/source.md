# Compromised @antv packages: credential stealer in the npm dependency graph

## Summary

An attacker took over an @antv maintainer account and shipped malicious versions of the G2 and G6 visualization libraries, which flowed downstream into echarts-for-react. We use "Mini Shai-Hulud" as a variant label on shared tradecraft with the earlier Shai-Hulud worm; operator continuity is not established, and nothing in our evidence links the two operators. We make no attribution claim: we found no infrastructure overlap with tracked actors, no code reuse against our corpus, and the victimology is too broad to narrow anything. The motive we can evidence is credential theft. We checked for follow-on staging and access resale patterns and saw neither, though our visibility there is partial and we say so below.

## Timeline and exposure window

The first malicious version published on 2026-06-30 at 14:02 UTC. Our scanner flagged the anomalous preinstall hook and we reported it to GitHub on 2026-07-01 at 22:15 UTC. npm removed the last affected version on 2026-07-02 at 09:41 UTC. That is a 43-hour exposure window, and the per-version windows are in appendix A with registry timestamps for each of the 640 versions.

## Sample handling

We pulled all 640 malicious versions from the npm registry within one hour of takedown and verified each tarball hash against the registry manifest. Detonation happened in disposable VMs emulating a Linux GitHub Actions runner with synthetic tokens. No production runner was touched.

## The payload

The 499 KB obfuscated JavaScript file overwrites index.js and fires during npm install through a preinstall hook, chaining node to a shell script to the Bun runtime, which it installs if missing. Two obfuscation layers wrap PBKDF2/SHA-256 runtime decryption of the C2 domain. The payload gates hard: it runs only inside GitHub Actions on Linux.

Inside a runner it harvests credentials across GitHub, AWS, HashiCorp Vault, npm, Kubernetes, and 1Password, scrapes Runner.Worker process memory to defeat secret masking, walks /proc, and attempts privilege escalation through a passwordless-sudo bind mount. Exfiltration goes to t.m-kosche[.]com with the Git Data API and self-created public repos as fallbacks. It forges SLSA provenance through Sigstore.

## Impact, measured

Capability is not impact, so here is what we measured. Netflow from our sensor estate shows resolution attempts for the C2 domain from 214 organizations, and three confirmed victim organizations where completed exfil POST bodies were observed and verified with the affected teams. Beyond those three, no exfiltration success is confirmed. We had no visibility into the Git Data API fallback path and treat that as an open question, not as absence of theft.

GitHub removed 640 malicious package versions and revoked 61,274 write-enabled npm tokens. Both numbers are containment actions, not victim counts: the removals measure cleanup and the revocations measure the size of the precautionary fire break. The confirmed victim count above is the only impact figure this report stands behind.

## Detection content and validation

The hunting queries in appendix B target the durable behaviors: preinstall hooks spawning shells and installing Bun, Runner.Worker memory reads, sudoers bind-mount writes, and Sigstore calls from build steps that don't normally attest. We tested the queries against 30 days of CI telemetry from 1,100 repositories. The false-positive rate was 0.4 percent, and the negative corpus was built from legitimate install-hook packages that use Bun, OIDC, and Sigstore for real work. The campaign-specific values (domain, hashes, package names) are listed separately in appendix C and should be treated as expiring enrichment, since durable behaviors drive detection and values die with the next variant.

We assess it is likely the actor retooles and returns to npm within months; the registry-side conditions that allowed the takeover are unchanged.
