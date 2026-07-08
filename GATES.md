# Pre-registered validation gates (frozen 2026-07-08, before any build beyond scaffold)

Chosen path: **builder-fee execution product** (see finance-bot session doc
`profit-path-decision-framework.md` for the scored decision). Revenue model:
Polymarket builder program — order attribution earns (a) optional self-set fees
(≤100bps taker / ≤50bps maker, paid by the app's user), (b) a pro-rata share of the
weekly USDC builder rewards pool (~0.5–1% of attributed volume, third-party est.),
(c) grant eligibility. All revenue figures reported ONLY as pUSD actually received.

## Stage 0 — mechanics validation (deadline: +7 days; capital cap: $5)
- [x] S0a Builder profile created, bytes32 builder code obtained (USER action:
      polymarket.com/settings?tab=builder). ✅ 2026-07-08 — profile "polyrails",
      code 0x7885f4b3…d56, fees 0/0, venue-verified via get_builder_fee_rates.
- [x] S0b `canary.py rest`: post-only limit order ACCEPTED carrying our builder_code,
      visible in open orders, cleanly canceled. ($0 spent) ✅ 2026-07-08 on the
      Hormuz-traffic market via the FI VPS.
- [x] S0c `canary.py fill`: one ~$1 marketable fill on a fee-free (geopolitics)
      liquid market; the fill appears under our code via `list_builder_trades`.
      ✅ 2026-07-08 — $1.10 @ 0.59 matched, ATTRIBUTION CONFIRMED
      (size_usdc=1.099998, fee_usdc=0, status=TRADE_STATUS_MATCHED). Learning:
      immediate unwind races on-chain settlement (conditional balance lands
      seconds after match) — sell retried separately.
- [ ] S0d Rewards accrual for the epoch (Sun–Sat) shows > $0 in the builder
      dashboard/API. NOTE: ~$2 of canary volume may round to $0.00 pro-rata —
      if so, S0d stays open until Stage 1 produces non-dust volume; the
      attribution MECHANISM is already proven by S0c.

KILL Stage 0 → abandon path if: attribution never appears on real fills; or the
builder program gates new entrants (the Apr-2026 audit tightening) such that a
solo non-copy-trading tool can't join; or payouts demonstrably don't reach the
profile wallet.

## Stage 1 — product + distribution (deadline: +30 days after S0 pass)
- Ship the OSS package publicly (name/publishing = USER decision) + docs; announce
  in the exact places stuck devs search: the SDK GitHub issue threads, r/Polymarket,
  X. (Outreach posts = USER approval first.)
- GATE at +30d: ≥3 external active users (distinct non-us wallets with attributed
  fills) OR ≥$10k external attributed volume. Below both → STOP building features;
  fix distribution or park the path. Do not rationalize.

## Stage 2 — revenue honesty (rolling)
- Weekly ledger: attributed volume (ours vs external), rewards pUSD RECEIVED,
  self-set fee pUSD RECEIVED. Target: ≥$50/week received by day 60; miss → pivot
  (fold in tape-analytics features — e.g. winner-cohort flow — as the paid layer)
  or park with a written post-mortem.

## Standing rules (non-negotiable, from 71 days of falsification + competitor hacks)
1. Non-custodial ONLY. No server ever sees a user key. (PolyGun −$70k, Polycule
   −$230k precedents.)
2. Own trading capital through these rails capped at $300 until Stage 2 passes.
3. Received-money accounting only; projections never enter the ledger.
4. No prediction strategies get built on top "because we have rails now."
5. User decision points (never unilateral): builder profile creation, wallet
   funding, package name + publishing, any outreach post, any self-set fee > 0bps.
