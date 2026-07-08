# Changelog

## 0.1.0 — 2026-07-08

First release. Validated end-to-end on the live venue (attributed fills
CONFIRMED on Polymarket's builder ledger; see GATES.md).

- `Rails.connect(private_key)` — non-custodial connection over the official
  `polymarket` unified SDK (>=0.1.0b16): credentials derived from your EOA,
  bound to your V2 Deposit Wallet. No dashboard visit, no manual API keys.
- Orders: `limit()` (incl. post-only, auto tick-conform), `market()` (FAK/FOK),
  `cancel()` / `cancel_all()`, `open_orders()`.
- Market data: `midpoint()`, `price()`, `spread()`, `book()`.
- Builder attribution on every order (`builder_code` resolution:
  explicit arg > `POLYRAILS_BUILDER_CODE` env > maintainer default; `""`/`off`
  disables). `builder_fills()` returns the venue's attributed-trade ledger.
- Canary scripts (`scripts/canary.py`): `check` / `rest` / `fill` / `sell` /
  `attributed` — validate the full chain with ≤$5 at risk.

Known venue facts this release encodes (July 2026):

- The pre-July two-step flow (manual cred derivation + `setup_gasless_wallet`)
  is rejected by the venue ("order signer address has to be the address of the
  API KEY"). Use `AsyncSecureClient.create()` semantics — polyrails does.
- SDK list endpoints paginate with `Page` objects; polyrails flattens them.
- A SELL immediately after a matched BUY can race on-chain settlement
  (conditional balance lands seconds later) — retry briefly.
