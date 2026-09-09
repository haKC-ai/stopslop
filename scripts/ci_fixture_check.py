#!/usr/bin/env python3
"""CI gate: run the tool against both golden fixtures and assert the outputs.

Exits nonzero if the gap-laden fixture doesn't surface its gaps or the
well-sourced fixture isn't clean. This is the 'if the tool can't tell them
apart, it doesn't work' check, run against the real CLI, not the test suite.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_cli(source: pathlib.Path, out: pathlib.Path) -> dict:
    subprocess.run(
        [sys.executable, "-m", "core.cli", "--file", str(source), "--no-llm",
         "--rules-dir", str(ROOT / "rules"), "--out", str(out)],
        cwd=ROOT, check=True, capture_output=True,
    )
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        mini = run_cli(ROOT / "tests/fixtures/mini-shai-hulud/source.md", tmp / "mini.json")
        well = run_cli(ROOT / "tests/fixtures/well-sourced/source.md", tmp / "well.json")
        narrative = run_cli(ROOT / "tests/fixtures/corpus/fixture-narrative.md", tmp / "narrative.json")
        clean = run_cli(ROOT / "tests/fixtures/corpus/fixture-clean.md", tmp / "clean.json")

    expected = json.loads(
        (ROOT / "tests/fixtures/mini-shai-hulud/expected_gaps.json").read_text(encoding="utf-8")
    )
    mini_checks = {g["check"] for g in mini["rigor"]["gaps"]}
    missing = [c for c in expected["required_missed_checks"] if c not in mini_checks]
    if missing:
        print(f"FAIL: mini-shai-hulud did not surface: {missing}")
        return 1

    containment = [g for g in mini["rigor"]["gaps"] if g["check"] == "containment-blast-radius"]
    if len(containment) < expected["containment_min_hits"]:
        print("FAIL: containment-vs-blast-radius split missing on the two large numbers")
        return 1

    well_missed = [g["id"] for g in well["rigor"]["gaps"]]
    if well_missed:
        print(f"FAIL: well-sourced fixture is not clean: {well_missed}")
        return 1

    for report, name in ((mini, "mini"), (well, "well"), (narrative, "narrative"), (clean, "clean")):
        flat = json.dumps(report)
        if "is_slop" in flat:
            print(f"FAIL: {name} report contains a verdict boolean")
            return 1

    # The 2025-2026 conversational register pair: the chat-register writeup must
    # be called, and the human-written control must not move because of it.
    narrative_era = narrative["fingerprint"]["era_estimate"]
    if narrative_era["era"] != "chat2026":
        print(f"FAIL: narrative fixture era is {narrative_era['era']!r}, expected 'chat2026'")
        return 1
    if clean["fingerprint"]["score"]["net"] != 0.0:
        print(f"FAIL: register rules taxed the human control (net {clean['fingerprint']['score']['net']})")
        return 1
    if clean["fingerprint"]["era_estimate"]["era"] != "none":
        print("FAIL: human control got an era call")
        return 1

    print(
        f"OK: mini surfaces {len(mini['rigor']['gaps'])} gaps, well-sourced surfaces 0, "
        f"narrative reads {narrative_era['era']}, human control stays at 0."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
