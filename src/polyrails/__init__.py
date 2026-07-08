"""polyrails — the Polymarket CLOB V2 execution layer that works.

Non-custodial: your private key never leaves your process. Every order can carry
a builder attribution code (see README "Funding disclosure").
"""
from polyrails.client import OrderResult, Rails

__all__ = ["Rails", "OrderResult"]
__version__ = "0.1.0"
