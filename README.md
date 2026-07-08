# polyrails

**The Polymarket CLOB V2 execution layer that works.**

Since the 2026 deposit-wallet migration, new accounts get `400 "maker address not
allowed"` / `"invalid order version"` from the legacy SDK paths most tutorials still
show ([py-clob-client-v2 #70](https://github.com/Polymarket/py-clob-client-v2/issues/70)
and friends). The working path is the official unified `polymarket` SDK over the
**gasless deposit-wallet flow** — but wiring it correctly (EOA → derived API creds →
`AsyncSecureClient` → `setup_gasless_wallet` → orders) is undocumented folklore.

`polyrails` is that folklore, packaged: **private key in, working orders out.**

```python
import asyncio
from polyrails import Rails

async def main():
    r = await Rails.connect(private_key="0x...")      # no website, no manual API keys
    print(r.wallet, await r.balance())                # your V2 deposit wallet + pUSD balance
    res = await r.limit("TOKEN_ID", "BUY", price=0.42, size=10)
    print(res.ok, res.order_id)
    await r.close()

asyncio.run(main())
```

## What it does

- **Derives API credentials from your EOA** — no dashboard visit needed.
- **Binds your V2 Deposit Wallet** (idempotent) and signs orders for it —
  the only order path the venue accepts for fresh accounts since July 2026.
- Limit (incl. post-only) + market (FAK/FOK) orders, cancels, open orders, balances.
- Market data: `midpoint()`, `price()`, `spread()`, `book()`.
- Price ticks conformed automatically (BUY rounds up as a marketable ceiling,
  SELL rounds down — you never lose edge to a tick rejection).
- Attribution verification built in: `builder_fills()` returns the venue's own
  ledger of trades credited to a builder code.
- Clear, honest errors instead of cryptic 400s.

## What it never does

- **Never custodies keys or funds.** Your key stays in your process, used only for
  local signing. There is no polyrails server. (The two biggest hosted Polymarket
  bots were hacked for −$70k and −$230k in 2026. Architecture is the fix: there is
  nothing here to hack.)
- Never places an order you didn't call for.

## Funding disclosure

Orders placed through polyrails carry a **builder attribution code** — a public
identifier in the signed order (that's Polymarket's official
[Builder Program](https://docs.polymarket.com/builders/overview)). Attribution
costs you **nothing**: polyrails sets no builder fee (0 bps, verifiable on-chain
per order); the code only routes a share of Polymarket's builder rewards pool to
whoever's code is attached. That's how free, non-custodial open source stays
maintained.

Resolution order: `Rails.connect(builder_code=...)` → `POLYRAILS_BUILDER_CODE`
env → the maintainer's code (`polyrails`,
`0x7885f4b3b4c42bbee435fc16f66e7679b461610eb080c9985bdd9fdfd1bffd56`).
Registered builder? Pass your own code and keep the rewards. Want no
attribution at all? Set `builder_code=""` (or env `POLYRAILS_BUILDER_CODE=off`).

## Status

v0.1 — extracted from a private trading system and validated end-to-end on the
live venue (order lifecycle + attribution CONFIRMED on the builder ledger; the
whole validation cost $0.02). Gates and roadmap: [GATES.md](GATES.md),
[CHANGELOG.md](CHANGELOG.md).

## Install

```
pip install polyrails
```

Requires Python ≥ 3.11. MIT licensed.
