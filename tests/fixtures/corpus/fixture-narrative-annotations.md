# Fixture annotations: ground truth for `fixture-narrative.md`

The third fixture. `fixture-slop.md` is 2023-2024 slop (delve, tapestry, testament, leaked `oaicite` markup). `fixture-clean.md` is the human control. This one is the gap the pair left open: a **2025-2026 chat-register** writeup of the same incident as `mini-shai-hulud`, carrying almost none of the old vocabulary and nearly all of the new conversational tells.

It covers the same facts as `well-sourced/source.md`. That is deliberate. The difference between the two is register, not content, so anything that fires here and not there is measuring what it claims to measure.

Source column cites the rule pack, then the external catalog the rule derives from.

## Layer 1: conversational register (`rules/layer1_narrative.json`)

| # | Rule | Instances in the fixture | Derived from |
|---|---|---|---|
| 1 | `narrative.performed-candor` | "Honestly?", "Let me be direct", "I'll be honest", "The honest answer is", "the uncomfortable truth", "the quiet part" | Forbes 2026-02-03; Polytranslator Claude-speak; Velitchkov, 22 Claude Cliches |
| 2 | `narrative.payoff-hooks` | "Here's the thing", "The best part?" (via rhetorical-qa), "Read that again", "Let that sink in" (implied), "that's the whole game" | Forbes 2026-02-03: "Here's the kicker", "The best part?"; claudisms.ai |
| 3 | `narrative.rhetorical-qa` | "The catch? It only runs...", "So what does this mean? Three things." | SlopDetector 2026: "The result?"; AIPromptIndex |
| 4 | `narrative.colon-fragments` | "Translation:", "Bottom line:", "**The result:**", "**The real question:**", "**The fix:**", "Zoom out:" | Blake Stockton, Colons everywhere; Velitchkov, "Better posed:" |
| 5 | `narrative.sycophancy` | "Great question." | anthropics/claude-code issue #3382; Georgetown Law AI sycophancy brief |
| 6 | `narrative.chat-offers` | "Want me to turn this into...", "If you'd like, I can also draft", "Just say the word" | PCWorld 2026; guide § Communication intended for the user |
| 7 | `narrative.reasoning-spill` | "Wait, actually — let me double-check the exposure window" | openai/codex issue #37524; PAN 2026 reasoning-trajectory task |
| 8 | `narrative.hortatives` | "Let's dig in", "Let's start with" | Olivia Cal 2026; Tan Rosado, "Let's dive in" |
| 9 | `narrative.conversational-pivots` | "That said,", "Which brings me to", "One caveat" | Prowlo 2026; umanwrite 2026 |
| 10 | `narrative.adverbial-openers` | "Critically,", "Interestingly,", "Ultimately,", "Fundamentally,", "Frankly,", "Make no mistake," | Penpoint, ChatGPT's adverb habit; Polytranslator |
| 11 | `narrative.reframe-contrast` | "It's not about infecting developers — it's about harvesting", "this isn't a supply chain compromise... This is a CI credential harvester", "not because they're wrong, but because they die", "less about npm and more about CI" | guide § Negative parallelisms; explainx.ai Claudisms |
| 12 | `narrative.staccato-fragments` | "No shell. No exfil. Just a wasted download.", "Not Microsoft. Not GitHub. Not the maintainers.", "Every install. Every pipeline. Every day." | Olivia Cal, "No X. No Y. Just Z."; explainx.ai |
| 13 | `narrative.emphatic-tails` | "— full stop", "— not because they're wrong" | guide § Overuse of em dashes |
| 14 | `narrative.real-x-recentering` | "The real question", "what actually happened", "the part most people miss", "Why this matters" | Forbes 2026: "Here's the part most people miss" |
| 15 | `narrative.signposting` | "More on that below", "As we'll see" | guide § Historical indicators, Section summaries |
| 16 | `narrative.second-person-address` | "If you're reading this", "You might be thinking" | Olivia Cal, "As a business owner, you know..." |

## Layer 1: 2026 vocabulary and mechanical artifacts

| # | Rule | Instances | Derived from |
|---|---|---|---|
| 17 | `vocab.era.chat2026` | genuinely, nuanced, compelling, seamless, deceptively simple, heavy lifting, resonate, the quiet part | Polytranslator; Olivia Cal blacklist 2026; Forbes on "quiet" |
| 18 | `vocab.era.claude` | load-bearing | louisabraham/load-bearing (929 in-cluster vs 82 out, 461k PR corpus) |
| 19 | `artifact.thought-duration` | "Thought for 14 seconds" | reasoning-UI chrome copied with the answer |
| 20 | `artifact.chatgpt-transcript-label` | "ChatGPT said:" | ChatGPT share/copy format |
| 21 | `format.em-dash-density` | 8 em dashes, mostly unspaced | guide § Overuse of em dashes |
| 22 | `structure.h1-overuse` | two level-1 headings ("# Mini Shai-Hulud, explained", "# Closing thoughts") | guide § Overuse of level 1 headings |
| 23 | `pattern.cutoff-selfref` | "I don't have access to real-time telemetry" | guide § Knowledge-cutoff disclaimers, 2026 capability-disclaimer form |

## What this fixture deliberately does **not** carry

This is the point of the fixture. It is a false negative for the entire pre-2025 pack:

| Absent | Rule that stays silent |
|---|---|
| delve, tapestry, testament, intricate, meticulous, pivotal | `vocab.era.gpt4` below its gate |
| "stands as a testament", "evolving landscape", "for years to come" | `pattern.undue-significance` |
| "Industry reports indicate", "experts argue" | `pattern.vague-attribution` |
| "In today's ever-evolving threat landscape" | `pattern.today-opener` |
| "Despite these challenges", "In conclusion" | `pattern.outline-conclusions` |
| `oaicite`, `turn0search0`, `[cite: N]`, lenticular brackets | the ChatGPT/Gemini/DeepSeek markup rules |
| emoji section decoration, title case headings | `format.emoji-decoration`, `structure.title-case-headings` |

Run it against the v2.0 rule set and it comes back **era `none`, confidence low, net 0.0**. That is the miss the 2.1 pack closes.

## Expected detector output

For `fixture-narrative.md`:

- Era estimate: **chat2026**, confidence **high** (two tier-1 artifacts: the thinking-UI line and the transcript label).
- At least 15 of the 16 `narrative.*` rules fire.
- Layer 2 still works on it: the containment-vs-blast-radius reading is stated correctly here, so that gap should be **acknowledged**, not missed. Register and rigor are independent axes and this fixture proves it.

For the three human fixtures (`fixture-clean.md`, `well-sourced/source.md`, `mini-shai-hulud/source.md`):

- Net score stays exactly **0.0**, tier 1 stays **0**, era stays **none**. `tests/test_narrative_register.py::TestHumanProseNeverScores::test_human_fixtures_still_clean` and the CI gate both enforce this. The register pack is only worth shipping if it costs the human control nothing.

## False-positive traps

`tests/test_narrative_register.py` carries ten probes of ordinary analyst prose that a naive widening of these rules would flag. They are the real specification. The load-bearing ones:

- **"surface" as a verb and "beacon" as a noun are excluded from `vocab.era.claude` and `vocab.era.chat2026`.** Both are ordinary SOC vocabulary; scoring them would fire on every hunt writeup. Independent sources rate both HIGH false-positive risk in security writing.
- **Structured analyst labels are excluded from `narrative.colon-fragments`.** "Hypothesis:", "Method:", "Scope:", "Findings:", "Recommendation:" are the shape of a good report, not a chat tic. Only editorial labels ("Translation:", "Bottom line:") score.
- **"In the interest of full disclosure" is excluded from `narrative.performed-candor`.** In security writing that phrase introduces a real conflict-of-interest statement.
- **`narrative.emphatic-tails` requires an em dash, en dash, or spaced hyphen**, so "pre-period" and "ultra-fast" never match.
- **Formal transitions (however, moreover, furthermore, therefore) are excluded everywhere.** The guide lists transition words in isolation as an ineffective indicator, and `test_nonscoring.py` enforces it.

## Known limits

- The fixture is dense, the same criticism the original pair earned. A human draft given one "make this punchier" pass is the harder population and it is still unbuilt.
- Every phrase here is a public, published tell. Anyone reading the rule list can strip them in one editing pass, which is exactly the failure mode the guide warns about. That is why the register rules are tier 2 and 3, gated by clustering, and why layer 2 rigor stays the product.
- The `claude` era bucket rests on one quantified corpus study. Treat a `claude` call as weaker than a `gpt4` call until a second source lands.
