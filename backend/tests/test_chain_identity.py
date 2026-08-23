"""Identity is (chain, address): identical addresses on two chains stay apart.

This is the property the whole multi-chain story rests on. If it breaks, the graph
silently welds two unrelated wallets together and every downstream conclusion is
built on an edge that exists on no ledger.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.attribution.context_builder import ContextBuilder
from app.chains import Chain, normalize_address
from app.models import Label, Transaction, Vasp, Wallet
from app.repositories.graph_repository import Direction, TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository

T0 = datetime(2026, 1, 1, tzinfo=UTC)

ROOT = "0x" + "11" * 20
ETH_HOP = "0x" + "22" * 20
POLY_HOP = "0x" + "33" * 20


def _tx(chain: str, tx_hash: str, frm: str, to: str, offset: int = 0) -> Transaction:
    return Transaction(
        chain=chain,
        provider="fixture",
        tx_hash=tx_hash,
        block_number=100 + offset,
        timestamp=T0 + timedelta(hours=offset),
        from_address=frm,
        to_address=to,
        value_wei=Decimal("1000000000000000000"),
        asset="ETH",
    )


async def _seed_two_chains(session: AsyncSession) -> None:
    """The same root address transacts on Ethereum and on Polygon."""
    session.add_all(
        [
            _tx(Chain.ETHEREUM.value, "0xeth1", ROOT, ETH_HOP, 0),
            _tx(Chain.POLYGON.value, "0xpoly1", ROOT, POLY_HOP, 1),
        ]
    )
    await session.commit()


async def test_traversal_does_not_cross_chains(session: AsyncSession) -> None:
    await _seed_two_chains(session)
    repo = SqlGraphRepository(session)

    eth = await repo.traverse(
        ROOT, TraversalBounds(max_hops=3, chain=Chain.ETHEREUM.value)
    )
    reached = {n.address for n in eth.nodes}
    assert ETH_HOP in reached
    assert POLY_HOP not in reached, "Polygon edge leaked into an Ethereum traversal"

    poly = await repo.traverse(
        ROOT, TraversalBounds(max_hops=3, chain=Chain.POLYGON.value)
    )
    reached = {n.address for n in poly.nodes}
    assert POLY_HOP in reached
    assert ETH_HOP not in reached


async def test_same_address_is_two_wallets(session: AsyncSession) -> None:
    """The old schema made this insert impossible; the new one must allow it."""
    session.add_all(
        [
            Wallet(address=ROOT, chain=Chain.ETHEREUM.value, tx_count=3),
            Wallet(address=ROOT, chain=Chain.POLYGON.value, tx_count=99),
        ]
    )
    await session.commit()

    repo = SqlGraphRepository(session)
    session.add(_tx(Chain.POLYGON.value, "0xpoly2", ROOT, POLY_HOP, 2))
    await session.commit()

    result = await repo.traverse(
        ROOT, TraversalBounds(max_hops=2, chain=Chain.POLYGON.value)
    )
    assert result.root == ROOT
    assert any(n.address == POLY_HOP for n in result.nodes)


async def test_labels_do_not_cross_chains(session: AsyncSession) -> None:
    """A Binance label on Ethereum must not name the same address on Polygon."""
    vasp = Vasp(name="Binance")
    session.add(vasp)
    await session.flush()
    session.add(
        Label(
            address=ETH_HOP,
            chain=Chain.ETHEREUM.value,
            name="Binance hot wallet",
            source="MANUAL",
            vasp_id=vasp.id,
        )
    )
    # Same address, different chain, no label.
    session.add(_tx(Chain.ETHEREUM.value, "0xeth2", ROOT, ETH_HOP, 3))
    session.add(_tx(Chain.POLYGON.value, "0xpoly3", ROOT, ETH_HOP, 4))
    await session.commit()

    repo = SqlGraphRepository(session)

    eth = await repo.traverse(
        ROOT, TraversalBounds(max_hops=2, chain=Chain.ETHEREUM.value)
    )
    eth_node = next(n for n in eth.nodes if n.address == ETH_HOP)
    assert eth_node.is_labeled
    assert eth_node.vasp_name == "Binance"

    poly = await repo.traverse(
        ROOT, TraversalBounds(max_hops=2, chain=Chain.POLYGON.value)
    )
    poly_node = next(n for n in poly.nodes if n.address == ETH_HOP)
    assert not poly_node.is_labeled, "Ethereum label leaked onto a Polygon node"
    assert poly_node.vasp_name is None


async def test_context_builder_is_chain_scoped(session: AsyncSession) -> None:
    await _seed_two_chains(session)
    builder = ContextBuilder(session, chain=Chain.ETHEREUM.value)
    context = await builder.build(ROOT, depth=3)
    assert context.chain == Chain.ETHEREUM.value
    reached = {n.address for n in context.forward_graph.nodes}
    assert POLY_HOP not in reached


async def test_reverse_traversal_is_also_chain_scoped(session: AsyncSession) -> None:
    await _seed_two_chains(session)
    repo = SqlGraphRepository(session)
    rev = await repo.traverse(
        POLY_HOP,
        TraversalBounds(
            max_hops=3, direction=Direction.REVERSE, chain=Chain.ETHEREUM.value
        ),
    )
    # Walking back from a Polygon-only address on Ethereum reaches nothing.
    assert [n.address for n in rev.nodes] == [POLY_HOP]


def test_evm_addresses_case_fold_but_bitcoin_does_not() -> None:
    mixed = "0xAbCdEf0123456789AbCdEf0123456789AbCdEf01"
    assert normalize_address(mixed, Chain.ETHEREUM) == mixed.lower()
    assert normalize_address(mixed, Chain.POLYGON) == mixed.lower()

    # Base58Check is case-significant; folding it would corrupt the address.
    btc = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
    assert normalize_address(btc, Chain.BITCOIN) == btc
