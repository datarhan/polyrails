"""Ledger classification tests — the Stage-1 gate hinges on splitting our own
trades (owner-UUID) from real external users. Locked because a wrong split
(e.g. keying on wallet address, which the `owner` field is NOT) silently
overcounts external adoption."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ledger import KNOWN_OWN_OWNER_IDS, classify, own_owner_ids  # noqa: E402


class _T:
    def __init__(self, owner, size_usdc, fee_usdc=0):
        self.owner = owner
        self.size_usdc = size_usdc
        self.fee_usdc = fee_usdc


OWN = next(iter(KNOWN_OWN_OWNER_IDS))


def test_own_owner_id_trades_are_internal():
    r = classify([_T(OWN, 1.10), _T(OWN.upper(), 1.08)], {OWN})
    assert r["internal_n"] == 2
    assert abs(r["internal_vol"] - 2.18) < 1e-9
    assert r["external_n"] == 0 and len(r["ext_owners"]) == 0


def test_external_users_counted_once_per_owner():
    r = classify([
        _T(OWN, 5.0),                     # ours
        _T("aaaa-1111", 100.0),           # ext user A
        _T("aaaa-1111", 50.0),            # ext user A again
        _T("bbbb-2222", 25.0),            # ext user B
    ], {OWN})
    assert r["external_n"] == 3
    assert len(r["ext_owners"]) == 2          # A + B, deduped
    assert abs(r["external_vol"] - 175.0) < 1e-9
    assert abs(r["by_ext_owner"]["aaaa-1111"] - 150.0) < 1e-9


def test_empty_owner_not_counted_as_user():
    # a trade with a blank owner adds volume but not a distinct user
    r = classify([_T("", 10.0)], {OWN})
    assert r["external_n"] == 1 and len(r["ext_owners"]) == 0


def test_fees_summed():
    r = classify([_T(OWN, 1.0, fee_usdc=0.01), _T("x", 1.0, fee_usdc=0.02)], {OWN})
    assert abs(r["fees"] - 0.03) < 1e-9


def test_env_and_extra_ids_merge(monkeypatch):
    monkeypatch.setenv("POLYRAILS_OWN_OWNER_IDS", "env-id-1, ENV-ID-2")
    ids = own_owner_ids(["extra-3"])
    assert OWN in ids and "env-id-1" in ids and "env-id-2" in ids and "extra-3" in ids


def test_default_known_owner_id_present(monkeypatch):
    monkeypatch.delenv("POLYRAILS_OWN_OWNER_IDS", raising=False)
    assert own_owner_ids() == {i.lower() for i in KNOWN_OWN_OWNER_IDS}
