"""Etherscan-compatible adapters.

The ``account / txlist`` shape is a de-facto standard: Etherscan defines it and
Blockscout (and most explorer forks) serve the same contract. One parser and one
paging implementation therefore cover both, with the subclass supplying only the
endpoint and whether a key is needed.

The free functions are retained: the offline importer and its tests replay saved
Etherscan payloads through ``parse_etherscan_txlist`` without going near HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog

from app.chains import DEFAULT_CHAIN
from app.providers.base import BaseProvider, Capability, ProviderPage, ProviderTx, WalletInfo
from app.providers.errors import ProviderBadResponse, ProviderRateLimited
from app.providers.http import ResilientHttp

log = structlog.get_logger(__name__)

# Etherscan answers HTTP 200 with the throttle notice in the body, so the status
# code alone never reveals it. These are the substrings it uses.
_RATE_LIMIT_MARKERS = ("rate limit", "max rate", "too many requests")


def parse_etherscan_txlist(payload: dict[str, Any]) -> list[ProviderTx]:
    """Normalize an Etherscan ``txlist`` JSON payload into ProviderTx rows."""
    results = payload.get("result", [])
    if not isinstance(results, list):
        raise ValueError("Unexpected Etherscan payload: 'result' is not a list")

    txs: list[ProviderTx] = []
    for item in results:
        to_addr = (item.get("to") or "").strip().lower() or None
        try:
            ts = datetime.fromtimestamp(int(item["timeStamp"]), tz=UTC)
        except (KeyError, ValueError, OverflowError):
            continue
        try:
            value = Decimal(str(item.get("value", "0")))
        except (InvalidOperation, ValueError):
            continue
        txs.append(
            ProviderTx(
                tx_hash=str(item["hash"]),
                block_number=int(item["blockNumber"]) if item.get("blockNumber") else None,
                timestamp=ts,
                from_address=str(item["from"]).strip().lower(),
                to_address=to_addr,
                value_wei=value,
                gas_used=int(item["gasUsed"]) if item.get("gasUsed") else None,
                gas_price_wei=Decimal(str(item["gasPrice"])) if item.get("gasPrice") else None,
                asset="ETH",
            )
        )
    return txs


async def fetch_etherscan_txlist(
    address: str,
    api_key: str,
    *,
    base_url: str = "https://api.etherscan.io/api",
    limit: int = 200,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Fetch normal transactions for an address from Etherscan (optional, live).

    Requires an API key. Not used by the offline demo.
    """
    import httpx

    params: dict[str, str | int] = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": limit,
        "sort": "asc",
        "apikey": api_key,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(base_url, params=params)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


class EtherscanCompatibleProvider(BaseProvider):
    """Shared implementation for any explorer serving the Etherscan API shape."""

    name = "etherscan-compatible"
    requires_api_key = True

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        chain: str = DEFAULT_CHAIN.value,
        http: ResilientHttp | None = None,
        page_size: int = 200,
    ) -> None:
        self.chain = chain
        self._base_url = base_url
        self._api_key = api_key
        self._page_size = page_size
        self._http = http or ResilientHttp(self.name)

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        params = {"module": "account", **extra}
        if self._api_key:
            params["apikey"] = self._api_key
        return params

    def _check_envelope(self, payload: Any) -> list[dict[str, Any]]:
        """Validate the ``{status, message, result}`` envelope.

        Etherscan signals three different things through it: success, an empty
        but valid result, and a throttle. Only the throttle should look like a
        failure to the router -- treating "no transactions found" as an error
        would make a genuinely empty wallet indistinguishable from an outage.
        """
        if not isinstance(payload, dict):
            raise ProviderBadResponse(self.name, "response was not a JSON object")

        message = str(payload.get("message", ""))
        result = payload.get("result")

        if isinstance(result, str):
            haystack = f"{message} {result}".lower()
            if any(m in haystack for m in _RATE_LIMIT_MARKERS):
                raise ProviderRateLimited(self.name, result)
            raise ProviderBadResponse(self.name, result or message)

        if result is None:
            if "no transactions found" in message.lower():
                return []
            raise ProviderBadResponse(self.name, message or "missing 'result'")

        if not isinstance(result, list):
            raise ProviderBadResponse(self.name, "'result' is not a list")
        return result

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:
        page_no = int(cursor) if cursor else 1
        size = min(limit, self._page_size)

        payload = await self._http.get_json(
            self._base_url,
            params=self._params(
                {
                    "action": "txlist",
                    "address": address,
                    "startblock": 0,
                    "endblock": 99999999,
                    "page": page_no,
                    "offset": size,
                    "sort": "asc",
                }
            ),
        )
        rows = self._check_envelope(payload)
        txs = parse_etherscan_txlist({"result": rows})

        # Rows the parser rejected (unparseable timestamp or value) are dropped
        # rather than guessed at, and the page is marked partial so a caller can
        # tell a filtered page from a complete one.
        dropped = len(rows) - len(txs)
        if dropped:
            log.warning(
                "provider_rows_dropped", provider=self.name, address=address, dropped=dropped
            )

        # A full page implies there may be another; a short one is the end.
        next_cursor = str(page_no + 1) if len(rows) >= size else None
        return ProviderPage(
            transactions=txs, next_cursor=next_cursor, partial=bool(dropped)
        )

    async def get_wallet(self, address: str) -> WalletInfo:
        payload = await self._http.get_json(
            self._base_url,
            params=self._params({"action": "balance", "address": address, "tag": "latest"}),
        )
        if not isinstance(payload, dict):
            raise ProviderBadResponse(self.name, "response was not a JSON object")
        result = payload.get("result")
        if isinstance(result, str) and result.isdigit():
            balance = Decimal(result)
        else:
            self._check_envelope(payload)
            raise ProviderBadResponse(self.name, f"unexpected balance result: {result!r}")
        return WalletInfo(address=address.strip().lower(), balance_wei=balance)


class EtherscanProvider(EtherscanCompatibleProvider):
    """Etherscan proper. Needs an API key."""

    name = "etherscan"
    requires_api_key = True

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.etherscan.io/api",
        chain: str = DEFAULT_CHAIN.value,
        http: ResilientHttp | None = None,
        page_size: int = 200,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            chain=chain,
            http=http or ResilientHttp(self.name),
            page_size=page_size,
        )


class BlockscoutProvider(EtherscanCompatibleProvider):
    """Blockscout serves the same contract and needs no key.

    That makes it the natural no-credentials fallback: when the keyed provider is
    rate-limited or down, an investigation can still complete.
    """

    name = "blockscout"
    requires_api_key = False
    capabilities = frozenset({Capability.WALLET_INFO, Capability.TRANSACTION_HISTORY})

    def __init__(
        self,
        *,
        base_url: str = "https://eth.blockscout.com/api",
        api_key: str = "",
        chain: str = DEFAULT_CHAIN.value,
        http: ResilientHttp | None = None,
        page_size: int = 200,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            chain=chain,
            http=http or ResilientHttp(self.name),
            page_size=page_size,
        )
