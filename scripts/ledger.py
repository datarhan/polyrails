"""Stage-1 honest ledger — reads Polymarket's builder-trade ledger for our code
and splits INTERNAL (our own account) from EXTERNAL (real third-party users)
attributed volume. This is the ground-truth measurement for the GATES.md
Stage-1 gate (>=3 external users OR >=$10k external attributed volume in 30d) —
the venue's own numbers, not projections.

CLASSIFICATION: builder trades identify the trader by `owner`, a Polymarket
ACCOUNT UUID (e.g. 9d8d300f-…) — NOT the on-chain wallet address. So INTERNAL is
keyed on our account's owner-UUID(s), not the 0x wallet. Our own bot/canary
trades all carry our owner-UUID; anything else is a real external user.

Run:  POLYMARKET_PRIVATE_KEY=0x... POLYRAILS_BUILDER_CODE=0x... \
      python scripts/ledger.py [--own-owner-id UUID ...]

Own owner-UUIDs default to the built-in known id + anything in the
POLYRAILS_OWN_OWNER_IDS env (comma-separated); --own-owner-id adds more.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from polyrails import Rails  # noqa: E402

# Our Polymarket account UUID (the deposit wallet 0x2766…825f), captured from the
# 2026-07-08 canary builder trades. Bot + canary trades all carry this owner id.
KNOWN_OWN_OWNER_IDS = {"9d8d300f-7b32-c0a0-86c1-538e86966bdb"}


def own_owner_ids(extra: list[str] | None = None) -> set[str]:
    ids = set(KNOWN_OWN_OWNER_IDS)
    env = os.environ.get("POLYRAILS_OWN_OWNER_IDS", "")
    ids |= {x.strip().lower() for x in env.split(",") if x.strip()}
    ids |= {x.strip().lower() for x in (extra or []) if x.strip()}
    return {i.lower() for i in ids}


def classify(trades, own_ids: set[str]) -> dict:
    """Pure split of builder trades into internal vs external by owner-UUID."""
    own = {i.lower() for i in own_ids}
    r = {"internal_vol": 0.0, "internal_n": 0, "external_vol": 0.0,
         "external_n": 0, "ext_owners": set(), "by_ext_owner": defaultdict(float),
         "fees": 0.0}
    for t in trades:
        usdc = float(getattr(t, "size_usdc", 0) or 0)
        r["fees"] += float(getattr(t, "fee_usdc", 0) or 0)
        owner = str(getattr(t, "owner", "") or "").lower()
        if owner in own:
            r["internal_vol"] += usdc
            r["internal_n"] += 1
        else:
            r["external_vol"] += usdc
            r["external_n"] += 1
            if owner:
                r["ext_owners"].add(owner)
                r["by_ext_owner"][owner] += usdc
    return r


async def main(extra_ids: list[str]) -> None:
    rails = await Rails.connect(_key())
    try:
        if not rails.builder_code:
            sys.exit("no builder code (set POLYRAILS_BUILDER_CODE)")
        own = own_owner_ids(extra_ids)
        trades = await rails.builder_fills()
        r = classify(trades, own)

        print(f"builder code: {rails.builder_code[:12]}…   wallet: {rails.wallet}")
        print(f"INTERNAL owner-ids: {sorted(own)}")
        print("-" * 60)
        print(f"total attributed trades : {len(trades)}")
        print(f"INTERNAL (our bot/canary): {r['internal_n']:>4} trades  ${r['internal_vol']:>10.2f}")
        print(f"EXTERNAL (real users)    : {r['external_n']:>4} trades  ${r['external_vol']:>10.2f}")
        print(f"distinct EXTERNAL users  : {len(r['ext_owners'])}")
        print(f"builder fees accrued     : ${r['fees']:.4f}")
        if r["by_ext_owner"]:
            print("\ntop external users by volume:")
            for w, v in sorted(r["by_ext_owner"].items(), key=lambda x: -x[1])[:10]:
                print(f"  {w}  ${v:.2f}")
        print("-" * 60)
        gate = len(r["ext_owners"]) >= 3 or r["external_vol"] >= 10_000
        print(f"STAGE-1 GATE (>=3 ext users OR >=$10k ext vol): "
              f"{'MET' if gate else 'not yet'}  "
              f"[{len(r['ext_owners'])} users / ${r['external_vol']:.0f}]")
    finally:
        await rails.close()


def _key() -> str:
    k = os.environ.get("POLYMARKET_PRIVATE_KEY", "")
    return k or sys.exit("POLYMARKET_PRIVATE_KEY not set")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--own-owner-id", action="append", default=[],
                   help="additional account owner-UUID(s) to classify as INTERNAL")
    a = p.parse_args()
    asyncio.run(main(a.own_owner_id))
