"""End-to-end tests for investigations, the platform's primary resource."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_task_sessionmaker
from app.attribution.model import DEFAULT_MODEL_PATH
from app.db.session import get_session
from app.enums import InvestigationStatus
from app.investigations.evidence import compute_evidence_hash
from app.investigations.runner import run_investigation
from app.main import app
from app.models import Investigation, Transaction
from app.synthetic import build_all_scenarios
from app.synthetic.seed import seed_demo

pytestmark = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="model artifact missing; run `make train`"
)

SCN = {s.key: s for s in build_all_scenarios()}
ATTRIBUTABLE = SCN["ransomware_to_exchange"].unknown_wallet
DEAD_END = SCN["dead_end"].unknown_wallet


@pytest_asyncio.fixture
async def client(
    session: AsyncSession, sessionmaker: async_sessionmaker[AsyncSession]
) -> AsyncIterator[AsyncClient]:
    await seed_demo(session)
    await session.commit()
    app.dependency_overrides[get_session] = lambda: session
    # Background work runs against the same in-memory database as the request.
    app.dependency_overrides[get_task_sessionmaker] = lambda: sessionmaker
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _open(client: AsyncClient, address: str, **kw: object) -> dict:
    resp = await client.post(
        "/investigations", json={"address": address, **kw}
    )
    assert resp.status_code == 202, resp.text
    return resp.json()


# --- lifecycle ------------------------------------------------------------


async def test_post_returns_202_with_an_id(client: AsyncClient) -> None:
    body = await _open(client, ATTRIBUTABLE, requested_by="analyst-1")
    assert body["id"].startswith("INV-")
    # INV-YYYY-NNNNN
    prefix, year, seq = body["id"].split("-")
    assert prefix == "INV" and len(year) == 4 and len(seq) == 5
    assert body["chain"] == "ethereum"
    assert body["address"] == ATTRIBUTABLE
    assert body["requested_by"] == "analyst-1"


async def test_investigation_reaches_a_terminal_state(client: AsyncClient) -> None:
    inv = await _open(client, ATTRIBUTABLE)
    detail = (await client.get(f"/investigations/{inv['id']}")).json()
    assert detail["status"] == InvestigationStatus.COMPLETED.value, detail.get("error")
    assert detail["has_result"] is True
    assert detail["started_at"] is not None
    assert detail["completed_at"] is not None
    assert detail["error"] is None


async def test_completed_detail_carries_conclusion_and_methodology(
    client: AsyncClient,
) -> None:
    inv = await _open(client, ATTRIBUTABLE)
    detail = (await client.get(f"/investigations/{inv['id']}")).json()

    assert detail["attribution"]["candidates"][0]["vasp_name"] == "Binance"
    assert detail["risk"]["level"] in {"MEDIUM", "HIGH", "CRITICAL"}

    method = detail["methodology"]
    assert len(method["evidence_hash"]) == 64
    assert method["provider"] == "fixture"
    assert method["model_version"].startswith("phase4-")
    assert method["traversal_bounds"]["chain"] == "ethereum"
    assert method["data_timestamp"] is not None


async def test_insufficient_evidence_is_a_completed_investigation(
    client: AsyncClient,
) -> None:
    """Declining to attribute is a successful run, not a failed one."""
    inv = await _open(client, DEAD_END)
    detail = (await client.get(f"/investigations/{inv['id']}")).json()
    assert detail["status"] == InvestigationStatus.COMPLETED.value
    assert detail["attribution"]["insufficient_evidence"] is True


# --- result sub-resources -------------------------------------------------


async def test_result_sub_resources(client: AsyncClient) -> None:
    inv = await _open(client, ATTRIBUTABLE)
    iid = inv["id"]

    graph = (await client.get(f"/investigations/{iid}/graph")).json()
    assert graph["investigation_id"] == iid
    assert graph["graph"]["nodes"]

    attribution = (await client.get(f"/investigations/{iid}/attribution")).json()
    assert attribution["candidates"]

    risk = (await client.get(f"/investigations/{iid}/risk")).json()
    assert 0.0 <= risk["score"] <= 1.0

    evidence = (await client.get(f"/investigations/{iid}/evidence")).json()
    assert evidence["record_count"] == len(evidence["records"])
    assert evidence["record_count"] > 0
    assert len(evidence["evidence_hash"]) == 64


async def test_evidence_records_are_sealed_by_their_hash(client: AsyncClient) -> None:
    """The published hash must actually be the hash of the published records."""
    from app.investigations.evidence import EvidenceRecord

    inv = await _open(client, ATTRIBUTABLE)
    bundle = (await client.get(f"/investigations/{inv['id']}/evidence")).json()

    recomputed = compute_evidence_hash(
        [EvidenceRecord.model_validate(r) for r in bundle["records"]]
    )
    assert recomputed == bundle["evidence_hash"]


async def test_report_renders_from_the_snapshot(client: AsyncClient) -> None:
    inv = await _open(client, ATTRIBUTABLE)
    resp = await client.get(f"/investigations/{inv['id']}/report")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert inv["id"] in resp.headers["content-disposition"]


# --- the point of the whole design ----------------------------------------


async def test_snapshot_does_not_change_when_the_chain_does(
    client: AsyncClient, session: AsyncSession
) -> None:
    """Yesterday's report must not silently rewrite itself.

    After the investigation completes, every transaction is deleted. A recomputing
    endpoint would now return 'insufficient evidence'; a snapshot-backed one
    returns exactly what it concluded at the time.
    """
    inv = await _open(client, ATTRIBUTABLE)
    iid = inv["id"]
    before = (await client.get(f"/investigations/{iid}/attribution")).json()
    graph_before = (await client.get(f"/investigations/{iid}/graph")).json()

    await session.execute(delete(Transaction))
    await session.commit()

    after = (await client.get(f"/investigations/{iid}/attribution")).json()
    graph_after = (await client.get(f"/investigations/{iid}/graph")).json()
    assert after == before
    assert graph_after == graph_before

    # And a fresh investigation over the emptied store does see the change --
    # proving the first result was frozen, not cached by accident.
    fresh = await _open(client, ATTRIBUTABLE)
    fresh_attr = (await client.get(f"/investigations/{fresh['id']}/attribution")).json()
    assert fresh_attr["insufficient_evidence"] is True


async def test_rerunning_a_finished_investigation_does_not_overwrite_it(
    client: AsyncClient,
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    inv = await _open(client, ATTRIBUTABLE)
    before = (await client.get(f"/investigations/{inv['id']}/evidence")).json()

    row = (
        await session.execute(
            select(Investigation).where(Investigation.public_id == inv["id"])
        )
    ).scalar_one()
    await run_investigation(row.id, sessionmaker=sessionmaker)

    after = (await client.get(f"/investigations/{inv['id']}/evidence")).json()
    assert after["evidence_hash"] == before["evidence_hash"]
    assert after["record_count"] == before["record_count"]


# --- error contracts ------------------------------------------------------


async def test_unknown_investigation_is_404(client: AsyncClient) -> None:
    assert (await client.get("/investigations/INV-2026-99999")).status_code == 404
    resp = await client.get("/investigations/INV-2026-99999/attribution")
    assert resp.status_code == 404


async def test_pending_investigation_returns_409_not_404(
    client: AsyncClient, session: AsyncSession
) -> None:
    """The resource exists; it just has no result yet. A poller must tell these apart."""
    inv = Investigation(
        public_id="INV-2026-00777",
        chain="ethereum",
        address=ATTRIBUTABLE,
        depth=6,
        min_value_wei=0,
        max_nodes=2000,
        status=InvestigationStatus.TRAVERSING,
    )
    session.add(inv)
    await session.commit()

    resp = await client.get("/investigations/INV-2026-00777/attribution")
    assert resp.status_code == 409
    assert "TRAVERSING" in resp.json()["detail"]


async def test_failed_investigation_reports_its_reason(
    client: AsyncClient, session: AsyncSession
) -> None:
    inv = Investigation(
        public_id="INV-2026-00778",
        chain="ethereum",
        address=ATTRIBUTABLE,
        depth=6,
        min_value_wei=0,
        max_nodes=2000,
        status=InvestigationStatus.FAILED,
        error="RuntimeError: provider unreachable",
    )
    session.add(inv)
    await session.commit()

    resp = await client.get("/investigations/INV-2026-00778/risk")
    assert resp.status_code == 409
    assert "provider unreachable" in resp.json()["detail"]


async def test_malformed_address_is_rejected_before_any_work(
    client: AsyncClient,
) -> None:
    resp = await client.post("/investigations", json={"address": "not-an-address"})
    assert resp.status_code == 422


async def test_evm_address_is_rejected_for_a_non_evm_chain(
    client: AsyncClient,
) -> None:
    """An 0x address is not a Bitcoin address; catching it here avoids an
    investigation that traverses nothing and looks like a real 'no evidence' finding."""
    resp = await client.post(
        "/investigations", json={"chain": "bitcoin", "address": "not/a/valid/addr"}
    )
    assert resp.status_code == 422


async def test_address_is_normalized_at_the_boundary(client: AsyncClient) -> None:
    mixed = ATTRIBUTABLE.upper().replace("0X", "0x")
    body = await _open(client, mixed)
    assert body["address"] == ATTRIBUTABLE.lower()


async def test_unknown_case_id_is_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/investigations", json={"address": ATTRIBUTABLE, "case_id": 4242}
    )
    assert resp.status_code == 404


async def test_investigations_can_be_listed_and_filtered_by_case(
    client: AsyncClient,
) -> None:
    case = (await client.post("/cases", json={"name": "Op Cascade"})).json()
    linked = await _open(client, ATTRIBUTABLE, case_id=case["id"])
    await _open(client, DEAD_END)

    all_rows = (await client.get("/investigations")).json()
    assert len(all_rows) >= 2

    filtered = (await client.get(f"/investigations?case_id={case['id']}")).json()
    assert [r["id"] for r in filtered] == [linked["id"]]
