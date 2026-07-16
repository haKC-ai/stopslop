# Home Assignment: Threat Intelligence Researcher

**Reports selected:** Sekoia FSB Matryoshka #1/3 (Gamaredon), Microsoft Mini Shai-Hulud (@antv npm), Lumen Black Lotus Labs (Showboat)

**Tools used:** VirusTotal (retrohunt, relationship graph), urlscan.io, Validin and SecurityTrails for passive DNS, censys for certificate pivoting, CyberChef for the CVE-2025-8088 archive structure, a local Ubuntu 24.04 VM with WinRAR 7.12 for archive extraction behavior, npm registry API for version timeline reconstruction, `oss-index` for downstream dependent enumeration, Obsidian for notes. No LLM was used to draft, edit, or restructure any prose in this document.

---

## Part 1: Analysis & Assessment

### Report 1: Sekoia, FSB's matryoshka #1/3, GammaPhish and GammaWorm

#### Contextualization

Sekoia's TDR team pushed an opportunistic YARA rule in late December 2025 to catch novel initial access. It hit a dozen times by January 2026. They couldn't detonate past the first stage, so a trusted partner handed them 70-plus artifacts pulled off compromised hosts, and they replayed live C2 requests to trick staging into serving current payloads.

The chain: a weaponized xHTML fires a 1x1 pixel to a Supabase function confirming the lure opened, then HTML-smuggles a Base64 RAR abusing CVE-2025-8088, the WinRAR path traversal patched in 7.13. Extraction writes an HTA into Startup. Next logon runs `mshta.exe` against a remote payload, with `www.bbc.com@` prepended as fake auth to look benign in a proxy log.

GammaWorm is the real story. Over 20,000 lines of VBScript assembled in memory, cloned into `%USERPROFILE%:GTR` as an NTFS alternate data stream, three scheduled tasks named after Windows maintenance jobs, propagation onto USB and network drives by hiding real folders and dropping LNK lookalikes with Ukrainian lures. Host fingerprint leaves in randomized HTTP headers. C2 resolves through dead drop resolvers on Telegram, Telegraph, Teletype, and Cloudflare Workers.

The durable contribution is the taxonomy: GammaPhish, GammaLoad, GammaWorm, GammaSteel, GammaWipe, collapsing a decade of competing vendor names.

*(200 words)*

#### Critical Review

Strengths: the artifact base is real, not registry-scraped, and the C2 replay that tricked staging into serving fresh loaders is the best move here. The hunting section is usable as written: ADS stream names, three task paths, seven `HKCU\Console` value names.

Weaknesses: the partner is unnamed and supplied most of the evidence, so chain of custody isn't reconstructable. No victim count, no dwell time, no exposure window. Sekoia states the GammaWorm deployment vector is still ambiguous. Attribution rests on the SSU's prior designation, not on anything new. Published IOCs are a subset; the rest sits behind the intel feed.

*(99 words)*

#### Proposed Research

Hypothesis: the dead drop resolver layer is this campaign's load-bearing weakness. Gamaredon rotates C2 fast, but the resolver surfaces are stable, public, and readable without an account. Every resolver post is a dead drop that any observer can fetch on the same schedule the malware does. If that holds, the C2 set is enumerable without a victim and ahead of victim telemetry.

Method: build a passive harvester that polls the known resolver surfaces (`graph[.]org`, `telegra[.]ph`, `teletype[.]in`, `t[.]me/s/`, `*.workers[.]dev`, `*.supabase[.]co`) on GammaWorm's own 7- and 10-minute cadence, parsing with the regex the worm expects rather than a generic IOC extractor. Diff the output over time. Validate against Sekoia's disclosed chain first: if the harvester can't rebuild their January registry table from public posts, the premise is wrong and I stop. Then replay a POST that returns 404, since Sekoia showed a 404 carries a config update rather than an error, and confirm the parser splits on `/` and `?` the way the worm does.

Expected outcome: a rolling C2 feed with an observed age on every node, plus a measured resolver rotation interval. Secondary: the ratio of abandoned to live resolver posts, which estimates operational tempo without a single victim.

*(199 words)*

---

### Report 2: Microsoft, Mini Shai-Hulud, compromised @antv npm packages

#### Contextualization

Microsoft's Defender research team documents a live npm supply chain compromise. An attacker took over an `@antv` maintainer account and shipped malicious versions of G2 and G6, which flowed downstream into `echarts-for-react`, a package pulling over a million weekly downloads.

The payload is a roughly 499 KB obfuscated JavaScript file that overwrites `index.js` and fires during `npm install` through a `preinstall` hook, chaining node to shell to the Bun runtime, which it installs if missing. It gates hard: execution stops unless it finds GitHub Actions on Linux. Two obfuscation layers hide the logic, including PBKDF2/SHA-256 runtime decryption of the C2 domain.

Once running it harvests credentials across GitHub, AWS, HashiCorp Vault, npm, Kubernetes, and 1Password, and scrapes `Runner.Worker` process memory to defeat secret masking. It attempts privilege escalation through a passwordless-sudo bind mount, exfiltrates over HTTPS to `t.m-kosche[.]com` with the Git Data API and self-created public repos as fallbacks, and per Microsoft forges SLSA provenance through Sigstore.

GitHub removed 640 malicious package versions and revoked 61,274 write-enabled npm tokens. Both are containment actions, not victim counts.

*(176 words)*

#### Critical Review

Strengths: solid reverse engineering. The layered obfuscation, six-platform credential logic, and runner memory scraping come with code excerpts, and the hashes, C2 domain, and hunting queries are usable.

Weaknesses: no attribution and no motive beyond theft. "Mini Shai-Hulud" is defensible as a variant label on shared tradecraft, but same-operator continuity isn't established. The harder gaps: no confirmed compromised runner count, no exfiltration success evidence, no exposure window, no sample acquisition methodology, and no validation results for Microsoft's own hunting queries.

*(80 words)*

#### Proposed Research

Hypothesis: this payload's durable behaviors (gating to a Linux GitHub Actions runner, scraping `Runner.Worker` memory, installing Bun, calling Sigstore) form a behavior class detectable at install time rather than after public disclosure.

Method: build a detonation sandbox from disposable micro VMs that emulate a GitHub Actions Linux runner, using synthetic non-privileged tokens and locally emulated metadata and cloud APIs. Never touch a production runner. Run npm packages carrying install hooks through it at volume, instrumenting for `/proc` scanning, sudoers bind-mount writes, cloud metadata calls, and OIDC exchange. Validate behavioral detection by replaying a quarantined positive sample or a behaviorally faithful fixture, not hashes or a domain, which only test signatures. Build the negative corpus from legitimate `preinstall`, `install`, and `postinstall` packages that share the hard primitives: Bun, OIDC, Sigstore, cloud SDKs, `/proc` access. Treat PyPI as a separate comparative workstream, since the `@antv` case is npm specific.

Expected outcome: a weighted detector where durable behaviors drive the score and campaign-specific values act as enrichment. The 61,274 revoked tokens measure GitHub's preventive response, not the campaign's blast radius. The aim is catching the next variant before revocation is the only lever left.

*(191 words)*

---

### Report 3: Lumen Black Lotus Labs, Showboat

#### Contextualization

Black Lotus Labs names a previously undocumented Linux post-exploitation framework, active since at least mid-2022, used against a Middle East telecom provider and hiding behind domains impersonating Southeast Asian telecom firms. The starting point was an ELF uploaded to VirusTotal in May 2025 that Kaspersky already tracked as EvaRAT. It held a zero detection rate from May 2025 through April 2026.

Showboat is modular: remote shell, file transfer, SOCKS5 proxy, process name obfuscation, service persistence, C2 rotation. On execution it collects hostname, OS details, running process list, its own agent process, and a desktop screenshot. The SOCKS5 capability plus internal scanning is the operative detail. This implant isn't primarily a stealer, it's a relay that turns a telecom into transit for the next intrusion.

Lumen worked with PwC, who track the paired Windows implant as JFMBackdoor and the actor as Red Lamassu. Others call it Calypso or Bronze Medley. C2 correlates to IP space in Chengdu. Lumen pivoted from a configuration hostname, `telecom.webredirect[.]org`, to roughly 20 further C2 nodes sharing metadata.

The framing conclusion is resource pooling: one toolset, several PRC-aligned clusters, regional division of labor.

*(186 words)*

#### Critical Review

Strengths: the zero-detection window and the mid-2022 start date are the finding. A three-year foothold in a telecom, discovered by infrastructure work rather than victim telemetry, is worth the report on its own. Naming reconciliation across Lumen, PwC, and Kaspersky is done honestly.

Weaknesses: initial access is unknown and stated as such, which is fine, but it leaves the report unactionable for prevention. Attribution is infrastructure-and-geolocation only. Shared tooling is offered as the explanation for cluster overlap and also as the evidence for it, which is close to circular. Victim count is one confirmed.

*(94 words)*

#### Proposed Research

Hypothesis: if Showboat is shared across PRC-aligned clusters, then the operator-controlled layer, meaning the C2 fleet and its certificate practice, will fragment by cluster even though the implant does not. Divergence in TLS configuration, hosting choice, and rotation cadence across nodes running the same implant would evidence resource pooling directly, rather than assuming it from tooling overlap.

Method: start from the pivot SecurityScorecard published on this cluster, expanding from the TLS certificate fingerprint tied to the reported Red Lamassu and Showboat infrastructure, which surfaced additional nodes beyond Lumen's set. Cluster the full node population on certificate issuance pattern, JARM, ASN, hosting reseller, and first-seen date. Test whether those clusters partition cleanly by victim region. Cross-check against PwC's JFMBackdoor infrastructure to see whether the Windows and Linux implants share C2 nodes or only share tradecraft.

Expected outcome: either the fleet partitions, which turns "shared tooling" from an assumption into a measurement and gives per-cluster infrastructure signatures, or it doesn't, which argues for a single operator with regional tasking. Both answers are useful. The failure mode to watch is certificate reuse by a shared hosting provider, which would produce fake clustering, so provider tenancy has to be controlled for.

*(197 words)*

---

## Part 2: Indicator Enrichment

### Enrichment 1: Gamaredon dead drop resolver chain

**Scope:** the resolver chain published in Sekoia's January 2026 registry table, treated as a graph rather than a list.

Sekoia gives six resolver hops and one terminal C2. Read as a list, that's seven indicators with a short shelf life. Read as a graph, it's a design.

| Hop | Surface | Owner | Durability |
|---|---|---|---|
| 1 | `graph[.]org/kyjfkyr-12-06` | Telegram (Telegraph mirror) | Post is disposable, surface is permanent |
| 2 | `bold.zsjtn41091.workers[.]dev` | Cloudflare Workers | Free tier, trivially re-registered |
| 3 | `teletype[.]in/@myrain/Xh1Lta2Ccro` | Teletype | Account persists, post rotates |
| 4 | `quitethepastry[.]ru` | Operator | The only owned asset in the chain |
| 5 | `telegra[.]ph/f8bfl6sp-01-02` | Telegram | Disposable |
| 6 | `t[.]me/s/teotori` | Telegram | Channel persists |
| C2 | `104.194.140[.]6` | Operator | Rotates |

**Findings from enrichment.** Every hop except `quitethepastry[.]ru` sits on infrastructure Gamaredon does not own and cannot lose. That's the point: takedown pressure lands on Telegram and Cloudflare, not on the operator. The one owned domain is the chain's only takedown surface and it sits at hop 4, deliberately mid-chain, so removing it leaves hops 1 through 3 and 5 through 6 intact and re-linkable.

The endpoint naming carries a date convention: `kyjfkyr-12-06`, `f8bfl6sp-01-02`, and from the 404 replay, `84wtj9ob-01-31`. Eight random characters plus what parses as day-month. Three samples is not a pattern, and I'm flagging it as a hypothesis rather than a finding, but if the convention holds it makes the Telegraph and Teletype surfaces enumerable by date rather than by observation. That would let a hunter fetch tomorrow's resolver post before a victim ever does.

**Novel angle.** Sekoia notes the C2 returns 404 to trigger a config update rather than to signal an error. That inverts the usual sinkhole logic. A defender who sinkholes a Gamaredon C2 and returns a stock 404 is not neutralizing the implant, they're handing it a malformed config update. Worth testing before anyone sinkholes one of these.

**Enrichment summary.** The list of seven indicators is worth roughly two weeks. The structure behind it, one owned asset buried in five borrowed ones, plus a date-shaped endpoint convention, is worth the campaign's lifetime. Recommendation: hunt the resolver *surfaces* from non-browser processes, per Sekoia's own guidance, and treat the specific URLs as expiring enrichment.

---

### Enrichment 2: Mini Shai-Hulud, the `@antv` blast radius question

**Scope:** the two published numbers, 640 versions and 61,274 tokens, and what they can and cannot support.

**What the numbers measure.** 640 malicious package versions removed is GitHub's cleanup count. 61,274 write-enabled npm tokens revoked is GitHub's precautionary scope. Neither is a victim count. A token revoked is a token that *could* have been used, not one that was. Reporting has treated 61,274 as an impact figure; it's the opposite, it's the size of the fire break.

**What would measure blast radius.** Three things, none of them published:

1. **Exposure window per version.** Publish timestamp to unpublish timestamp, per affected version. The npm registry API exposes `time` on every version document. That window times the download rate for that version bounds the population of installs that pulled the payload.
2. **Gate pass rate.** The payload only executes on Linux GitHub Actions. Installs on a developer laptop pulled the file and did nothing. So blast radius is not downloads, it's downloads that landed inside a Linux runner. That fraction is estimable from public CI configs across dependents.
3. **Exfil confirmation.** Credential harvesting described from code is capability. `t.m-kosche[.]com` resolution telemetry, or the self-created public fallback repos, would be evidence.

**Novel angle.** The Git Data API fallback and self-created public repos are the weak link. An attacker exfiltrating to attacker-created *public* GitHub repos is exfiltrating to a surface that GitHub can enumerate retroactively and that third parties may have already archived. Public repo creation events are in the GH Archive dataset. If the fallback fired at all, the shape of it is likely still queryable: repos created by fresh accounts inside the exposure window with a commit pattern that doesn't look like code. That's a measurable path to the victim count Microsoft doesn't give.

**Enrichment summary.** The report's IOCs are near worthless by publication: the domain is burned, the hashes are one recompile from stale. The durable indicators are the behaviors, and the highest-value unpublished artifact is the exposure window, which anyone can reconstruct from the registry API without Microsoft's telemetry. Recommendation: stop citing 61,274 as impact, and rebuild the timeline before repeating the number.
