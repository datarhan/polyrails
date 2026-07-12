#!/bin/bash
# VPS Stage-1 ledger runner — pulls the EOA key via the finance-bot settings
# loader, sets the builder code, and prints the attributed-volume ledger
# (INTERNAL vs EXTERNAL). Invoked over SSH by the Mac watchdog's weekly
# polyrails Stage-1 report. Key never printed.
set -e
cd /root/finance-bot
KEY=$(./.venv/bin/python -c "from config.settings import settings; print(settings.polymarket_wallet_private_key)")
export POLYMARKET_PRIVATE_KEY="$KEY"
export POLYRAILS_BUILDER_CODE="0x7885f4b3b4c42bbee435fc16f66e7679b461610eb080c9985bdd9fdfd1bffd56"
cd /root/polyrails
PYTHONPATH=src exec /root/polyrails/.venv/bin/python scripts/ledger.py "$@"
