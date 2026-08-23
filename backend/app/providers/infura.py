"""Infura provider — wallet state only.

Infura is a plain JSON-RPC node endpoint. It has no address index, so there is no
call that returns "every transaction touching this address"; reconstructing that
would mean scanning blocks or running a separate indexer. Rather than pretend
otherwise with a stub that returns an empty list — which downstream would read as
"this wallet has no activity", the most dangerous possible wrong answer — this
provider declares only ``WALLET_INFO`` and the router never asks it for history.

It is still worth having: balance, contract-ness and nonce are exactly what you
want a second opinion on when the indexing providers disagree or are down.
"""

from __future__ import annotations

from decimal import Decimal

from app.chains import DEFAULT_CHAIN
from app.providers.base import (
    BaseProvider,
    Capability,
    ProviderPage,
    WalletInfo,
)
from app.providers.errors import ProviderNotCapable
from app.providers.http import ResilientHttp
from app.providers.rpc import JsonRpcClient, hex_to_int


class InfuraProvider(BaseProvider):
    name = "infura"
    requires_api_key = True
    capabilities = frozenset({Capability.WALLET_INFO})

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://mainnet.infura.io/v3",
        chain: str = DEFAULT_CHAIN.value,
        http: ResilientHttp | None = None,
    ) -> None:
        self.chain = chain
        url = f"{base_url.rstrip('/')}/{api_key}"
        self._rpc = JsonRpcClient(self.name, url, http or ResilientHttp(self.name))

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

    async def get_transaction_page(
        self, address: str, *, limit: int = 1000, cursor: str | None = None
    ) -> ProviderPage:
        raise ProviderNotCapable(
            self.name,
            "a JSON-RPC node has no address index; transaction history needs an "
            "indexing provider (Etherscan, Blockscout, Alchemy)",
        )
