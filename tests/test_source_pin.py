"""The source pin must stay in step with the rules, offline.

scripts/watch_sources.py talks to Wikipedia, so it can't run in the test suite.
These checks are the offline half: every guide section a rule cites has to be
present in .rule-sources.json. That catches the realistic mistake, which is
adding a rule with a new or reworded citation and never re-pinning, leaving the
patrol blind to that section forever.
"""

from __future__ import annotations

import json

from tests.conftest import REPO_ROOT

PIN_PATH = REPO_ROOT / ".rule-sources.json"


def _pin() -> dict:
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


def test_pin_exists_and_names_a_revision() -> None:
    pin = _pin()
    assert isinstance(pin["guide_revid"], int)
    assert pin["section_hashes"], "pin carries no section hashes"


def test_every_cited_guide_section_is_pinned() -> None:
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from watch_sources import cited_sections

    pinned = set(_pin()["section_hashes"])
    missing = sorted(set(cited_sections()) - pinned)
    assert not missing, (
        f"rules cite guide sections the pin does not cover: {missing}. "
        "Run: python scripts/watch_sources.py --update-pin"
    )


def test_pin_carries_no_empty_digests() -> None:
    """A parent section whose body is entirely subsections used to hash the
    empty string, so drift there could never fire."""
    import hashlib

    empty = hashlib.sha256(b"").hexdigest()
    offenders = [k for k, v in _pin()["section_hashes"].items() if v == empty]
    assert not offenders, f"sections hashed to the empty digest: {offenders}"


def test_no_pinned_section_is_orphaned() -> None:
    """The pin should not accumulate sections no rule cites any more."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from watch_sources import cited_sections

    orphans = sorted(set(_pin()["section_hashes"]) - set(cited_sections()))
    assert not orphans, (
        f"pin covers sections no rule cites: {orphans}. "
        "Run: python scripts/watch_sources.py --update-pin"
    )
