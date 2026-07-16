# Fixture annotations: ground truth for `fixture-slop.md`

Every tell was injected deliberately. `fixture-clean.md` is the negative control and should trip none of these. If your detector fires on the clean one, that's a false positive worth chasing before you tune anything else.

Source column cites the section of `Wikipedia:Signs of AI writing` the rule derives from.

## Layer 1: lexical and structural

| # | Rule | Instances | Source section |
|---|---|---|---|
| 1 | `vocab.era.gpt4` | delve/delves/delving (7), tapestry (2), testament (4), intricate (5), meticulous (1), pivotal (11), underscore/underscores/underscoring (13), crucial (4), additionally (3), vibrant (3), landscape (7), garner/garnered/garnering (6), interplay (2), boasts/boasting (4), enduring (5), valuable (7), bolstered (0), robust (5) | AI vocabulary, 2023 to mid-2024 bucket |
| 2 | `vocab.era.gpt4o` | align/aligns/aligning with (5), emphasizing (4), enhance/enhancing (9), foster/fostering (4), highlighting (5), showcase/showcases/showcasing (11) | AI vocabulary, mid-2024 to mid-2025 bucket |
| 3 | `vocab.cooccurrence` | Both buckets are saturated in the same document. Era classifier should report *mixed*, which is itself a signal: a human doesn't produce both distributions at once | AI vocabulary, era breakdown |
| 4 | `pattern.copulativeAvoidance` | "serves as" (4), "stands as" (5), "represents a/not merely a" (4), "functions as" (2), "boasts" (4), "refers to" (0) | Avoidance of basic copulatives |
| 5 | `pattern.negativeParallelism` | "not just a delivery mechanism — it's a philosophy"; "not merely malware; it's an ecosystem"; "not merely a compromise, but a paradigm shift"; "isn't just malware — it's a statement" | Negative parallelism, Not just X but also Y |
| 6 | `structure.ruleOfThree` | "numerous, comprehensive, and multifaceted"; "remote shell, file transfer, and SOCKS5 proxying"; "comprehensive, multi-pronged, and holistic"; "trust, verification, and resilience"; "attribution, sovereignty, and resilience"; "operational security, infrastructure rotation, and attribution ambiguity"; "detection capabilities, and contribute"; explicit "vibrant triad" | Rule of three |
| 7 | `pattern.superficialAnalysis` | Trailing participles: "underscoring its significance", "showcasing the group's technical depth", "highlighting the actor's commitment", "reflecting broader trends", "emphasizing the actor's holistic approach", "symbolizing its ongoing commitment", "cementing Sekoia's role" | Superficial analyses |
| 8 | `pattern.undueSignificance` | "marks a pivotal moment" (3), "stands as a testament" (4), "evolving landscape" (3), "reflects broader trends" (2), "for years to come" (3), "shape the trajectory" | Undue emphasis on significance, legacy, broader trends |
| 9 | `pattern.vagueAttribution` | "Industry reports indicate", "experts argue", "Several sources support this assessment", "observers have cited" — none with a matching citation | Vague attributions and overgeneralization |
| 10 | `pattern.cannedNotability` | "a leading voice in the security community with independent coverage across major technology outlets", "profiled in leading security outlets", "garnering significant media attention across leading trade publications" | Canned emphasis on notability, attribution, media coverage |
| 11 | `structure.outlineConclusion` | "Despite these challenges" (3), "Despite these minor limitations", literal heading "Challenges and Future Outlook", "In conclusion" | Outline-like conclusions about challenges and future prospects |
| 12 | `pattern.cutoffDisclaimer` | "As of my last knowledge update", "While specific details regarding the timeline are limited in the available sources", "in ways that may vary" | Knowledge-cutoff disclaimers and speculation about gaps |
| 13 | `punctuation.emDash` | 16 em dashes, all space-surrounded, against typographic convention. Guide is explicit this is weak alone and most useful in combination | Overuse of em dashes |
| 14 | `punctuation.curlyQuotes` | 35 curly apostrophes, 2 curly double quotes. Guide caveat applies: curly quotes alone prove nothing (Word smart quotes, macOS default, Chicago style), so this must never fire alone. Note Gemini and Claude typically do *not* emit them, so presence narrows the era estimate toward ChatGPT or DeepSeek | Curly quotation marks and apostrophes |
| 15 | `format.emoji` | 🔍 in the title, 📌 and 🎯 as section decoration | Emoji as formatting |
| 16 | `format.titleCase` | "Analysis And Assessment", "GammaPhish And GammaWorm", "Compromised @antv NPM Packages", "The Attack Chain", "Key Technical Findings" | Title case |
| 17 | `format.inlineHeaderList` | Every bullet block uses `- **Header**: text` | Inline-header vertical lists |
| 18 | `format.boldfaceDensity` | 40+ bold runs, mechanical, every list label plus emphasis mid-prose | Overuse of boldface |
| 19 | `format.unusualTable` | The 4-row IOC table in Report 2 carries less information than a sentence would | Unusual use of tables |
| 20 | `format.openerBuffer` | "Certainly! Below is a comprehensive analysis..." | Communication intended for the user |
| 21 | `pattern.todayOpener` | "In today's ever-evolving threat landscape", "in today's interconnected digital ecosystem", "in today's world", "in today's threat landscape" | Promotional and advertisement-like language |
| 22 | `pattern.correspondenceLeakage` | "I hope this helps! Let me know if you'd like me to expand"; "Would you like me to also add more IOCs?"; "Best regards, [Your Name]" | Communication intended for the user |
| 23 | `placeholder.leakage` | `[Your Name]`, `[DATE: 2026-XX-XX]`, `INSERT_SOURCE_URL` | Phrasal templates and placeholder text |
| 24 | `artifact.contentReference` | `contentReference[oaicite:0]{index=0}` | Reference markup bugs |
| 25 | `artifact.oaiCitation` | `oai_citation:12‡microsoft.com` | Reference markup bugs |
| 26 | `artifact.turnSearch` | `turn0search3` | turn0search0 |
| 27 | `artifact.lenticular` | `【85†L261-269】` (DeepSeek-flavored) | Reference markup bugs |
| 28 | `artifact.geminiCite` | `[cite: 4]` | Reference markup bugs |
| 29 | `artifact.utmSource` | `?utm_source=chatgpt.com` on the VirusTotal link | utm_source= |
| 30 | `pattern.itsImportantToNote` | "it's important to note that this trend will likely continue" | Didactic disclaimers (historical indicator) |

**Deliberate mixed-artifact signal.** Tells 24 through 29 are ChatGPT, Gemini, and DeepSeek artifacts in one document. That combination is either a multi-tool workflow or copy-paste from several sessions. Your tier-1 classifier should surface the conflict rather than pick one and move on.

## Layer 1 negative evidence: absent by design

The clean fixture carries these; the slop fixture strips them. Both directions should be measurable.

| Signal | Clean | Slop | Source section |
|---|---|---|---|
| Simple is/has constructions | frequent | replaced by serves as / stands as / boasts | Signs of human writing, Syntax |
| Plain verbs over stiff synonyms | "pushed", "handed", "caught", "hit", "sits", "burned" | "utilizes", "facilitates", "leverages", "employs" | Signs of human writing, Syntax |
| Superlative or definitive statements | "the best move in the report", "the only owned asset", "worth the report on its own" | hedged into mush | Signs of human writing, Syntax |
| Hedging qualifiers and intensifiers | "roughly", "close to circular", "worth testing" | absent, replaced by false confidence | Signs of human writing, Syntax |
| Varied cadence | fragments next to long clauses | uniform 20-to-30-word sentences throughout | Break the rhythm |

## Layer 2: analytic gaps

| # | Check | Instance |
|---|---|---|
| 31 | `analytic.containmentAsBlastRadius` | "GitHub revoked 61,274 npm tokens, a number that vividly illustrates the campaign's devastating blast radius"; "640 malicious package versions were identified as victims"; "the 61,274 revoked tokens represent 61,274 compromised developer accounts". This is the highest-value catch in the fixture and it appears three times, escalating. The clean fixture states the correct reading in one line |
| 32 | `analytic.capabilityAsImpact` | "The payload stole credentials from over a million developers worldwide". The million is the weekly download count of a downstream package. Nothing in the source supports a single successful theft |
| 33 | `analytic.responderMetricAsVictimCount` | "20 additional C2 nodes were discovered, representing 20 confirmed victim organizations". C2 nodes are attacker infrastructure. This confuses the attacker's estate with the victim set |
| 34 | `analytic.attributionWithoutBasis` | "Attribution is almost certainly to FSB Center 16, based on targeting patterns and geopolitical alignment". Gamaredon's public attribution runs through the SSU's designation. Center 16 is asserted, sourced to an `oaicite` artifact, and the stated basis (targeting patterns, geopolitical alignment) is not attribution evidence |
| 35 | `analytic.confidenceLanguage` | "could possibly almost certainly", "would likely underscore", "may vary". ICD 203 assigns "almost certainly" a probability band. Stacking it with "could possibly" is incoherent |
| 36 | `analytic.noExposureWindow` | No first-publish-to-unpublish timing on any of the three campaigns |
| 37 | `analytic.noSampleProvenance` | "Gather samples from various sources" is the entire acquisition methodology |
| 38 | `analytic.unvalidatedDetection` | "Develop robust signatures that enhance coverage" with no false-positive measurement, no negative corpus |
| 39 | `analytic.iocDurability` | Every proposed indicator is a campaign-specific value (domain, hash, package name). Zero durable behaviors. Validation is explicitly proposed *against the known IOCs*, which tests the signature against itself |
| 40 | `analytic.circularEvidence` | Report 3 offers resource pooling as both the explanation for cluster overlap and the evidence for it |
| 41 | `analytic.fabricatedCitation` | "Chen et al. (2025)... (doi:10.1109/TSE.2025.3341129)". The DOI is well-formed and the venue is plausible. Resolve it | 
| 42 | `analytic.falsePrecision` | "zero-percent detection rate" is repeated from the source without noting it describes a single sample over a stated window, not the family |

## Assignment-instruction violations

Not AI tells. Separate failure class, and worth scoring separately because a human can fail these too.

| # | Instruction | Violation |
|---|---|---|
| 43 | "Ensure all indicators are properly defanged" | `t.m-kosche.com`, `quitethepastry.ru`, `104.194.140.6`, `graph.org/...`, `telegra.ph/...`, `t.me/s/teotori` all live. A clickable VirusTotal link too |
| 44 | "disclose all tools used" | "AI assistance was used for research support" names nothing |
| 45 | "your written responses must be in your own words" | Whole document, per Layer 1 |
| 46 | Word caps: 200 / 100 / 200 | Four sections over cap: R1 Contextualization (241/200), R1 Critical Review (115/100), R1 Proposed Research (204/200), R2 Contextualization (224/200), R3 Contextualization (208/200). Separately, six of nine self-declared counts are simply wrong, in both directions. The declared number and the real number are independent checks and both fail |
| 47 | Font, size, spacing (Arial 11, 1.15) | Out of scope for a markdown fixture. Flag as untested if you ever render to PDF |

## Expected detector output

For `fixture-slop.md`:

- Era estimate: **mixed**, GPT-4 bucket dominant, GPT-4o bucket present, tier-1 artifacts from three vendors. Confidence high on tool artifacts alone, independent of the lexical layer.
- Analytic gaps: at minimum 31, 32, 33, 34, 39. Miss 31 and the tool has failed at its actual job.
- Instruction violations: 43 and 46 are deterministic and should never be missed.

For `fixture-clean.md`:

- Era estimate: **no fingerprint**, confidence low-to-moderate. It should *not* claim human authorship. The guide is explicit that humans detect at chance and that detectors carry non-trivial error rates. Absence of signal is not evidence of a human.
- Analytic gaps: near zero. It names its own gaps rather than hiding them, and states the containment reading correctly.
- Non-scoring check: the clean fixture uses formal prose, technical vocabulary, and consistent structure. If any of that raises the score, you've scored an ineffective indicator and the guardrail test is broken.

## Known limits of this pair

Two fixtures don't make a corpus. Specific things they won't catch:

- The slop fixture is dense. Real submissions are usually 60% clean prose with a slop paragraph in the middle. Build a **mixed** fixture where a human draft got a single "polish this" pass, because that's the actual population and it's where detectors fall over.
- The clean fixture was written to pass. That's a fair negative control for rules, but it's an unfair test of calibration, since nobody writes this deliberately. A better negative control is a real human submission with typos, an uneven section, and a weak third answer.
- Neither fixture tests the human-writing signals *in adversarial use*: an LLM told to add fragments, drop em dashes, and insert one superlative. That's the next fixture, and it's the one that matters, because it's what anyone reading a de-slop rules list will do.
