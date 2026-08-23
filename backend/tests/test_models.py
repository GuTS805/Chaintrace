"""Model + relationship smoke tests against the real metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import CaseStatus, FindingSeverity, LabelSource, VaspCategory
from app.models import (
    Case,
    Cluster,
    ClusterMember,
    Finding,
    Label,
    Transaction,
    Vasp,
    Wallet,
)


async def test_wallet_and_transaction_roundtrip(session: AsyncSession) -> None:
    session.add(Wallet(address="0xabc", balance_wei=Decimal("1000")))
    session.add(
        Transaction(
            tx_hash="0xdead",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            from_address="0xabc",
            to_address="0xdef",
            value_wei=Decimal("500"),
        )
    )
    await session.commit()

    wallet = (
        await session.execute(select(Wallet).where(Wallet.address == "0xabc"))
    ).scalar_one()
    assert wallet.balance_wei == Decimal("1000")

    tx = (await session.execute(select(Transaction))).scalar_one()
    assert tx.from_address == "0xabc"
    assert tx.value_wei == Decimal("500")


async def test_vasp_label_relationship(session: AsyncSession) -> None:
    vasp = Vasp(name="Binance", category=VaspCategory.CENTRALIZED_EXCHANGE)
    session.add(vasp)
    await session.flush()
    session.add(
        Label(
            address="0x3f5ce5",
            name="Binance: Hot Wallet",
            source=LabelSource.ETHEREUM_LISTS,
            vasp_id=vasp.id,
        )
    )
    await session.commit()

    loaded = (
        await session.execute(select(Vasp).where(Vasp.name == "Binance"))
    ).scalar_one()
    await session.refresh(loaded, ["labels"])
    assert len(loaded.labels) == 1
    assert loaded.labels[0].source == LabelSource.ETHEREUM_LISTS


async def test_case_finding_cascade(session: AsyncSession) -> None:
    case = Case(name="Ransomware payout trace", status=CaseStatus.OPEN)
    session.add(case)
    await session.flush()
    session.add(
        Finding(
            case_id=case.id,
            title="Deposit sweep into exchange hot wallet",
            severity=FindingSeverity.HIGH,
            evidence={"signal_type": "DEPOSIT_SWEEP", "weight": 0.4},
        )
    )
    await session.commit()

    finding = (await session.execute(select(Finding))).scalar_one()
    assert finding.severity == FindingSeverity.HIGH
    assert finding.evidence["signal_type"] == "DEPOSIT_SWEEP"


async def test_cluster_membership(session: AsyncSession) -> None:
    cluster = Cluster(name="peel-chain-1", heuristic="common_input_ownership")
    cluster.members.append(ClusterMember(address="0x1"))
    cluster.members.append(ClusterMember(address="0x2"))
    session.add(cluster)
    await session.commit()

    loaded = (await session.execute(select(Cluster))).scalar_one()
    await session.refresh(loaded, ["members"])
    assert {m.address for m in loaded.members} == {"0x1", "0x2"}
