"""Layer 2: analytic rigor. Deterministic gap detection first, LLM second.

The LLM never moves a score. If a provider is unreachable, the deterministic
output stands alone and says so.
"""

from core.layer2.rigor import Gap, RigorResult, analyze_rigor

__all__ = ["Gap", "RigorResult", "analyze_rigor"]
