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
- **Deploys/binds your V2 deposit wallet** (idempotent) and signs orders as it —
  the only order path that works for fresh accounts in 2026.
- Limit (incl. post-only) + market (FAK/FOK) orders, cancels, open orders, balances.
- Price ticks conformed automatically (BUY rounds up as a marketable ceiling,
  SELL rounds down — you never lose edge to a tick rejection).
- Clear, honest errors instead of cryptic 400s.

## What it never does

- **Never custodies keys or funds.** Your key stays in your process, used only for
  local signing. There is no polyrails server. (The two biggest hosted Polymarket
  bots were hacked for −$70k and −$230k in 2026. Architecture is the fix: there is
  nothing here to hack.)
- Never places an order you didn't call for.

## Funding disclosure

Orders placed through polyrails carry a builder attribution code
(`POLYRAILS_BUILDER_CODE` env or `Rails.connect(builder_code=...)`; defaults to the
maintainer's code when unset). Attribution costs you **nothing** — it routes a share
of Polymarket's builder rewards pool to whoever's code is attached. That's how free,
non-custodial open source stays maintained. Set your own code to keep the rewards;
leave the default to support the project.

## Status

v0.1 — extracted from a private trading system with real on-chain fill history on
these exact rails. Validation gates and the roadmap live in [GATES.md](GATES.md).

## Install

```
pip install polyrails        # (not yet published — build from source for now)
```

Requires Python ≥ 3.11.
