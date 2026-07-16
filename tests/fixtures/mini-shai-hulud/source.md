# Mini Shai-Hulud: compromised @antv packages push credential stealer through npm

A supply-chain compromise hit the npm ecosystem this week. An attacker took over a maintainer account for the @antv organization and shipped malicious versions of the G2 and G6 data-visualization libraries. Those poisoned releases flowed downstream into echarts-for-react, a package with over a million weekly downloads. We call the campaign Mini Shai-Hulud, named for its resemblance to the Shai-Hulud worm campaign that swept npm earlier: the same taste for self-propagation through the package graph, the same appetite for CI secrets.

## The payload

The malicious versions carry a 499 KB obfuscated JavaScript file that overwrites index.js and fires during npm install through a preinstall hook. Execution chains node to a shell script to the Bun runtime, which the payload installs if it's missing. Two layers of obfuscation wrap the logic, including PBKDF2/SHA-256 runtime decryption of the C2 domain.

The payload gates hard: execution stops unless it finds itself inside GitHub Actions on Linux. On a developer laptop it does nothing.

Once inside a runner, it harvests credentials across GitHub, AWS, HashiCorp Vault, npm, Kubernetes, and 1Password. It scrapes Runner.Worker process memory to defeat GitHub's secret masking, walks /proc for environment blocks, and attempts privilege escalation through a passwordless-sudo bind mount. Exfiltration goes over HTTPS to t.m-kosche[.]com, with the GitHub Git Data API and self-created public repositories as fallbacks. The payload also forges SLSA provenance through Sigstore, so downstream consumers see attestations that look legitimate.

## Scale

GitHub removed 640 malicious package versions, a figure that illustrates the sheer scale of the attack across the ecosystem. The platform also revoked 61,274 write-enabled npm tokens, and that number speaks to the campaign's reach across the developer community. Every one of those tokens sat within the campaign's grasp.

## Hunting

Defenders should hunt for the following:

- npm packages executing preinstall hooks that spawn shells and install Bun
- processes reading Runner.Worker memory on Linux CI hosts
- writes to sudoers via bind mounts inside build containers
- Sigstore signing calls from build steps that don't normally produce attestations

The hunting queries below encode these behaviors for common SIEM platforms and ship ready to deploy.

## Indicators

| Type | Value |
|---|---|
| Domain | t.m-kosche[.]com |
| Package | @antv/g2 |
| Package | @antv/g6 |
| Downstream | echarts-for-react |
| Payload SHA256 | 4c2f8dbb1a09e6f3b7a2d951c04e8f7a6b3d2e1f0c9b8a7d6e5f4a3b2c1d0e9f |

The payload filename and the Bun install path vary per build and are listed in the appendix.
