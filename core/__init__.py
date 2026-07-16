"""stopslop: analytic-rigor scorer for threat intelligence writing.

Design constraint, from Wikipedia:Signs of AI writing (WikiProject AI Cleanup):
the signs are not the problem, they point at the problem. Layer 1 fingerprints
are supporting signals only. Layer 2 analytic rigor is the product. No layer
emits a verdict on its own, and nothing in this package emits a slop boolean.
"""

__version__ = "2.0.0"

USER_AGENT = f"stopslop/{__version__} (+https://github.com/haKC-ai/stopslop)"
