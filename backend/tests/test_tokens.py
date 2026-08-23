"""ERC-20 (stablecoin) transfers flow through the same pipeline."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.chain_import import import_provider_txs
from app.ingest.labels import ingest_all
from app.providers.etherscan import parse_etherscan_tokentx
from app.repositories.graph_repository import TraversalBounds
from app.repositories.sql_graph_repository import SqlGraphRepository

KRAKEN = "0x2910543af39aba0cd09dbb2d50200b3e800a63d2"
UNKNOWN = "0x" + "1" * 40


def _tokentx_payload() -> dict[str, Any]:
    return {
        "status": "1",
        "message": "OK",
        "result": [
            {
                "hash": "0x" + "a" * 64,
                "blockNumber": "100",
                "timeStamp": "1710000000",
                "from": UNKNOWN,
                "to": KRAKEN,
                "value": "1000000000",  # 1000 USDT (6 decimals)
                "tokenSymbol": "USDT",
                "tokenDecimal": "6",
                "gasUsed": "21000",
                "gasPrice": "1000000000",
            }
        ],
    }


def test_parse_tokentx_sets_asset_and_value() -> None:
    txs = parse_etherscan_tokentx(_tokentx_payload())
    assert len(txs) == 1
    assert txs[0].asset == "USDT"
    assert txs[0].value_wei == Decimal("1000000000")
    assert txs[0].to_address == KRAKEN


async def test_token_transfer_reaches_vasp_in_graph(session: AsyncSession) -> None:
    await ingest_all(session)
    txs = parse_etherscan_tokentx(_tokentx_payload())
    await import_provider_txs(session, txs)
    await session.commit()

    repo = SqlGraphRepository(session)
    graph = await repo.traverse(UNKNOWN, TraversalBounds(max_hops=2))

    edge = next((e for e in graph.edges if e.to_address == KRAKEN), None)
    assert edge is not None
    assert edge.asset == "USDT"  # asset carried through the traversal
    kraken = next((n for n in graph.nodes if n.address == KRAKEN), None)
    assert kraken is not None and kraken.vasp_name == "Kraken"
