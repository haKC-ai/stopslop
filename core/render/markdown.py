"""Markdown renderer for stopslop v2 reports.

Voice rules for generated prose: no em dashes, no en dashes, no emoji,
hyphens only, contractions, no preamble, no recap. Evidence quoted from the
source goes in backticks so the dogfood linter can exclude it: if this
renderer's own prose trips the layer-1 rules, that's a bug and CI catches it.
"""

from __future__ import annotations

from typing import Any

_MAX_FINDINGS_SHOWN = 12
_MAX_SPANS_SHOWN = 3
_EXCERPT_LEN = 90


def _excerpt(span: dict[str, Any]) -> str:
    text = str(span["text"]).replace("`", "'").replace("\n", " ")
    if len(text) > _EXCERPT_LEN:
        text = text[: _EXCERPT_LEN - 3] + "..."
    return f"`{text}` (chars {span['start']}-{span['end']})"


def _render_finding(f: dict[str, Any]) -> list[str]:
    lines = [f"- **{f['rule_id']}** (tier {f['tier']}, {len(f['spans'])} hits)"]
    if f.get("details"):
        lines.append(f"  - {f['details']}")
    for span in f["spans"][:_MAX_SPANS_SHOWN]:
        lines.append(f"  - {_excerpt(span)}")
    return lines


def _render_gap(g: dict[str, Any]) -> list[str]:
    lines = [f"- **{g['id']}** [{g['severity']}] {g['description']}"]
    for span in g["spans"][:_MAX_SPANS_SHOWN]:
        lines.append(f"  - {_excerpt(span)}")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    fp = report["fingerprint"]
    era = fp["era_estimate"]
    rigor = report["rigor"]
    out: list[str] = []

    src = report["source_meta"].get("source", "text input")
    out.append("# stopslop report")
    out.append("")
    out.append(
        f"Source: {src}. {report['word_count']} words analyzed, "
        f"content sha256 {report['content_sha256'][:12]}. "
        f"Rules {report['rules_version']}."
    )
    out.append("")

    out.append("## Fingerprint (supporting signal, not a verdict)")
    out.append("")
    out.append(f"Model-era estimate: **{era['era']}** (confidence: {era['confidence']}).")
    for r in era["rationale"]:
        out.append(f"- {r}")
    if era.get("vendor_artifacts"):
        out.append(f"- Vendor artifacts found: {', '.join(era['vendor_artifacts'])}.")
    out.append("")
    score = fp["score"]
    out.append(
        f"Score components: tier1 {score['tier1']}, tier2 {score['tier2_gated']}, "
        f"tier3 {score['tier3_gated']}, human-signal offset {score['negative_evidence']}, "
        f"net {score['net']}. Components stay separate; there's no threshold and no verdict."
    )
    out.append("")
    if fp["category_densities"]:
        out.append("| Category | Tier | Hits | Per 1000 words |")
        out.append("|---|---|---|---|")
        for cat, d in fp["category_densities"].items():
            out.append(f"| {cat} | {d['tier']} | {d['hits']} | {d['per_1000_words']} |")
        out.append("")
    if fp["findings"]:
        out.append("### Findings")
        out.append("")
        for f in fp["findings"][:_MAX_FINDINGS_SHOWN]:
            out.extend(_render_finding(f))
        if len(fp["findings"]) > _MAX_FINDINGS_SHOWN:
            out.append(f"- plus {len(fp['findings']) - _MAX_FINDINGS_SHOWN} more in the JSON report")
        out.append("")
    if fp["negative_findings"]:
        out.append("### Human-writing signals (subtract)")
        out.append("")
        for f in fp["negative_findings"][:_MAX_FINDINGS_SHOWN]:
            out.extend(_render_finding(f))
        out.append("")
    for c in era["caveats"]:
        out.append(f"> {c}")
    out.append("")

    out.append("## Analytic rigor")
    out.append("")
    missed = rigor["gaps"]
    acked = rigor["acknowledged"]
    if missed:
        out.append(f"{len(missed)} gap(s) the text misses:")
        out.append("")
        for g in missed:
            out.extend(_render_gap(g))
    else:
        out.append("No missed analytic gaps detected by the deterministic checks.")
    out.append("")
    if acked:
        out.append(f"{len(acked)} gap(s) the text acknowledges on its own:")
        out.append("")
        for g in acked:
            out.extend(_render_gap(g))
        out.append("")
    dur = rigor["ioc_durability"]
    out.append(
        f"Indicator durability: {len(dur['behaviors'])} durable behavior(s), "
        f"{len(dur['values'])} campaign-specific value(s)."
        + (
            " Value-weighted: this indicator set has a short shelf life."
            if dur["value_weighted"]
            else ""
        )
    )
    conf = rigor["confidence_terms"]
    if conf["icd203_terms"]:
        out.append(f"ICD 203 terms in use: {', '.join(conf['icd203_terms'])}.")
    if conf["incoherent_stacks"]:
        stacks = ", ".join(f"`{s}`" for s in conf["incoherent_stacks"])
        out.append(f"Incoherent confidence stacks: {stacks}.")
    out.append("")

    audit = report["llm_audit"]
    if audit.get("available"):
        out.append(f"## Critical Review (LLM: {audit['provider']}:{audit['model_version']})")
        out.append("")
        out.append(str(audit["critical_review"]))
        out.append("")
        out.append("## Proposed Research")
        out.append("")
        out.append(str(audit["proposed_research"]))
        out.append("")
    else:
        out.append("## LLM audit")
        out.append("")
        out.append(audit["note"])
        out.append("")

    prov = report["provenance"]
    out.append("## Provenance")
    out.append("")
    if prov["present"]:
        out.append(f"Meter: {prov['meter_line']}")
        if prov["paste_ratio"] is not None:
            out.append(f"Paste ratio: {prov['paste_ratio']}")
    else:
        out.append(prov["note"])
    out.append("")
    return "\n".join(out)
