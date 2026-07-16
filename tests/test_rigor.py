"""Unit tests for the layer-2 deterministic gap checks: one positive (gap
missed), one negative (gap closed or acknowledged) per check."""

from __future__ import annotations

from core.layer2.rigor import analyze_rigor


def _missed(text: str) -> set[str]:
    return {g.check for g in analyze_rigor(text).gaps}


def _acked(text: str) -> set[str]:
    return {g.check for g in analyze_rigor(text).acknowledged}


class TestContainmentBlastRadius:
    def test_responder_metric_with_impact_framing_fires(self) -> None:
        text = (
            "GitHub revoked 61,274 npm tokens, a number that vividly illustrates "
            "the campaign's devastating blast radius."
        )
        assert "containment-blast-radius" in _missed(text)

    def test_correct_framing_is_acknowledged(self) -> None:
        text = (
            "GitHub removed 640 malicious package versions and revoked 61,274 "
            "tokens. Both are containment actions, not victim counts."
        )
        assert "containment-blast-radius" not in _missed(text)
        assert "containment-blast-radius" in _acked(text)

    def test_responder_units_framed_as_victims_fires(self) -> None:
        text = "In total, 640 malicious package versions were identified as victims of this attack."
        assert "containment-blast-radius" in _missed(text)

    def test_c2_nodes_as_victim_orgs_fires(self) -> None:
        text = "20 additional C2 nodes were discovered, representing 20 confirmed victim organizations."
        assert "containment-blast-radius" in _missed(text)

    def test_neutral_reporting_passes(self) -> None:
        text = "GitHub removed 640 malicious package versions during cleanup."
        assert "containment-blast-radius" not in _missed(text)


class TestAttribution:
    def test_claim_without_basis_fires(self) -> None:
        assert "attribution" in _missed("The campaign is attributed to Actor X.")

    def test_claim_with_weak_basis_fires(self) -> None:
        text = "Attribution is almost certainly to Unit Y, based on targeting patterns and geopolitical alignment."
        assert "attribution" in _missed(text)

    def test_claim_with_strong_basis_passes(self) -> None:
        text = (
            "The campaign is attributed to Actor X based on infrastructure "
            "overlap and code reuse with prior samples."
        )
        assert "attribution" not in _missed(text)

    def test_absence_unaddressed_fires(self) -> None:
        text = "A compromise happened. Malware was deployed. Nothing else is known about who."
        assert "attribution" in _missed(text)

    def test_absence_acknowledged(self) -> None:
        text = "We make no attribution claim; the evidence doesn't narrow the actor set."
        assert "attribution" not in _missed(text)
        assert "attribution" in _acked(text)


class TestNamingContinuity:
    def test_variant_label_without_continuity_fires(self) -> None:
        text = "We call it Mini Hydra, named for its resemblance to the Hydra campaign."
        assert "naming-continuity" in _missed(text)

    def test_acknowledged_label_passes(self) -> None:
        text = (
            "We use Mini Hydra as a variant label on shared tradecraft; operator "
            "continuity isn't established."
        )
        assert "naming-continuity" not in _missed(text)

    def test_continuity_evidence_passes(self) -> None:
        text = "Mini Hydra shares infrastructure with Hydra: the same operator registered both C2 domains."
        assert "naming-continuity" not in _missed(text)


class TestCapabilityVsImpact:
    def test_capability_without_evidence_fires(self) -> None:
        text = "The payload steals credentials across GitHub, AWS, Vault, npm, Kubernetes, and 1Password."
        assert "capability-vs-impact" in _missed(text)

    def test_nearby_evidence_passes(self) -> None:
        text = (
            "The payload steals credentials across GitHub and AWS. Completed exfil "
            "POST bodies were observed and confirmed with two victim teams."
        )
        assert "capability-vs-impact" not in _missed(text)

    def test_acknowledgment_passes(self) -> None:
        text = (
            "The payload steals credentials across GitHub and AWS, though no "
            "exfiltration success evidence exists."
        )
        assert "capability-vs-impact" in _acked(text)


class TestExposureWindow:
    def test_missing_timeline_fires(self) -> None:
        text = "Malicious versions shipped and were eventually removed. A sample was analyzed."
        assert "exposure-window" in _missed(text)

    def test_dated_lifecycle_passes(self) -> None:
        text = (
            "The first malicious version published on 2026-06-30. npm removed the "
            "last affected version on 2026-07-02."
        )
        assert "exposure-window" not in _missed(text)

    def test_weasel_ack_still_fires(self) -> None:
        text = "While specific details regarding the timeline are limited in the available sources, the malware spread."
        assert "exposure-window" in _missed(text)


class TestSampleProvenance:
    def test_unstated_fires(self) -> None:
        text = "We analyzed the payload in depth. The sample decrypts its C2 at runtime."
        assert "sample-provenance" in _missed(text)

    def test_vague_fires(self) -> None:
        text = "We will gather samples from various sources including public repositories."
        assert "sample-provenance" in _missed(text)

    def test_stated_passes(self) -> None:
        text = "We pulled the sample from the npm registry and verified its hash against the manifest."
        assert "sample-provenance" not in _missed(text)


class TestDetectionValidation:
    def test_untested_fires(self) -> None:
        text = "The hunting queries ship ready to deploy for common SIEM platforms."
        assert "detection-validation" in _missed(text)

    def test_circular_fires(self) -> None:
        text = "Validation: test the detections against the known IOCs, specifically the hash and the C2 domain."
        gaps = analyze_rigor(text).gaps
        assert any(g.id == "detection-validation-circular" for g in gaps)

    def test_validated_passes(self) -> None:
        text = (
            "The hunting queries were tested against 30 days of CI telemetry; the "
            "false-positive rate was 0.4 percent with a negative corpus of benign packages."
        )
        assert "detection-validation" not in _missed(text)


class TestConfidenceLanguage:
    def test_stacked_terms_fire(self) -> None:
        result = analyze_rigor("The actor could possibly almost certainly continue operations.")
        assert result.incoherent_stacks
        assert any(g.check == "confidence-language" for g in result.gaps)

    def test_icd_terms_recorded(self) -> None:
        result = analyze_rigor("It is likely the actor returns; a second campaign is almost certainly staged.")
        assert "likely" in result.icd203_terms
        assert not result.incoherent_stacks


class TestIocDurability:
    def test_value_weighted_fires(self) -> None:
        text = (
            "IOCs: evil1[.]com, evil2[.]net, evil3[.]org, 10.1.1[.]1, "
            "d41d8cd98f00b204e9800998ecf8427e, dropper.exe, and stage2.js were compromised."
        )
        result = analyze_rigor(text)
        assert result.value_weighted

    def test_behavior_weighted_passes(self) -> None:
        text = (
            "Hunt the behaviors: preinstall hooks spawning shells, Runner.Worker "
            "memory scraping, sudoers bind-mount writes, OIDC exchange, and "
            "Sigstore calls. The single domain evil[.]com is expiring enrichment."
        )
        result = analyze_rigor(text)
        assert not result.value_weighted
        assert len(result.behaviors) >= 4


class TestVictimAndMotive:
    def test_unquantified_victims_fire(self) -> None:
        text = "The campaign compromised build systems and stole credentials at scale."
        assert "victim-quantification" in _missed(text)

    def test_quantified_passes(self) -> None:
        text = "The campaign compromised build systems; three confirmed victim organizations were verified."
        assert "victim-quantification" not in _missed(text)

    def test_motive_unexamined_fires(self) -> None:
        text = "The payload is a credential stealer harvesting tokens and secrets."
        assert "motive" in _missed(text)

    def test_motive_discussed_passes(self) -> None:
        text = (
            "The payload harvests credentials and secrets. The motive we can "
            "evidence is theft; we checked for resale staging."
        )
        assert "motive" not in _missed(text)
