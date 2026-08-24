"""Case management endpoints (create cases, attach findings/notes).

Every case is owned by the officer who created it; every route below scopes
reads, writes, and deletes to the requesting officer's own cases. A missing
or someone-else's case both 404 (never 403) — an officer must not be able to
learn "case #47 exists, it's just not yours" by probing IDs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_officer
from app.db.session import get_session
from app.models import Case, Finding, Officer
from app.schemas.case import (
    CaseCreate,
    CaseDetail,
    CaseOut,
    FindingCreate,
    FindingOut,
)

router = APIRouter(
    prefix="/cases", tags=["cases"], dependencies=[Depends(get_current_officer)]
)


async def _get_owned_case(
    session: AsyncSession, case_id: int, officer: Officer
) -> Case:
    case = await session.get(Case, case_id)
    if case is None or case.officer_id != officer.id:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(
    payload: CaseCreate,
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> Case:
    case = Case(**payload.model_dump(), officer_id=officer.id)
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


@router.get("", response_model=list[CaseOut])
async def list_cases(
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> list[Case]:
    rows = (
        await session.execute(
            select(Case)
            .where(Case.officer_id == officer.id)
            .order_by(Case.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(
    case_id: int,
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    case = await _get_owned_case(session, case_id, officer)
    findings = (
        await session.execute(
            select(Finding)
            .where(Finding.case_id == case_id)
            .order_by(Finding.created_at.desc())
        )
    ).scalars().all()
    return CaseDetail(
        **CaseOut.model_validate(case).model_dump(),
        findings=[FindingOut.model_validate(f) for f in findings],
    )


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: int,
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> None:
    case = await _get_owned_case(session, case_id, officer)
    await session.delete(case)
    await session.commit()


@router.post("/{case_id}/findings", response_model=FindingOut, status_code=201)
async def add_finding(
    case_id: int,
    payload: FindingCreate,
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> Finding:
    await _get_owned_case(session, case_id, officer)
    finding = Finding(case_id=case_id, **payload.model_dump())
    session.add(finding)
    await session.commit()
    await session.refresh(finding)
    return finding


@router.get("/{case_id}/findings", response_model=list[FindingOut])
async def list_findings(
    case_id: int,
    officer: Officer = Depends(get_current_officer),
    session: AsyncSession = Depends(get_session),
) -> list[Finding]:
    await _get_owned_case(session, case_id, officer)
    rows = (
        await session.execute(
            select(Finding)
            .where(Finding.case_id == case_id)
            .order_by(Finding.created_at.desc())
        )
    ).scalars().all()
    return list(rows)
