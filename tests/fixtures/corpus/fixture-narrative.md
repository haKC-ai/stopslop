# Mini Shai-Hulud, explained: what actually happened in the @antv npm compromise

Thought for 14 seconds

ChatGPT said:

Great question. Honestly? Most of the coverage of this incident has been missing the point. Let's dig in.

Here's the thing: everyone is quoting the 61,274 revoked tokens as if it were a body count. It isn't. That number measures GitHub's response, not the attacker's reach — and that distinction is load-bearing for everything that follows. More on that below.

## What happened

In late June 2026 an attacker took over an @antv maintainer account and pushed malicious versions of G2 and G6, which flowed downstream into echarts-for-react. The payload—a 499 KB obfuscated JavaScript blob—overwrites index.js and fires from a preinstall hook. Node to shell to Bun. It installs Bun if it has to.

The catch? It only runs inside GitHub Actions on Linux. Everywhere else it does nothing. No shell. No exfil. Just a wasted download.

Let me be direct: that gate is the single most important design decision in the whole campaign, and it's the part most people miss. The gate is deceptively simple, and that one check does most of the heavy lifting. It's not about infecting developers — it's about harvesting CI secrets at scale.

## Why this matters

I'll be honest, the credential list is genuinely impressive: GitHub, AWS, HashiCorp Vault, npm, Kubernetes, 1Password. It scrapes Runner.Worker memory to defeat secret masking. It tries a passwordless-sudo bind mount. It forges SLSA provenance through Sigstore. Read that again. The attacker signed their own malware with the ecosystem's trust machinery.

Bottom line: this isn't a supply chain compromise in the classic sense. This is a CI credential harvester that happens to travel through npm.

That said, capability isn't impact. Nobody has published a confirmed count of compromised runners. Not Microsoft. Not GitHub. Not the maintainers. The honest answer is that we don't know how many secrets left the building, and that is a nuanced point the compelling headline numbers paper over.

## The numbers, and what they don't say

Translation: 640 malicious versions is a cleanup count. 61,274 tokens is the size of the fire break. Neither is a victim count — full stop.

So what does this mean? Three things.

- **The result:** the widely quoted blast radius is a containment metric wearing an impact costume.
- **The real question:** how many Linux runners actually pulled an affected version inside the 43-hour exposure window?
- **The fix:** stop citing revocations as reach.

Wait, actually — let me double-check the exposure window. Microsoft's write-up gives first publish at 14:02 UTC on 30 June and last removal at 09:41 UTC on 2 July. Forty-three hours. Confirmed.

Critically, none of this requires Microsoft's telemetry. The npm registry API exposes per-version timestamps. Anyone can rebuild the timeline. Interestingly, almost nobody has. As we'll see, that gap is the whole story.

## What you should actually do

If you're reading this and you run Linux runners, here's what I'd do, in order. You might be thinking the hashes are enough. They are not.

1. Let's start with the durable behaviors, not the hashes. Preinstall hooks that spawn shells and install Bun. Runner.Worker memory reads. Sudoers writes. Sigstore calls from build steps that don't normally attest.
2. Treat the domain, the hashes, and the package names as expiring enrichment — not because they're wrong, but because they die with the next variant.
3. Zoom out: the registry-side conditions that allowed the takeover are unchanged. This will happen again.

Ultimately, the uncomfortable truth is that the detection content most teams deployed tests the signature against the campaign's own IOCs, which is circular. It's not that the queries are bad; it's that they're validated against nothing.

Fundamentally, this campaign is less about npm and more about the trust we place in CI. Make no mistake, the attacker understood that better than most defenders do.

# Closing thoughts

Frankly, the seamless way this payload moved through the dependency graph should resonate with anyone who has ever added a package without reading its install hooks. Which brings me to the quiet part: we all do that. Every install. Every pipeline. Every day.

One caveat — I don't have access to real-time telemetry, so the victim count above is an inference, not a measurement.

Want me to turn this into a detection checklist for your runners? If you'd like, I can also draft the hunting queries. Just say the word.
