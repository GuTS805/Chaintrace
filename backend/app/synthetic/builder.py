"""Deterministic builder for synthetic scenario graphs.

Everything is derived from string keys via a stable hash, so regenerating a
scenario always yields identical addresses, tx hashes, timestamps and values —
essential for a reliable, reproducible demo.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.providers.base import ProviderTx, WalletInfo
from app.synthetic.types import ExpectedOutcome, Scenario, ScenarioLabel

WEI = Decimal(10) ** 18
# Fixed epoch so every generated timestamp is deterministic.
BASE_TIME = datetime(2024, 3, 1, 9, 0, 0, tzinfo=UTC)
BASE_BLOCK = 19_400_000


def eth_to_wei(amount: float | str | Decimal) -> Decimal:
    return (Decimal(str(amount)) * WEI).quantize(Decimal(1))


class ScenarioBuilder:
    """Fluent helper to assemble a scenario's wallets, txs and labels."""

    def __init__(self, key: str, title: str, description: str) -> None:
        self.key = key
        self.title = title
        self.description = description
        self._addr: dict[str, str] = {}
        self._wallets: dict[str, WalletInfo] = {}
        self._txs: list[ProviderTx] = []
        self._labels: list[ScenarioLabel] = []
        self._minutes = 0
        self._nonce = 0

    # -- addresses -------------------------------------------------------
    def addr(self, name: str) -> str:
        """Deterministic synthetic address for a logical node name."""
        if name not in self._addr:
            digest = hashlib.sha1(f"{self.key}/{name}".encode()).hexdigest()
            self._addr[name] = "0x" + digest[:40]
        return self._addr[name]

    def known(self, address: str, name: str) -> str:
        """Register a real/known address (e.g. a VASP hot wallet) under a name."""
        addr = address.strip().lower()
        self._addr[name] = addr
        self._ensure_wallet(addr)
        return addr

    def _resolve(self, ref: str) -> str:
        """Resolve a name to its address (or accept a raw 0x address)."""
        if ref in self._addr:
            return self._addr[ref]
        if ref.startswith("0x"):
            return ref.lower()
        return self.addr(ref)

    # -- wallets ---------------------------------------------------------
    def _ensure_wallet(self, address: str) -> WalletInfo:
        if address not in self._wallets:
            self._wallets[address] = WalletInfo(address=address)
        return self._wallets[address]

    def wallet(
        self,
        name: str,
        *,
        is_contract: bool = False,
        balance_eth: float | str | None = None,
    ) -> str:
        addr = self._resolve(name)
        w = self._ensure_wallet(addr)
        w.is_contract = is_contract
        if balance_eth is not None:
            w.balance_wei = eth_to_wei(balance_eth)
        return addr

    # -- labels ----------------------------------------------------------
    def label(
        self, ref: str, name: str, category: str, vasp: str | None = None
    ) -> None:
        self._labels.append(
            ScenarioLabel(
                address=self._resolve(ref), name=name, category=category, vasp=vasp
            )
        )

    # -- transactions ----------------------------------------------------
    def tx(
        self,
        frm: str,
        to: str,
        value_eth: float | str,
        *,
        gap_minutes: int = 30,
    ) -> ProviderTx:
        """Append a transfer, advancing the deterministic clock/block counter."""
        self._minutes += gap_minutes
        self._nonce += 1
        from_addr = self._resolve(frm)
        to_addr = self._resolve(to)
        self._ensure_wallet(from_addr)
        self._ensure_wallet(to_addr)
        ts = BASE_TIME + timedelta(minutes=self._minutes)
        tx_hash = "0x" + hashlib.sha256(f"{self.key}/tx/{self._nonce}".encode()).hexdigest()
        tx = ProviderTx(
            tx_hash=tx_hash,
            block_number=BASE_BLOCK + self._minutes * 5,
            timestamp=ts,
            from_address=from_addr,
            to_address=to_addr,
            value_wei=eth_to_wei(value_eth),
            gas_used=21_000,
            gas_price_wei=eth_to_wei("0.0000000003"),  # ~0.3 gwei placeholder
            asset="ETH",
        )
        self._txs.append(tx)
        return tx

    # -- finalize --------------------------------------------------------
    def build(
        self,
        *,
        unknown: str,
        expected: ExpectedOutcome,
        ground_truth: str | None,
        ground_truth_candidates: list[str] | None = None,
    ) -> Scenario:
        counts: Counter[str] = Counter()
        for t in self._txs:
            counts[t.from_address] += 1
            if t.to_address:
                counts[t.to_address] += 1
        for addr, w in self._wallets.items():
            w.tx_count = counts.get(addr, 0)

        return Scenario(
            key=self.key,
            title=self.title,
            description=self.description,
            unknown_wallet=self._resolve(unknown),
            expected=expected,
            ground_truth=ground_truth,
            ground_truth_candidates=ground_truth_candidates or [],
            wallets=list(self._wallets.values()),
            transactions=list(self._txs),
            labels=list(self._labels),
        )
