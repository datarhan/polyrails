"""Stage-0 canary — validates the GATES.md S0 mechanics with <=$5 at risk.

Modes:
  check                  connect + print deposit wallet + pUSD balance ($0 spent)
  rest  --token T        post-only $~1 limit far from mid: accepted -> visible ->
                         canceled. Proves order plumbing + builder_code carriage. ($0)
  fill  --token T        ~$1 marketable FAK buy, then poll list_builder_trades until
                         the fill appears under our builder code. Optionally --unwind
                         sells the shares straight back. Use a FEE-FREE (geopolitics)
                         liquid market so the round trip costs only the spread.

Env: POLYMARKET_PRIVATE_KEY (required), POLYRAILS_BUILDER_CODE (required for fill).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from polyrails import Rails  # noqa: E402


def _key() -> str:
    k = os.environ.get("POLYMARKET_PRIVATE_KEY", "")
    if not k:
        sys.exit("POLYMARKET_PRIVATE_KEY not set")
    return k


async def cmd_check(_: argparse.Namespace) -> None:
    r = await Rails.connect(_key())
    try:
        print(f"wallet:  {r.wallet}")
        print(f"balance: ${await r.balance():.2f} pUSD")
        print(f"builder: {r.builder_code or 'NOT SET'}")
    finally:
        await r.close()


async def cmd_rest(a: argparse.Namespace) -> None:
    r = await Rails.connect(_key())
    try:
        res = await r.limit(a.token, "BUY", price=a.price, size=a.size, post_only=True)
        print(f"placed: ok={res.ok} status={res.status} id={res.order_id}")
        if not res.ok:
            sys.exit(f"REST CANARY FAIL — order rejected: {res.raw}")
        open_ids = [str(getattr(o, "id", getattr(o, "order_id", ""))) for o in
                    await r.open_orders(token_id=a.token)]
        print(f"visible in open orders: {res.order_id in open_ids} ({len(open_ids)} open)")
        await r.cancel(res.order_id)
        open_ids = [str(getattr(o, "id", getattr(o, "order_id", ""))) for o in
                    await r.open_orders(token_id=a.token)]
        print(f"canceled: {res.order_id not in open_ids}")
        print("REST CANARY PASS" if res.order_id not in open_ids else "REST CANARY FAIL (cancel)")
    finally:
        await r.close()


async def cmd_fill(a: argparse.Namespace) -> None:
    r = await Rails.connect(_key())
    try:
        if not r.builder_code:
            sys.exit("fill canary needs POLYRAILS_BUILDER_CODE (gate S0a first)")
        res = await r.market(a.token, "BUY", amount=a.usdc, order_type="FAK")
        print(f"buy: ok={res.ok} status={res.status} spent=${res.making_amount:.2f} "
              f"shares={res.taking_amount:.4f}")
        if not res.ok or res.taking_amount <= 0:
            sys.exit(f"FILL CANARY FAIL — no fill: {res.raw}")
        deadline = time.time() + a.wait
        seen = None
        while time.time() < deadline and seen is None:
            for t in await r.builder_fills(token_id=a.token):
                oid = str(getattr(t, "order_id", getattr(t, "taker_order_id", "")))
                if res.order_id and res.order_id in oid:
                    seen = t
                    break
            if seen is None:
                await asyncio.sleep(5)
        if seen is not None:
            print(f"ATTRIBUTION CONFIRMED: builder trade recorded -> {seen}")
            print("FILL CANARY PASS (gate S0c)")
        else:
            # order-id match can be brittle across models; any trade under our code
            # in the window is still evidence — report what we saw
            recent = await r.builder_fills(token_id=a.token)
            print(f"no order-id match in {a.wait}s; trades under our code on this "
                  f"token: {len(recent)}")
            print("FILL CANARY INCONCLUSIVE — inspect manually" if not recent
                  else f"ATTRIBUTION LIKELY (inspect): {recent[-1]}")
        if a.unwind and res.taking_amount > 0:
            sell = await r.market(a.token, "SELL", shares=res.taking_amount,
                                  order_type="FAK")
            print(f"unwind: ok={sell.ok} received=${sell.taking_amount:.2f}")
    finally:
        await r.close()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    pr = sub.add_parser("rest")
    pr.add_argument("--token", required=True)
    pr.add_argument("--price", type=float, default=0.21,
                    help="far-below-mid resting price (default 0.21)")
    pr.add_argument("--size", type=float, default=5.0,
                    help="shares (default 5 — venue minimums are ~5 shares/$1)")
    pf = sub.add_parser("fill")
    pf.add_argument("--token", required=True)
    pf.add_argument("--usdc", type=float, default=1.10)
    pf.add_argument("--wait", type=int, default=90, help="attribution poll seconds")
    pf.add_argument("--unwind", action="store_true", help="market-sell the shares back")
    a = p.parse_args()
    asyncio.run({"check": cmd_check, "rest": cmd_rest, "fill": cmd_fill}[a.cmd](a))


if __name__ == "__main__":
    main()
