"""Etherscan-compatible providers: parsing, paging, and envelope handling."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.providers.base import Capability
from app.providers.errors import ProviderBadResponse, ProviderRateLimited
from app.providers.etherscan import (
    BlockscoutProvider,
    EtherscanProvider,
    parse_etherscan_txlist,
)
from app.providers.http import ResilientHttp


def tx(i: int, *, value: str = "1000000000000000000") -> dict[str, str]:
    return {
        "blockNumber": str(1000 + i),
        "timeStamp": str(1700000000 + i * 60),
        "hash": f"0x{i:064x}",
        "from": "0xAAAA000000000000000000000000000000000001",
        "to": "0xbbbb000000000000000000000000000000000002",
        "value": value,
        "gasUsed": "21000",
        "gasPrice": "1000000000",
    }


def provider(handler, **kw):
    http = ResilientHttp(
        "etherscan",
        transport=httpx.MockTransport(handler),
        sleep=lambda _s: _noop(),
        max_attempts=1,
    )
    return EtherscanProvider(api_key="k", http=http, **kw)


async def _noop() -> None:
    return None


# --- parsing --------------------------------------------------------------


def test_parser_lowercases_addresses_and_keeps_wei_exact() -> None:
    [row] = parse_etherscan_txlist({"result": [tx(1, value="123456789012345678901")]})
    assert row.from_address == "0xaaaa000000000000000000000000000000000001"
    assert row.to_address == "0xbbbb000000000000000000000000000000000002"
    assert row.value_wei == Decimal("123456789012345678901")


def test_parser_skips_rows_it_cannot_trust() -> None:
    """A row without a usable timestamp or value must not become an edge."""
    bad_ts = tx(1) | {"timeStamp": "not-a-number"}
    bad_value = tx(2) | {"value": "abc"}
    rows = parse_etherscan_txlist({"result": [bad_ts, bad_value, tx(3)]})
    assert [r.tx_hash for r in rows] == [f"0x{3:064x}"]


def test_parser_rejects_a_non_list_result() -> None:
    with pytest.raises(ValueError):
        parse_etherscan_txlist({"result": "Max rate limit reached"})


# --- envelope -------------------------------------------------------------


async def test_rate_limit_arrives_as_http_200_and_is_detected() -> None:
    """Etherscan puts the throttle notice in the body, not the status code."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "0", "message": "NOTOK", "result": "Max rate limit reached"},
        )

    with pytest.raises(ProviderRateLimited):
        await provider(handler).get_transaction_page("0xabc")


async def test_empty_wallet_is_not_an_error() -> None:
    """'No transactions found' must be distinguishable from an outage."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"status": "0", "message": "No transactions found", "result": []}
        )

    page = await provider(handler).get_transaction_page("0xabc")
    assert page.transactions == []
    assert page.next_cursor is None


async def test_unexpected_envelope_is_a_bad_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "0", "message": "Invalid API Key",
                                         "result": "Invalid API Key"})

    with pytest.raises(ProviderBadResponse):
        await provider(handler).get_transaction_page("0xabc")


# --- paging ---------------------------------------------------------------


async def test_full_page_advertises_a_next_cursor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "1", "result": [tx(i) for i in range(5)]})

    page = await provider(handler, page_size=5).get_transaction_page("0xabc", limit=5)
    assert len(page.transactions) == 5
    assert page.next_cursor == "2"


async def test_short_page_ends_the_walk() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "1", "result": [tx(1), tx(2)]})

    page = await provider(handler, page_size=5).get_transaction_page("0xabc", limit=5)
    assert page.next_cursor is None


async def test_get_transactions_walks_pages_and_dedupes_overlap() -> None:
    """Overlapping page boundaries must not produce duplicate edges."""
    pages = {
        "1": [tx(1), tx(2)],
        # tx(2) repeats: a real explorer can return it on both pages.
        "2": [tx(2), tx(3)],
        "3": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        page_no = request.url.params.get("page", "1")
        return httpx.Response(200, json={"status": "1", "result": pages[page_no]})

    rows = await provider(handler, page_size=2).get_transactions("0xabc", limit=10)
    hashes = [r.tx_hash for r in rows]
    assert hashes == sorted(set(hashes), key=hashes.index)
    assert len(hashes) == 3


async def test_paging_stops_at_the_requested_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page_no = int(request.url.params.get("page", "1"))
        base = (page_no - 1) * 2
        return httpx.Response(
            200, json={"status": "1", "result": [tx(base + 1), tx(base + 2)]}
        )

    rows = await provider(handler, page_size=2).get_transactions("0xabc", limit=5)
    assert len(rows) == 5


async def test_paging_cannot_spin_forever() -> None:
    """A provider that always advertises another page must still terminate."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        page_no = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json={"status": "1", "result": [tx(page_no)]})

    p = provider(handler, page_size=1)
    rows = await p.get_transactions("0xabc", limit=10_000)
    assert calls["n"] == p.max_pages
    assert len(rows) == p.max_pages


async def test_dropped_rows_mark_the_page_partial() -> None:
    """Silently filtered rows would make missing data look like absent activity."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "1", "result": [tx(1), tx(2) | {"timeStamp": "bad"}]},
        )

    page = await provider(handler).get_transaction_page("0xabc")
    assert page.partial is True
    assert len(page.transactions) == 1


# --- balance + blockscout -------------------------------------------------


async def test_get_wallet_reads_the_balance() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "1", "result": "4200000000000000000"})

    wallet = await provider(handler).get_wallet("0xABC")
    assert wallet.address == "0xabc"
    assert wallet.balance_wei == Decimal("4200000000000000000")


async def test_blockscout_needs_no_key_and_sends_none() -> None:
    """The keyless fallback must not send an empty apikey parameter."""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"status": "1", "result": [tx(1)]})

    http = ResilientHttp("blockscout", transport=httpx.MockTransport(handler), max_attempts=1)
    bs = BlockscoutProvider(http=http)
    await bs.get_transaction_page("0xabc")

    assert "apikey" not in seen
    assert bs.requires_api_key is False
    assert Capability.TRANSACTION_HISTORY in bs.capabilities
