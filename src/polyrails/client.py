"""Rails — non-custodial async client over the official `polymarket` unified SDK.

The one order path that works for new accounts under the 2026 deposit-wallet
flow: `AsyncSecureClient.create(private_key)` — the SDK (>=0.1.0b16) derives
API credentials and binds the signer's Deposit Wallet itself. Do NOT use the
older two-step flow (manual cred derivation + `setup_gasless_wallet`): since
~2026-07-01 the venue rejects its orders with "the order signer address has
to be the address of the API KEY". SDK imports are lazy so importing polyrails
never requires network or the SDK at module load.
"""
from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

Side = Literal["BUY", "SELL"]


# Maintainer's builder code — the package's default order attribution (public
# identifier; see README "Funding disclosure"). Override precedence:
# connect(builder_code=...) > POLYRAILS_BUILDER_CODE env > this default.
# Pass builder_code="" (or set the env var to "off") to disable attribution.
MAINTAINER_BUILDER_CODE = (
    "0x7885f4b3b4c42bbee435fc16f66e7679b461610eb080c9985bdd9fdfd1bffd56"
)


def resolve_builder_code(arg: str | None) -> str | None:
    """Resolve the builder code for a connection. `""` or `"off"` (arg or env)
    disables attribution entirely; None falls through env -> maintainer default."""
    if arg is not None:
        return arg or None
    env = os.environ.get("POLYRAILS_BUILDER_CODE")
    if env is not None:
        env = env.strip()
        return None if env in ("", "off") else env
    return MAINTAINER_BUILDER_CODE


async def _drain(paginator: Any) -> list[Any]:
    """Flatten an SDK AsyncPaginator: iteration yields Page objects (with an
    `.items` tuple), so collect page items — not the pages themselves."""
    out: list[Any] = []
    async for page in paginator:
        items = getattr(page, "items", None)
        if items is not None:
            out.extend(items)
        else:  # future-proof: some paginators may yield raw items
            out.append(page)
    return out


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
                      wallet: str | None = None) -> "Rails":
        """Create an authenticated client acting for the signer's Deposit Wallet
        (or an explicit `wallet`). Credential derivation is handled by the SDK;
        idempotent across reconnects."""
        from polymarket import AsyncSecureClient

        g = await AsyncSecureClient.create(private_key=private_key, wallet=wallet)
        code = resolve_builder_code(builder_code)
        logger.info("polyrails: acting for wallet %s (type=%s, builder_code=%s)",
                    getattr(g, "wallet", "?"), getattr(g, "wallet_type", "?"),
                    code or "none")
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
        return await _drain(self._g.list_open_orders(token_id=token_id, market=market))

    # -- market data -------------------------------------------------------

    async def midpoint(self, token_id: str) -> float:
        return float(await self._g.get_midpoint(token_id=token_id))

    async def price(self, token_id: str, side: Side) -> float:
        """Best price to trade `side` right now (BUY -> ask, SELL -> bid)."""
        return float(await self._g.get_price(token_id=token_id, side=side))

    async def spread(self, token_id: str) -> float:
        return float(await self._g.get_spread(token_id=token_id))

    async def book(self, token_id: str) -> Any:
        return await self._g.get_order_book(token_id=token_id)

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
        return await _drain(self._g.list_builder_trades(
            builder_code=code, market=market, token_id=token_id))
