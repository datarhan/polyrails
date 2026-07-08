"""Stage-1 honest ledger — reads Polymarket's builder-trade ledger for our code
and splits INTERNAL (our own deposit wallet) from EXTERNAL (real third-party
users) attributed volume. This is the ground-truth measurement for the GATES.md
Stage-1 gate (>=3 external users OR >=$10k external attributed volume in 30d) —
the venue's own numbers, not projections.

Run:  POLYMARKET_PRIVATE_KEY=0x... POLYRAILS_BUILDER_CODE=0x... \
      python scripts/ledger.py [--own-wallet 0x2766...]

--own-wallet defaults to the connected deposit wallet (so its own volume is
classified INTERNAL). Everything else is EXTERNAL = the number that counts.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from polyrails import Rails  # noqa: E402


def _key() -> str:
    k = os.environ.get("POLYMARKET_PRIVATE_KEY", "")
    return k or sys.exit("POLYMARKET_PRIVATE_KEY not set")


async def main(own_wallet: str | None) -> None:
    rails = await Rails.connect(_key())
    try:
        if not rails.builder_code:
            sys.exit("no builder code (set POLYRAILS_BUILDER_CODE)")
        own = (own_wallet or rails.wallet).lower()
        trades = await rails.builder_fills()

        internal_vol = external_vol = 0.0
        internal_n = external_n = 0
        ext_wallets: set[str] = set()
        by_ext_wallet: dict[str, float] = defaultdict(float)
        fees = 0.0

        for t in trades:
            usdc = float(getattr(t, "size_usdc", 0) or 0)
            fees += float(getattr(t, "fee_usdc", 0) or 0)
            owner = str(getattr(t, "owner", "") or "").lower()
            if owner == own:
                internal_vol += usdc
                internal_n += 1
            else:
                external_vol += usdc
                external_n += 1
                if owner:
                    ext_wallets.add(owner)
                    by_ext_wallet[owner] += usdc

        print(f"builder code: {rails.builder_code[:12]}…")
        print(f"own wallet (INTERNAL): {own}")
        print("-" * 56)
        print(f"total attributed trades : {len(trades)}")
        print(f"INTERNAL (our bot/canary): {internal_n:>4} trades  ${internal_vol:>10.2f}")
        print(f"EXTERNAL (real users)    : {external_n:>4} trades  ${external_vol:>10.2f}")
        print(f"distinct EXTERNAL wallets: {len(ext_wallets)}")
        print(f"builder fees accrued     : ${fees:.4f}")
        if by_ext_wallet:
            print("\ntop external wallets by volume:")
            for w, v in sorted(by_ext_wallet.items(), key=lambda x: -x[1])[:10]:
                print(f"  {w}  ${v:.2f}")
        print("-" * 56)
        # Stage-1 gate (GATES.md): >=3 external users OR >=$10k external volume
        gate = len(ext_wallets) >= 3 or external_vol >= 10_000
        print(f"STAGE-1 GATE (>=3 ext users OR >=$10k ext vol): "
              f"{'MET' if gate else 'not yet'}  "
              f"[{len(ext_wallets)} users / ${external_vol:.0f}]")
    finally:
        await rails.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--own-wallet", default=None,
                   help="wallet to classify as INTERNAL (default: connected wallet)")
    a = p.parse_args()
    asyncio.run(main(a.own_wallet))
