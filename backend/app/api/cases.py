"""Case management endpoints (create cases, attach findings/notes)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Case, Finding
from app.schemas.case import (
    CaseCreate,
    CaseDetail,
    CaseOut,
    FindingCreate,
    FindingOut,
)

router = APIRouter(prefix="/cases", tags=["cases"])


async def _get_case(session: AsyncSession, case_id: int) -> Case:
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(
    payload: CaseCreate, session: AsyncSession = Depends(get_session)
) -> Case:
    case = Case(**payload.model_dump())
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


@router.get("", response_model=list[CaseOut])
async def list_cases(session: AsyncSession = Depends(get_session)) -> list[Case]:
    rows = (
        await session.execute(select(Case).order_by(Case.created_at.desc()))
    ).scalars().all()
    return list(rows)


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(
    case_id: int, session: AsyncSession = Depends(get_session)
) -> CaseDetail:
    case = await _get_case(session, case_id)
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
    case_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    case = await _get_case(session, case_id)
    await session.delete(case)
    await session.commit()


@router.post("/{case_id}/findings", response_model=FindingOut, status_code=201)
async def add_finding(
    case_id: int,
    payload: FindingCreate,
    session: AsyncSession = Depends(get_session),
) -> Finding:
    await _get_case(session, case_id)
    finding = Finding(case_id=case_id, **payload.model_dump())
    session.add(finding)
    await session.commit()
    await session.refresh(finding)
    return finding


@router.get("/{case_id}/findings", response_model=list[FindingOut])
async def list_findings(
    case_id: int, session: AsyncSession = Depends(get_session)
) -> list[Finding]:
    await _get_case(session, case_id)
    rows = (
        await session.execute(
            select(Finding)
            .where(Finding.case_id == case_id)
            .order_by(Finding.created_at.desc())
        )
    ).scalars().all()
    return list(rows)
