"""API-credential derivation from a bare EOA private key — no website visit.

The unified `polymarket` SDK authenticates with a (key, secret, passphrase)
triple. Polymarket derives these deterministically from an EOA signature, so a
fresh wallet can mint its own credentials via the CLOB API. A dedicated builder
key is preferred when the venue grants one; the standard L2 key works otherwise.
"""
from __future__ import annotations

import logging

CLOB_HOST = "https://clob.polymarket.com"
POLYGON_CHAIN_ID = 137

logger = logging.getLogger(__name__)


def derive_api_creds(private_key: str, chain_id: int = POLYGON_CHAIN_ID,
                     host: str = CLOB_HOST) -> tuple[str, str, str]:
    """Return (api_key, secret, passphrase) for `private_key`. Sync + blocking.

    `create_or_derive_api_key` logs an EXPECTED 400 at ERROR level when the key
    already exists (it then derives it); that SDK logger is quieted for the call.
    """
    from py_clob_client_v2 import ClobClient

    sdk_log = logging.getLogger("py_clob_client_v2.http_helpers.helpers")
    prev = sdk_log.level
    sdk_log.setLevel(logging.CRITICAL)
    try:
        c = ClobClient(host=host, chain_id=chain_id, key=private_key)
        l2 = c.create_or_derive_api_key()
        c.set_api_creds(l2)
        try:
            resp = c.create_builder_api_key()
            if isinstance(resp, dict):
                k = resp.get("apiKey") or resp.get("api_key") or resp.get("key")
                s = resp.get("secret") or resp.get("api_secret")
                p = resp.get("passphrase") or resp.get("api_passphrase")
                if k and s and p:
                    return k, s, p
        except Exception as e:  # builder-key mint can be venue-gated; L2 works
            logger.debug("create_builder_api_key unavailable (%r); using L2 key", e)
        return l2.api_key, l2.api_secret, l2.api_passphrase
    finally:
        sdk_log.setLevel(prev)
