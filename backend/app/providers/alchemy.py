"""Alchemy provider, via ``alchemy_getAssetTransfers``.

Alchemy is a node vendor that additionally maintains a transfer index, which is
what makes address history answerable here at all. Paging uses the API's own
``pageKey`` rather than an offset, so a long history stays consistent even if new
blocks land mid-walk.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import structlog

from app.chains import DEFAULT_CHAIN
from app.providers.base import (
    BaseProvider,
    Capability,
    ProviderPage,
    ProviderTx,
    WalletInfo,
)
from app.providers.errors import ProviderBadResponse
from app.providers.http import ResilientHttp
from app.providers.rpc import JsonRpcClient, hex_to_int

log = structlog.get_logger(__name__)


def _parse_timestamp(metadata: object) -> datetime | None:
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("blockTimestamp")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _parse_value_wei(transfer: dict[str, object]) -> Decimal | None:
    """Take wei from ``rawContract.value``, never from ``value``.

    The top-level ``value`` is a JSON float already divided down to ETH, so it
    cannot represent a wei-exact amount. Deriving evidence from a lossy number
    would put rounding error into figures an investigator may have to defend.
    """
    raw = transfer.get("rawContract")
    if isinstance(raw, dict):
        parsed = hex_to_int(raw.get("value"))
        if parsed is not None:
            return Decimal(parsed)
    return None


class AlchemyProvider(BaseProvider):
    name = "alchemy"
    requires_api_key = True
    capabilities = frozenset({Capability.WALLET_INFO, Capability.TRANSACTION_HISTORY})

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://eth-mainnet.g.alchemy.com/v2",
        chain: str = DEFAULT_CHAIN.value,
        http: ResilientHttp | None = None,
        page_size: int = 100,
    ) -> None:
        self.chain = chain
        self._page_size = page_size
        url = f"{base_url.rstrip('/')}/{api_key}"
        self._rpc = JsonRpcClient(self.name, url, http or ResilientHttp(self.name))

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:
        size = min(limit, self._page_size)
        params: dict[str, object] = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "fromAddress": address,
            # External transfers only: internal calls and token movements are a
            # different edge type and would change what the graph means.
            "category": ["external"],
            "withMetadata": True,
            "excludeZeroValue": False,
            "maxCount": hex(size),
            "order": "asc",
        }
        if cursor:
            params["pageKey"] = cursor

        result = await self._rpc.call("alchemy_getAssetTransfers", [params])
        if not isinstance(result, dict):
            raise ProviderBadResponse(self.name, "getAssetTransfers result was not an object")

        transfers = result.get("transfers")
        if not isinstance(transfers, list):
            raise ProviderBadResponse(self.name, "'transfers' missing or not a list")

        txs: list[ProviderTx] = []
        dropped = 0
        for t in transfers:
            if not isinstance(t, dict):
                dropped += 1
                continue
            # A transfer without a timestamp, an exact value, a hash or a sender
            # cannot become a defensible edge, so it is dropped and counted
            # rather than filled in with a guess.
            ts = _parse_timestamp(t.get("metadata"))
            if ts is None:
                dropped += 1
                continue
            value = _parse_value_wei(t)
            if value is None:
                dropped += 1
                continue
            tx_hash = t.get("hash")
            frm = t.get("from")
            if not isinstance(tx_hash, str) or not isinstance(frm, str):
                dropped += 1
                continue

            to = t.get("to")
            txs.append(
                ProviderTx(
                    tx_hash=tx_hash,
                    block_number=hex_to_int(t.get("blockNum")),
                    timestamp=ts,
                    from_address=frm.strip().lower(),
                    to_address=to.strip().lower() if isinstance(to, str) and to else None,
                    value_wei=value,
                    asset=str(t.get("asset") or "ETH"),
                )
            )

        if dropped:
            log.warning(
                "provider_rows_dropped", provider=self.name, address=address, dropped=dropped
            )

        page_key = result.get("pageKey")
        return ProviderPage(
            transactions=txs,
            next_cursor=page_key if isinstance(page_key, str) and page_key else None,
            partial=bool(dropped),
        )

    async def get_wallet(self, address: str) -> WalletInfo:
        balance = await self._rpc.call("eth_getBalance", [address, "latest"])
        code = await self._rpc.call("eth_getCode", [address, "latest"])
        nonce = await self._rpc.call("eth_getTransactionCount", [address, "latest"])
        wei = hex_to_int(balance)
        return WalletInfo(
            address=address.strip().lower(),
            balance_wei=Decimal(wei) if wei is not None else None,
            is_contract=isinstance(code, str) and code not in ("0x", "0x0", ""),
            tx_count=hex_to_int(nonce, 0) or 0,
        )
