"""polyrails — the Polymarket CLOB V2 execution layer that works.

Non-custodial: your private key never leaves your process. Every order can carry
a builder attribution code (see README "Funding disclosure").
"""
from polyrails.client import OrderResult, Rails
from polyrails.creds import derive_api_creds

__all__ = ["Rails", "OrderResult", "derive_api_creds"]
__version__ = "0.1.0"
