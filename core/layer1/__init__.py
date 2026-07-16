"""Layer 1: deterministic lexical and structural fingerprint."""

from core.layer1.checks import CHECKS
from core.layer1.fingerprint import FingerprintResult, analyze_fingerprint

__all__ = ["CHECKS", "FingerprintResult", "analyze_fingerprint"]
