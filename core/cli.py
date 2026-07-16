"""stopslop CLI: fingerprint + analytic rigor over text, file, or URL."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from dotenv import load_dotenv

from core import __version__
from core.config import RuntimeConfig
from core.extractors.file_ingest import extract_text_from_file
from core.extractors.url_fetcher import fetch_url
from core.layer1.checks import CHECKS as LAYER1_CHECKS
from core.layer1.fingerprint import analyze_fingerprint
from core.layer2.auditor import UNAVAILABLE_NOTE, run_audit
from core.layer2.hygiene import HYGIENE_CHECKS
from core.layer2.rigor import Gap, analyze_rigor
from core.layer3.provenance import ProvenanceEnvelope, load_envelope, provenance_section
from core.normalizers.text_clean import normalize_text
from core.render.markdown import render_markdown
from core.report import build_report
from core.rules.engine import run_rules
from core.rules.loader import load_rules_dir
from core.rules.model import Finding
from core.textmodel import word_count

ALL_CHECKS = {**LAYER1_CHECKS, **HYGIENE_CHECKS}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="stopslop",
        description="Analytic-rigor scorer for threat intelligence writing.",
    )
    p.add_argument("--version", action="version", version=f"stopslop {__version__}")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="URL to analyze")
    src.add_argument("--file", help="file path to analyze")
    src.add_argument("--stdin", action="store_true", help="read text from stdin")
    p.add_argument("--rules-dir", default="rules", help="directory of JSON rule packs")
    p.add_argument(
        "--providers",
        nargs="*",
        default=None,
        help="LLM providers for the auditor: anthropic openai gemini (default: whichever have keys)",
    )
    p.add_argument("--no-llm", action="store_true", help="deterministic layers only")
    p.add_argument("--provenance", help="path to a provenance envelope JSON")
    p.add_argument("--word-budget", type=int, default=None, help="hard cap on generated section words")
    p.add_argument("--out", help="write the JSON report here")
    p.add_argument("--md-out", help="write the Markdown rendering here")
    p.add_argument("--format", choices=["json", "md"], default="json", help="what to print to stdout")
    return p.parse_args(argv)


def hygiene_findings_to_gaps(findings: list[Finding]) -> list[Gap]:
    gaps: list[Gap] = []
    for f in findings:
        gaps.append(
            Gap(
                id=f"hygiene-{f.rule_id}",
                check="indicator-hygiene",
                severity="medium",
                status="missed",
                description=f"{f.details}" if f.details else f.rule_id,
                spans=f.spans,
            )
        )
    return gaps


def analyze(
    text: str,
    source_meta: dict[str, Any],
    rules_dir: str,
    cfg: RuntimeConfig,
    providers: list[str] | None = None,
    envelope: ProvenanceEnvelope | None = None,
    word_budget: int | None = None,
) -> dict[str, Any]:
    """Full pipeline over already-normalized text. Importable for tests and embedding."""
    rules, rules_version = load_rules_dir(rules_dir, frozenset(ALL_CHECKS))
    findings = run_rules(text, rules, ALL_CHECKS)
    layer1_findings = [f for f in findings if _rule_layer(rules, f.rule_id) == 1]
    layer2_findings = [f for f in findings if _rule_layer(rules, f.rule_id) == 2]

    fingerprint = analyze_fingerprint(text, layer1_findings)
    rigor = analyze_rigor(text)
    rigor.gaps.extend(hygiene_findings_to_gaps(layer2_findings))

    budget = word_budget
    if budget is None and envelope is not None:
        budget = envelope.word_budget

    deterministic_summary: dict[str, Any] = {
        "fingerprint": fingerprint.to_dict(),
        "rigor": rigor.to_dict(),
    }
    if providers:
        llm_audit = run_audit(text, deterministic_summary, cfg, providers, budget)
    else:
        llm_audit = {"available": False, "note": UNAVAILABLE_NOTE}

    words_used: int | None = None
    if llm_audit.get("available"):
        words_used = word_count(str(llm_audit["critical_review"])) + word_count(
            str(llm_audit["proposed_research"])
        )
    provenance = provenance_section(envelope, words_used)
    return build_report(
        content=text,
        source_meta=source_meta,
        fingerprint=fingerprint,
        rigor=rigor,
        llm_audit=llm_audit,
        provenance=provenance,
        rules_version=rules_version,
        word_budget=budget,
        words_used=words_used,
    )


def _rule_layer(rules: list[Any], rule_id: str) -> int:
    for r in rules:
        if r.id == rule_id:
            return int(r.layer)
    return 1


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    cfg = RuntimeConfig()

    if args.url:
        text, meta = fetch_url(args.url, timeout_sec=cfg.timeout_sec, block_private_ips=cfg.block_private_ips)
    elif args.file:
        text, meta = extract_text_from_file(args.file)
    else:
        text = sys.stdin.read()
        meta = {"source": "stdin"}
    text = normalize_text(text, cfg.max_chars)

    envelope = load_envelope(args.provenance) if args.provenance else None
    providers: list[str] | None
    if args.no_llm:
        providers = None
    elif args.providers is not None:
        providers = list(args.providers)
    else:
        providers = cfg.providers_available

    report = analyze(
        text,
        meta,
        args.rules_dir,
        cfg,
        providers=providers,
        envelope=envelope,
        word_budget=args.word_budget,
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    if args.md_out:
        with open(args.md_out, "w", encoding="utf-8") as f:
            f.write(render_markdown(report))
    if args.format == "md":
        print(render_markdown(report))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
