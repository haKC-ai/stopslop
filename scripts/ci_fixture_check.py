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

    for report, name in ((mini, "mini"), (well, "well")):
        flat = json.dumps(report)
        if "is_slop" in flat:
            print(f"FAIL: {name} report contains a verdict boolean")
            return 1

    print(f"OK: mini surfaces {len(mini['rigor']['gaps'])} gaps, well-sourced surfaces 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
