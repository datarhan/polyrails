#!/bin/bash
# VPS canary runner — pulls the EOA key through the finance-bot settings loader
# (canonical parsing; key never printed) and execs the canary with it.
set -e
cd /root/finance-bot
KEY=$(./.venv/bin/python -c "from config.settings import settings; print(settings.polymarket_wallet_private_key)")
echo "key format (via bot settings): len=${#KEY} prefix=${KEY:0:2}"
export POLYMARKET_PRIVATE_KEY="$KEY"
cd /root/polyrails
PYTHONPATH=src exec /root/polyrails/.venv/bin/python scripts/canary.py "$@"
