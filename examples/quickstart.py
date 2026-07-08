"""polyrails quickstart: read the market, place a resting order, cancel it.

Run:  POLYMARKET_PRIVATE_KEY=0x... python examples/quickstart.py TOKEN_ID
"""
import asyncio
import os
import sys

from polyrails import Rails

TOKEN = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: quickstart.py TOKEN_ID")


async def main() -> None:
    rails = await Rails.connect(os.environ["POLYMARKET_PRIVATE_KEY"])
    try:
        print(f"wallet   {rails.wallet}")
        print(f"balance  ${await rails.balance():.2f} pUSD")

        mid = await rails.midpoint(TOKEN)
        print(f"midpoint {mid:.3f}  spread {await rails.spread(TOKEN):.3f}")

        # rest a post-only bid 20% below mid (won't cross), then cancel it
        res = await rails.limit(TOKEN, "BUY", price=mid * 0.8, size=5, post_only=True)
        print(f"placed   ok={res.ok} status={res.status} id={res.order_id}")
        if res.ok:
            await rails.cancel(res.order_id)
            print("canceled cleanly")
    finally:
        await rails.close()


asyncio.run(main())
