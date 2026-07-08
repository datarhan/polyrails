"""Rails — non-custodial async client over the official `polymarket` unified SDK.

The one order path that works for new accounts under the 2026 deposit-wallet
flow: EOA -> derived API creds -> AsyncSecureClient -> setup_gasless_wallet ->
orders signed as the V2 deposit wallet. SDK imports are lazy so importing
polyrails never requires network or the SDK at module load.
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
from dataclasses import dataclass
from typing import Any, Literal

from polyrails.creds import POLYGON_CHAIN_ID, derive_api_creds

logger = logging.getLogger(__name__)

Side = Literal["BUY", "SELL"]


def _default_builder_code() -> str | None:
    return os.environ.get("POLYRAILS_BUILDER_CODE") or None


def conform_tick(price: float, side: Side) -> float:
    """Clamp to the venue's $0.01 tick. A BUY limit is a ceiling -> round UP (a
    marketable limit still crosses and fills at the real ask, no edge lost); a
    SELL limit is a floor -> round DOWN. round() first scrubs float noise
    (0.18*100 -> 18.0000004). For post-only orders pick a clearly-non-crossing
    price; the tick rounding here never moves you more than one cent."""
    raw = round(float(price) * 100, 4)
    cents = math.floor(raw) if side == "SELL" else math.ceil(raw)
    return min(0.99, max(0.01, cents / 100.0))


@dataclass
class OrderResult:
    ok: bool
    status: str
    order_id: str
    making_amount: float   # BUY: USDC offered; SELL: shares offered
    taking_amount: float   # BUY: shares received; SELL: USDC received
    raw: str

    @classmethod
    def from_sdk(cls, resp: Any) -> "OrderResult":
        return cls(
            ok=bool(getattr(resp, "ok", False)),
            status=str(getattr(resp, "status", "") or ""),
            order_id=str(getattr(resp, "order_id", "") or ""),
            making_amount=float(getattr(resp, "making_amount", 0) or 0),
            taking_amount=float(getattr(resp, "taking_amount", 0) or 0),
            raw=str(resp),
        )


class Rails:
    """Connected execution client bound to the caller's V2 deposit wallet."""

    def __init__(self, client: Any, builder_code: str | None):
        self._g = client
        self.builder_code = builder_code

    @classmethod
    async def connect(cls, private_key: str, *, builder_code: str | None = None,
                      chain_id: int = POLYGON_CHAIN_ID) -> "Rails":
        """Derive creds, bind (deploying if needed) the gasless deposit wallet.

        Idempotent: an existing deposit wallet is re-bound, never re-deployed.
        """
        from polymarket import AsyncSecureClient, BuilderApiKey

        loop = asyncio.get_event_loop()
        k, s, p = await loop.run_in_executor(None, derive_api_creds, private_key, chain_id)
        eoa = await AsyncSecureClient.create(
            private_key=private_key,
            api_key=BuilderApiKey(key=k, secret=s, passphrase=p),
        )
        try:
            g = await eoa.setup_gasless_wallet()
        finally:
            await eoa.close()
        code = builder_code or _default_builder_code()
        logger.info("polyrails: bound to deposit wallet %s (type=%s, builder_code=%s)",
                    g.wallet, g.wallet_type, code or "none")
        return cls(g, code)

    # -- account ---------------------------------------------------------

    @property
    def wallet(self) -> str:
        return str(self._g.wallet)

    async def close(self) -> None:
        await self._g.close()

    async def balance(self) -> float:
        """pUSD collateral in the deposit wallet, in dollars."""
        bal = await self._g.get_balance_allowance(asset_type="COLLATERAL")
        raw = float(getattr(bal, "balance", 0) or 0)
        return raw / 1_000_000.0 if raw > 1_000 else raw

    async def open_orders(self, *, token_id: str | None = None,
                          market: str | None = None) -> list[Any]:
        return [o async for o in self._g.list_open_orders(token_id=token_id, market=market)]

    # -- orders ----------------------------------------------------------

    async def limit(self, token_id: str, side: Side, *, price: float, size: float,
                    post_only: bool = False, expiration: int | None = None) -> OrderResult:
        resp = await self._g.place_limit_order(
            token_id=token_id, side=side, price=f"{conform_tick(price, side):.2f}",
            size=str(round(float(size), 2)), post_only=post_only,
            expiration=expiration, builder_code=self.builder_code,
        )
        return OrderResult.from_sdk(resp)

    async def market(self, token_id: str, side: Side, *, amount: float | None = None,
                     shares: float | None = None,
                     order_type: Literal["FAK", "FOK"] = "FAK") -> OrderResult:
        """Marketable order. BUY sizes by `amount` (USDC), SELL by `shares`."""
        resp = await self._g.place_market_order(
            token_id=token_id, side=side, amount=amount, shares=shares,
            order_type=order_type, builder_code=self.builder_code,
        )
        return OrderResult.from_sdk(resp)

    async def cancel(self, order_id: str) -> Any:
        return await self._g.cancel_order(order_id=order_id)

    async def cancel_all(self, order_ids: list[str]) -> Any:
        return await self._g.cancel_orders(order_ids=order_ids)

    # -- builder attribution ----------------------------------------------

    async def builder_fills(self, *, builder_code: str | None = None,
                            market: str | None = None,
                            token_id: str | None = None) -> list[Any]:
        """Fills attributed to a builder code — the ground truth that attribution
        (and therefore rewards eligibility) is actually flowing."""
        code = builder_code or self.builder_code
        if not code:
            raise ValueError("no builder_code configured (POLYRAILS_BUILDER_CODE or connect(builder_code=...))")
        return [t async for t in self._g.list_builder_trades(
            builder_code=code, market=market, token_id=token_id)]
