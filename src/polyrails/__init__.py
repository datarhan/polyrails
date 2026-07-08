"""polyrails — the Polymarket CLOB V2 execution layer that works.

Non-custodial: your private key never leaves your process. Every order can carry
a builder attribution code (see README "Funding disclosure").
"""
from polyrails.client import (
    MAINTAINER_BUILDER_CODE,
    OrderResult,
    Rails,
    resolve_builder_code,
)

__all__ = ["Rails", "OrderResult", "MAINTAINER_BUILDER_CODE", "resolve_builder_code"]
__version__ = "0.1.0"
