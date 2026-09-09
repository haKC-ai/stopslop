#!/usr/bin/env python3
"""Rule-drift patrol: does the rule set still match the guide it cites?

Every rule in rules/*.json carries a `source_citation`. For rules derived from
Wikipedia:Signs of AI writing that citation names a specific section, so the
set of sections the rule pack depends on is derivable from the pack itself.
This compares that set against the live guide and reports three things:

  STALE      a rule cites a section that no longer exists under that name
  UNCOVERED  the guide has a scoreable section that no rule cites
  DRIFT      a cited section's wikitext changed since the pinned revision

The guide is edited close to daily, mostly copyedits, so watching the page as
a whole produces a false alarm every day and gets muted within a week. Only
the cited sections are diffed, and only against a pinned revision that a human
re-pins after review with --update-pin.

Deterministic: one API call for the section list, one for the wikitext. No
LLM, no judgement. Exit 0 clean, 1 drift found, 2 could not check.
"""

from __future__ import annotations

import argparse
import difflib
import glob
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / ".rule-sources.json"
GUIDE_TITLE = "Wikipedia:Signs of AI writing"
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "stopslop-rule-drift/1.0 (+https://github.com/haKC-ai/stopslop)"

CITATION_RE = re.compile(r"Wikipedia:Signs of AI writing\s*§\s*([^;]+)")
HEADING_RE = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.MULTILINE)

# Guide sections that describe Wikipedia-editing artifacts rather than writing.
# stopslop scores threat-intelligence prose, so a rule for these would never
# fire on its corpus. Listed explicitly so "uncovered" stays meaningful: an
# entry here is a decision, not an oversight.
OUT_OF_SCOPE = {
    "leads treating wikipedia lists or broad article titles as proper nouns",
    '"awards and recognition" section',
    "broken wikitext",
    "non-existent or out-of-place categories",
    "non-existent templates",
    "links to searches",
    "named references declared in references section but unused in article body",
    "comment-specific indicators",
    "edit summaries",
    "general examples",
    "canned assurance of adherence to wikipedia policies and guidelines",
    'specific mentions of "preserved" or "retained" information, "avoided" mistakes',
    "overemphasis on presence/reliability of citations",
    "overemphasis on parameter/template names and markup idiosyncracies",
    "reference to afc review",
    '"submission statements" in afc drafts',
    "pre-placed maintenance templates",
    "canned user pages",
    "permissions gaming",
    "miscellaneous",
    "pronounced shift in writing style",
    "biases in content",
    "pro-authoritarian bias",
    "age of text relative to chatgpt launch",
    "ability to explain one's own editorial choices",
    "caveats",
    "ai detection tools",
    "your detection ability",
    "content",
    "language and grammar",
    "style",
    "markup",
    "citations",
    "subtypes",
    "see also",
    "notes",
    "references",
    "further reading",
    "external links",
    "differences between llms",
    "signs of human writing",
    "ineffective indicators",
    "historical indicators",
    "communication intended for the user",
    "broken external links",
    "invalid doi and isbns",
    "dois that lead to unrelated articles",
    "book citations without page numbers or urls",
    "incorrect or unconventional use of references",
}


def _clean_heading(s: str) -> str:
    """Wikitext headings carry anchors, templates and links the rendered TOC does not.

    '<span class="anchor" id="lists"></span>Inline-header vertical lists' and
    'utm_source{{=}}' both have to reduce to what the sections API reports.
    """
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("{{=}}", "=")
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    return s.strip()


def _norm(s: str) -> str:
    """Normalize a section name for comparison: case, quotes, punctuation, spacing."""
    s = _clean_heading(s).strip().strip(".")
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def _paren_free(s: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", s).strip()


def _api(params: dict[str, str]) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read().decode("utf-8"))


def cited_sections() -> dict[str, list[str]]:
    """Guide sections named by rule source_citations, mapped to the rule ids citing them."""
    out: dict[str, list[str]] = {}
    for path in sorted(glob.glob(str(ROOT / "rules" / "*.json"))):
        pack = json.load(open(path, encoding="utf-8"))
        for rule in pack["rules"]:
            for m in CITATION_RE.finditer(rule["source_citation"]):
                out.setdefault(m.group(1).strip().rstrip("."), []).append(rule["id"])
    return out


def live_guide() -> tuple[int, list[dict], dict[str, str]]:
    """Returns (revid, section records, {normalized name: sha256 of its wikitext}).

    Each record carries `line` (display name) and `number` (the TOC path such
    as "3.2.1") so subsection coverage can be inherited from a cited parent.
    """
    meta = _api({"action": "query", "prop": "revisions", "titles": GUIDE_TITLE, "rvprop": "ids"})
    revid = int(meta["query"]["pages"][0]["revisions"][0]["revid"])

    parsed = _api({"action": "parse", "page": GUIDE_TITLE, "prop": "sections"})
    sections = [{"line": _clean_heading(s["line"]), "number": s.get("number", "")} for s in parsed["parse"]["sections"]]

    raw = _api({"action": "parse", "page": GUIDE_TITLE, "prop": "wikitext"})
    text = raw["parse"]["wikitext"]

    # Split the wikitext on its own headings so each section can be hashed
    # independently. A copyedit elsewhere on the page then costs nothing.
    #
    # A section's hash spans its subsections, running to the next heading of
    # the same or shallower level. Parent sections like "Communication intended
    # for the user" have no body of their own, so hashing to the next heading
    # of any level would hash the empty string and never register a change.
    hashes: dict[str, str] = {}
    marks = [(m.start(), m.end(), len(m.group(1)), m.group(2)) for m in HEADING_RE.finditer(text)]
    for i, (_, end, level, title) in enumerate(marks):
        stop = len(text)
        for start_j, _, level_j, _ in marks[i + 1:]:
            if level_j <= level:
                stop = start_j
                break
        body = re.sub(r"\s+", " ", text[end:stop]).strip()
        hashes[_norm(title)] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return revid, sections, hashes


def match_citation(citation: str, live: dict[str, str]) -> str | None:
    """Resolve a citation to a live section name.

    A citation may name a section plus a subpart ("Negative parallelisms, Grok
    notes"), and either side may carry a parenthetical the other lacks
    ("Avoidance of basic copulatives" vs the live '... ("is"/"are" phrases)').
    """
    candidates = [citation, citation.split(",")[0], _paren_free(citation)]
    for cand in candidates:
        if _norm(cand) in live:
            return _norm(cand)
    # Try again ignoring parentheticals on the live side.
    bare = {_paren_free(k): k for k in live}
    for cand in candidates:
        key = _paren_free(_norm(cand))
        if key in bare:
            return bare[key]
    return None


def load_pin() -> dict:
    if PIN_PATH.exists():
        return json.loads(PIN_PATH.read_text(encoding="utf-8"))
    return {"guide_revid": None, "section_hashes": {}}


def main() -> int:
    ap = argparse.ArgumentParser(prog="watch_sources", description=__doc__)
    ap.add_argument("--update-pin", action="store_true", help="re-pin to the current revision after review")
    ap.add_argument("--format", choices=["text", "markdown"], default="text")
    args = ap.parse_args()

    try:
        revid, sections, live = live_guide()
    except (urllib.error.URLError, KeyError, IndexError, ValueError) as exc:
        print(f"ERROR: could not read the guide: {exc}", file=sys.stderr)
        return 2

    pin = load_pin()
    cited = cited_sections()

    stale: list[tuple[str, list[str], str]] = []
    drift: list[tuple[str, list[str]]] = []
    resolved: dict[str, str] = {}

    for citation, rule_ids in sorted(cited.items()):
        key = match_citation(citation, live)
        if key is None:
            close = difflib.get_close_matches(_norm(citation.split(",")[0]), list(live), n=1, cutoff=0.5)
            stale.append((citation, sorted(set(rule_ids)), close[0] if close else "no close match"))
            continue
        resolved[citation] = live[key]
        was = pin.get("section_hashes", {}).get(citation)
        if was is not None and was != live[key]:
            drift.append((citation, sorted(set(rule_ids))))

    # A subsection is covered when an ancestor is cited or out of scope: the
    # three "Not just X, but also Y" subsections belong to "Negative
    # parallelisms", and every "Historical indicators" child inherits from it.
    covered = {match_citation(c, live) for c in cited}
    claimed_numbers = [
        s["number"] for s in sections
        if _norm(s["line"]) in covered or _norm(s["line"]) in OUT_OF_SCOPE
    ]

    def _inherits(number: str) -> bool:
        return any(number != c and number.startswith(c + ".") for c in claimed_numbers if c)

    uncovered = [
        s["line"] for s in sections
        if _norm(s["line"]) not in covered
        and _norm(s["line"]) not in OUT_OF_SCOPE
        and not _inherits(s["number"])
        and _norm(s["line"]) in live
    ]
    names = [s["line"] for s in sections]

    lines: list[str] = []
    bullet = "- " if args.format == "markdown" else "  "
    tick = "`" if args.format == "markdown" else ""

    lines.append(f"Guide revision {revid} (pinned: {pin.get('guide_revid') or 'never'}).")
    lines.append(f"{len(cited)} cited sections, {len(names)} live sections.")
    lines.append("")

    if stale:
        lines.append(f"## STALE citations ({len(stale)})" if args.format == "markdown" else f"STALE ({len(stale)}):")
        for citation, rule_ids, suggestion in stale:
            lines.append(f"{bullet}{tick}{citation}{tick} -> closest live section: {tick}{suggestion}{tick}")
            lines.append(f"{bullet}  cited by: {', '.join(rule_ids)}")
        lines.append("")
    if drift:
        lines.append(f"## DRIFT since pin ({len(drift)})" if args.format == "markdown" else f"DRIFT ({len(drift)}):")
        for citation, rule_ids in drift:
            lines.append(f"{bullet}{tick}{citation}{tick} changed; cited by {', '.join(rule_ids)}")
        lines.append("")
    if uncovered:
        lines.append(
            f"## UNCOVERED guide sections ({len(uncovered)})"
            if args.format == "markdown"
            else f"UNCOVERED ({len(uncovered)}):"
        )
        for n in uncovered:
            lines.append(f"{bullet}{tick}{n}{tick}")
        lines.append("")

    if not (stale or drift or uncovered):
        lines.append("No drift. Every cited section resolves and every scoreable section is covered.")

    report = "\n".join(lines)
    print(report)

    if args.update_pin:
        PIN_PATH.write_text(
            json.dumps({"guide_revid": revid, "section_hashes": resolved}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"\nPinned to revision {revid} with {len(resolved)} section hashes.", file=sys.stderr)
        return 0

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(report + "\n")
    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(f"drift={'true' if (stale or drift or uncovered) else 'false'}\n")

    return 1 if (stale or drift or uncovered) else 0


if __name__ == "__main__":
    raise SystemExit(main())
