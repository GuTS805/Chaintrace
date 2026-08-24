"""SAHYOG-Portal disclosure-request generator.

Turns an attribution result into a ready lawful-information-request draft an
authorized officer can file with the attributed VASP via India's SAHYOG Portal
(I4C, Ministry of Home Affairs) — bridging attribution to the actual LEA action.

`disclosure_sections` (the request content/wording) was drafted with the peer
`devcon-1d` session; it is rendered here through reportlab. The document is a
clearly-marked DRAFT with no legal effect until filed by a competent authority.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas.attribution import AttributionResult
from app.schemas.risk import RiskResult

_ACCENT = colors.HexColor(0x1F3A8A)
_MUTED = colors.HexColor(0x57606A)
_TEXT = colors.HexColor(0x1F2328)

PDF_TITLE = "Request for Information under Lawful Process — SAHYOG Portal (I4C, MHA)"


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def disclosure_filename(wallet: str, vasp_name: str) -> str:
    ref = datetime.now(UTC).strftime("%Y%m%d")
    return f"SAHYOG_Disclosure_{_slug(vasp_name)}_{wallet[2:10]}_{ref}.pdf"


def disclosure_sections(
    wallet: str,
    vasp_name: str,
    probability: float,
    hops: int,
    tx_hashes: list[str],
    risk_level: str,
    risk_notes: list[str],
    *,
    officer_name: str | None = None,
    officer_department: str | None = None,
) -> list[tuple[str, list[str]]]:
    """Ordered (heading, body_lines) for a SAHYOG disclosure-request draft.

    `officer_name`/`officer_department` come from the authenticated session that
    requested the report; when absent the field stays an explicit placeholder for
    manual completion, same as every other field a signing officer must supply.
    """
    hop_word = "hop" if hops == 1 else "hops"
    confidence_pct = f"{probability * 100:.1f}%"
    officer_line = (
        f"Investigating Officer (Name & Designation): {officer_name}"
        if officer_name
        else "Investigating Officer (Name & Designation): [Insert Officer Details]"
    )
    lea_line = (
        f"Requesting Law Enforcement Agency: {officer_department}"
        if officer_department
        else "Requesting Law Enforcement Agency: [Insert LEA Name]"
    )

    return [
        (
            "Draft — For Use by Authorized Law Enforcement Personnel Only",
            [
                "This is a system-generated draft prepared for submission by an "
                "authorized officer through the official SAHYOG Portal maintained "
                "by the Indian Cyber Crime Coordination Centre (I4C), Ministry of "
                "Home Affairs. It carries no legal effect until reviewed, "
                "completed, and filed by a competent authority under applicable law.",
            ],
        ),
        (
            "Reference & Authority",
            [
                "Indian Cyber Crime Coordination Centre (I4C)",
                "Cyber & Information Security (CIS) Division",
                "Ministry of Home Affairs, Government of India",
                "Channel of submission: SAHYOG Portal",
                lea_line,
                officer_line,
                "Case / FIR No.: [Insert Case or FIR Number]",
                "Date of Request: [Insert Date]",
                "Internal Reference No.: [Insert Reference Number]",
            ],
        ),
        (
            "Subject of Request",
            [
                f"Virtual digital asset (VDA) wallet address under investigation: {wallet}",
                f"Attributed Virtual Asset Service Provider (VASP): {vasp_name}",
                f"Attribution confidence: {confidence_pct}",
                f"Attribution basis: nearest deposit-accepting exchange address, "
                f"{hops} {hop_word} from the subject wallet on the traced "
                f"transaction graph.",
            ],
        ),
        (
            "Basis for Request — On-Chain Evidence",
            [
                f"The attribution above rests on {len(tx_hashes)} on-chain "
                f"transaction(s) linking the subject wallet to an account believed "
                f"to be held at {vasp_name}:",
                *[f"  - Transaction hash: {h}" for h in tx_hashes],
                "The full transaction graph and attribution methodology are "
                "available on request and can be furnished as a supporting annexure.",
            ],
        ),
        (
            "Risk Indicators",
            [
                f"Assessed risk level: {risk_level}",
                *(
                    risk_notes
                    if risk_notes
                    else [
                        "No specific risk indicators beyond standard investigative "
                        "due diligence."
                    ]
                ),
            ],
        ),
        (
            "Information Requested",
            [
                f"{vasp_name} is requested to furnish the following, to the extent "
                f"held in the ordinary course of its Know Your Customer (KYC) and "
                f"record-keeping obligations, for the account(s) controlling the "
                f"deposit address identified above:",
                "  1. Full KYC records: legal name, government ID details, date of "
                "birth, registered address, and photograph on file.",
                "  2. Account opening details and complete account statement / "
                "transaction ledger for the relevant period.",
                "  3. Linked payment instruments: bank account(s), UPI ID(s), "
                "card(s), or other fiat on/off-ramp details.",
                "  4. Login and access logs, including IP addresses, device "
                "identifiers, and timestamps, for the relevant period.",
                "  5. Beneficial ownership details, where the account is held in a "
                "corporate, trust, or nominee capacity.",
                "  6. Current balance held in the account, and confirmation of "
                "whether a freeze on further withdrawals can be effected pending "
                "formal legal process.",
            ],
        ),
        (
            "Legal Basis & Confidentiality",
            [
                "This request is made in connection with a lawful investigation and "
                "is issued under applicable Indian law governing production of "
                "information by intermediaries and virtual digital asset service "
                "providers. It is submitted through the SAHYOG Portal as the "
                "designated channel for such requests to VASPs operating in or "
                "serving users in India.",
                f"{vasp_name} and its personnel are requested to treat this request, "
                f"and the fact of its receipt, as confidential, and not to disclose "
                f"its existence to the account holder(s) concerned where such "
                f"disclosure would prejudice the investigation, except as required "
                f"by law.",
            ],
        ),
        (
            "Response Requested By",
            [
                "A response is requested within [Insert Response Deadline, e.g. 15 "
                "days] of receipt, or such shorter period as applicable law or the "
                "urgency of the matter requires.",
                "For queries regarding this request, please contact the "
                "investigating officer named above through official channels only.",
            ],
        ),
    ]


def build_disclosure_request(
    wallet: str,
    attribution: AttributionResult,
    risk: RiskResult,
    *,
    hops: int,
    tx_hashes: list[str],
    officer_name: str | None = None,
    officer_department: str | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    if not attribution.candidates:
        raise ValueError("No attributed VASP — cannot generate a disclosure request.")
    generated_at = generated_at or datetime.now(UTC)
    top = attribution.candidates[0]

    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "t", parent=base["Title"], fontSize=15, textColor=_TEXT, spaceAfter=2
    )
    sub_style = ParagraphStyle(
        "s", parent=base["Normal"], fontSize=8.5, textColor=_MUTED, spaceAfter=10
    )
    h2 = ParagraphStyle(
        "h", parent=base["Heading2"], fontSize=11, textColor=_ACCENT,
        spaceBefore=10, spaceAfter=3,
    )
    body = ParagraphStyle("b", parent=base["Normal"], fontSize=9, leading=13)
    mono = ParagraphStyle(
        "m", parent=base["Normal"], fontName="Courier", fontSize=8, leading=11
    )

    sections = disclosure_sections(
        wallet=wallet,
        vasp_name=top.vasp_name,
        probability=top.probability,
        hops=hops,
        tx_hashes=tx_hashes,
        risk_level=risk.level,
        risk_notes=[i.description for i in risk.indicators]
        + [t.description for t in risk.typology_tags],
        officer_name=officer_name,
        officer_department=officer_department,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm, title=PDF_TITLE,
    )
    story: list[Any] = [
        Paragraph(_esc(PDF_TITLE), title_style),
        Paragraph(
            f"System-generated draft · {generated_at:%Y-%m-%d %H:%M UTC} · "
            f"model {attribution.model_version}",
            sub_style,
        ),
    ]
    for heading, lines in sections:
        story.append(Paragraph(_esc(heading), h2))
        for line in lines:
            style = mono if "0x" in line else body
            story.append(Paragraph(_esc(line), style))
        story.append(Spacer(1, 4))

    doc.build(story)
    return buf.getvalue()
