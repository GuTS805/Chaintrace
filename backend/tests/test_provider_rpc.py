"""JSON-RPC providers: Alchemy transfer history and Infura wallet state."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.providers.alchemy import AlchemyProvider
from app.providers.base import Capability
from app.providers.errors import (
    ProviderBadResponse,
    ProviderNotCapable,
    ProviderRateLimited,
)
from app.providers.http import ResilientHttp
from app.providers.infura import InfuraProvider


def transfer(i: int, *, raw_hex: str = "0xde0b6b3a7640000") -> dict[str, object]:
    return {
        "blockNum": hex(1000 + i),
        "hash": f"0x{i:064x}",
        "from": "0xAAAA000000000000000000000000000000000001",
        "to": "0xbbbb000000000000000000000000000000000002",
        # Lossy float Alchemy also sends; deliberately wrong here so a test fails
        # if the parser ever prefers it.
        "value": 0.1,
        "asset": "ETH",
        "rawContract": {"value": raw_hex, "decimal": "0x12"},
        "metadata": {"blockTimestamp": "2024-03-01T12:00:00.000Z"},
    }


def alchemy(handler, **kw) -> AlchemyProvider:
    http = ResilientHttp("alchemy", transport=httpx.MockTransport(handler), max_attempts=1)
    return AlchemyProvider(api_key="k", http=http, **kw)


def infura(handler) -> InfuraProvider:
    http = ResilientHttp("infura", transport=httpx.MockTransport(handler), max_attempts=1)
    return InfuraProvider(api_key="k", http=http)


def rpc_ok(result: object) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})


# --- alchemy --------------------------------------------------------------


async def test_value_comes_from_raw_contract_not_the_lossy_float() -> None:
    """1 ETH is 10**18 wei exactly; the float field would round it."""

    def handler(request: httpx.Request) -> httpx.Response:
        return rpc_ok({"transfers": [transfer(1)]})

    [row] = (await alchemy(handler).get_transaction_page("0xabc")).transactions
    assert row.value_wei == Decimal(10**18)
    assert row.timestamp == datetime(2024, 3, 1, 12, 0, tzinfo=UTC)
    assert row.block_number == 1001
    assert row.from_address == "0xaaaa000000000000000000000000000000000001"


async def test_transfer_without_an_exact_value_is_dropped_and_flagged() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        broken = transfer(2)
        del broken["rawContract"]
        return rpc_ok({"transfers": [transfer(1), broken]})

    page = await alchemy(handler).get_transaction_page("0xabc")
    assert len(page.transactions) == 1
    assert page.partial is True


async def test_transfer_without_a_timestamp_is_dropped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        broken = transfer(2) | {"metadata": {}}
        return rpc_ok({"transfers": [broken]})

    page = await alchemy(handler).get_transaction_page("0xabc")
    assert page.transactions == []
    assert page.partial is True


async def test_page_key_is_used_as_the_cursor() -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        body = _json.loads(request.content)
        seen.append(body["params"][0].get("pageKey"))
        if len(seen) == 1:
            return rpc_ok({"transfers": [transfer(1)], "pageKey": "KEY2"})
        return rpc_ok({"transfers": [transfer(2)]})

    rows = await alchemy(handler).get_transactions("0xabc", limit=10)
    assert seen == [None, "KEY2"]
    assert len(rows) == 2


async def test_rpc_rate_limit_maps_to_the_shared_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32005, "message": "capacity exceeded"},
            },
        )

    with pytest.raises(ProviderRateLimited):
        await alchemy(handler).get_transaction_page("0xabc")


async def test_rpc_error_is_a_bad_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1,
                  "error": {"code": -32602, "message": "invalid params"}},
        )

    with pytest.raises(ProviderBadResponse):
        await alchemy(handler).get_transaction_page("0xabc")


async def test_missing_result_is_a_bad_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1})

    with pytest.raises(ProviderBadResponse):
        await alchemy(handler).get_transaction_page("0xabc")


# --- infura ---------------------------------------------------------------


async def test_infura_reports_wallet_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        method = _json.loads(request.content)["method"]
        return rpc_ok(
            {
                "eth_getBalance": "0xde0b6b3a7640000",
                "eth_getCode": "0x60806040",
                "eth_getTransactionCount": "0x2a",
            }[method]
        )

    wallet = await infura(handler).get_wallet("0xABC")
    assert wallet.balance_wei == Decimal(10**18)
    assert wallet.is_contract is True
    assert wallet.tx_count == 42


async def test_infura_marks_an_eoa_as_not_a_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        method = _json.loads(request.content)["method"]
        return rpc_ok({"eth_getBalance": "0x0", "eth_getCode": "0x",
                       "eth_getTransactionCount": "0x0"}[method])

    assert (await infura(handler).get_wallet("0xabc")).is_contract is False


async def test_infura_declares_no_history_capability() -> None:
    """A node has no address index; the router must know before it routes."""

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request should be made")

    p = infura(handler)
    assert Capability.TRANSACTION_HISTORY not in p.capabilities
    assert Capability.WALLET_INFO in p.capabilities
    with pytest.raises(ProviderNotCapable):
        await p.get_transaction_page("0xabc")
