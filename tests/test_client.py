"""Offline tests: pure logic + SDK surface compatibility (no network, no keys)."""
from __future__ import annotations

import inspect

import pytest

from polyrails import OrderResult, Rails
from polyrails.client import conform_tick


class TestConformTick:
    def test_buy_rounds_up(self):
        assert conform_tick(0.421, "BUY") == 0.43

    def test_sell_rounds_down(self):
        assert conform_tick(0.429, "SELL") == 0.42

    def test_float_noise_not_bumped(self):
        # 0.18*100 -> 18.000000000000004 must stay 0.18, not become 0.19
        assert conform_tick(0.18, "BUY") == 0.18
        assert conform_tick(0.18, "SELL") == 0.18

    def test_clamps(self):
        assert conform_tick(0.001, "SELL") == 0.01
        assert conform_tick(0.999, "BUY") == 0.99


class TestOrderResult:
    def test_from_sdk_maps_fields(self):
        class Stub:
            ok = True
            status = "matched"
            order_id = "0xabc"
            making_amount = "1.10"
            taking_amount = "2.75"

        r = OrderResult.from_sdk(Stub())
        assert r.ok and r.status == "matched" and r.order_id == "0xabc"
        assert r.making_amount == 1.10 and r.taking_amount == 2.75

    def test_from_sdk_rejected_defaults(self):
        r = OrderResult.from_sdk(object())
        assert not r.ok and r.order_id == "" and r.making_amount == 0.0


@pytest.fixture(scope="module")
def secure_cls():
    polymarket = pytest.importorskip("polymarket")
    assert hasattr(polymarket, "BuilderApiKey"), "BuilderApiKey missing from SDK"
    return polymarket.AsyncSecureClient


class TestSdkSurface:
    """Locks the SDK API polyrails depends on. Fails loudly on SDK drift."""

    @pytest.mark.parametrize("method,needed", [
        ("place_limit_order", {"token_id", "price", "size", "side", "post_only", "builder_code"}),
        ("place_market_order", {"token_id", "side", "amount", "shares", "order_type", "builder_code"}),
        ("cancel_order", {"order_id"}),
        ("list_open_orders", {"token_id", "market"}),
        ("list_builder_trades", {"builder_code"}),
        ("get_balance_allowance", {"asset_type"}),
    ])
    def test_method_signatures(self, secure_cls, method, needed):
        fn = getattr(secure_cls, method, None)
        assert fn is not None, f"AsyncSecureClient.{method} missing"
        params = set(inspect.signature(fn).parameters)
        missing = needed - params
        assert not missing, f"{method} lost params: {missing}"

    def test_connect_entrypoints(self, secure_cls):
        assert hasattr(secure_cls, "create")
        create_params = set(inspect.signature(secure_cls.create).parameters)
        assert {"private_key", "api_key"} <= create_params
        # setup_gasless_wallet is an instance method on the created client
        assert hasattr(secure_cls, "setup_gasless_wallet")

    def test_rails_never_imports_sdk_at_module_load(self):
        import sys
        import importlib
        import polyrails.client as pc
        # reload polyrails.client with polymarket hidden -> must still import
        hidden = {k: sys.modules.pop(k) for k in list(sys.modules)
                  if k == "polymarket" or k.startswith("polymarket.")}
        try:
            importlib.reload(pc)
            assert hasattr(pc, "Rails") and hasattr(Rails, "connect")
        finally:
            sys.modules.update(hidden)
            importlib.reload(pc)
