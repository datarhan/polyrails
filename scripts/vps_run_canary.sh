#!/bin/bash
# VPS canary runner — pulls the EOA key through the finance-bot settings loader
# (canonical parsing; key never printed) and execs the canary with it.
set -e
cd /root/finance-bot
KEY=$(./.venv/bin/python -c "from config.settings import settings; print(settings.polymarket_wallet_private_key)")
echo "key format (via bot settings): len=${#KEY} prefix=${KEY:0:2}"
export POLYMARKET_PRIVATE_KEY="$KEY"
# polyrails builder code — PUBLIC identifier (appears onchain in every attributed
# order); profile "polyrails", created 2026-07-08
export POLYRAILS_BUILDER_CODE="0x7885f4b3b4c42bbee435fc16f66e7679b461610eb080c9985bdd9fdfd1bffd56"
cd /root/polyrails
PYTHONPATH=src exec /root/polyrails/.venv/bin/python scripts/canary.py "$@"
