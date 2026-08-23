"""Build investigator PDF reports with reportlab."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.report.graph_flowable import GraphFlowable
from app.schemas.attribution import AttributionResult
from app.schemas.case import CaseDetail
from app.schemas.graph import GraphResult
from app.schemas.risk import RiskResult

_TEXT = colors.HexColor(0x1F2328)
_ACCENT = colors.HexColor(0x1F6FEB)
_MUTED = colors.HexColor(0x57606A)
_BORDER = colors.HexColor(0xD0D7DE)
_GOOD = colors.HexColor(0x1A7F37)
_WARN = colors.HexColor(0x9A6700)
_BAD = colors.HexColor(0xD1242F)
_PANEL = colors.HexColor(0xF6F8FA)

Styles = dict[str, ParagraphStyle]

_SIGNAL_LABEL = {
    "HOP_PATH": "hop path",
    "DEPOSIT_SWEEP": "deposit sweep",
    "COUNTERPARTY_OVERLAP": "counterparty overlap",
    "TEMPORAL_CORRELATION": "temporal correlation",
    "KNOWN_LABEL": "known label",
    "PATTERN_SIMILARITY": "pattern similarity",
}


def _pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> Styles:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=18, spaceAfter=2,
            textColor=_TEXT,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=9, textColor=_MUTED,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11, textColor=_ACCENT,
            spaceBefore=12, spaceAfter=4, alignment=TA_LEFT,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=9, leading=13,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontSize=7.5, textColor=_MUTED,
            leading=10,
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["Normal"], fontName="Courier", fontSize=8.5,
        ),
    }


def _header(story: list[Any], s: Styles, title: str, subtitle: str) -> None:
    story.append(Paragraph(_esc(title), s["title"]))
    story.append(Paragraph(_esc(subtitle), s["subtitle"]))


def _kv_table(rows: list[tuple[str, str]], s: Styles) -> Table:
    data = [
        [Paragraph(f"<b>{_esc(k)}</b>", s["small"]), Paragraph(_esc(v), s["body"])]
        for k, v in rows
    ]
    t = Table(data, colWidths=[35 * mm, 130 * mm])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), _PANEL),
            ("GRID", (0, 0), (-1, -1), 0.4, _BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _doc(buf: BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
    )


def build_wallet_report(
    wallet: str,
    attribution: AttributionResult,
    risk: RiskResult,
    graph: GraphResult,
    generated_at: datetime | None = None,
) -> bytes:
    generated_at = generated_at or datetime.now(UTC)
    s = _styles()
    buf = BytesIO()
    doc = _doc(buf, f"Wallet report {wallet}")
    story: list[Any] = []
    _header(
        story,
        s,
        "Wallet Attribution Report",
        "SIH 26182 · law-enforcement crypto tracing · generated "
        f"{generated_at:%Y-%m-%d %H:%M UTC}",
    )

    if attribution.insufficient_evidence:
        verdict, tone = "INSUFFICIENT EVIDENCE", _WARN
    elif attribution.ambiguous:
        verdict, tone = "AMBIGUOUS", _ACCENT
    else:
        verdict, tone = "ATTRIBUTED", _GOOD

    story.append(Paragraph("Subject wallet", s["h2"]))
    story.append(Paragraph(_esc(wallet), s["mono"]))
    story.append(Spacer(1, 6))

    verdict_rows = [("Verdict", verdict)]
    if attribution.candidates:
        top = attribution.candidates[0]
        verdict_rows.append(
            ("Top candidate", f"{top.vasp_name} — {_pct(top.probability)}")
        )
    if attribution.explanation:
        verdict_rows.append(("Explanation", attribution.explanation))
    verdict_rows.append(
        (
            "Model",
            f"{attribution.model_version} "
            f"(threshold {_pct(attribution.confidence_threshold, 0)})",
        )
    )
    vt = _kv_table(verdict_rows, s)
    vt.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (1, 0), (1, 0), tone),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(vt)

    # Candidates table.
    story.append(Paragraph("Candidates", s["h2"]))
    data: list[list[Any]] = [
        [
            Paragraph("<b>VASP</b>", s["small"]),
            Paragraph("<b>Probability</b>", s["small"]),
            Paragraph("<b>Signals</b>", s["small"]),
        ]
    ]
    for c in attribution.candidates:
        data.append(
            [
                Paragraph(_esc(c.vasp_name), s["body"]),
                Paragraph(_pct(c.probability), s["body"]),
                Paragraph(str(len(c.evidence)), s["body"]),
            ]
        )
    if len(data) == 1:
        data.append(
            [Paragraph("—", s["body"]), Paragraph("—", s["body"]), Paragraph("0", s["body"])]
        )
    ct = Table(data, colWidths=[70 * mm, 45 * mm, 50 * mm])
    ct.setStyle(_table_style())
    story.append(ct)

    # Evidence chain.
    story.append(Paragraph("Evidence chain", s["h2"]))
    any_ev = False
    for c in attribution.candidates:
        if not c.evidence:
            continue
        any_ev = True
        story.append(
            Paragraph(f"<b>{_esc(c.vasp_name)}</b> — {_pct(c.probability)}", s["body"])
        )
        for ev in c.evidence:
            label = _SIGNAL_LABEL.get(ev.signal_type, ev.signal_type)
            sign = "+" if ev.weight >= 0 else ""
            line = (
                f"• <b>{_esc(label)}</b> (contribution {sign}{ev.weight:.3f}) — "
                f"{_esc(ev.description)}"
            )
            story.append(Paragraph(line, s["body"]))
            if ev.tx_hashes:
                shown = ", ".join(h[:10] + "…" for h in ev.tx_hashes[:5])
                extra = (
                    f" +{len(ev.tx_hashes) - 5} more" if len(ev.tx_hashes) > 5 else ""
                )
                story.append(Paragraph(f"tx: {_esc(shown)}{extra}", s["small"]))
        story.append(Spacer(1, 4))
    if not any_ev:
        story.append(
            Paragraph("No evidence signals fired for any candidate.", s["body"])
        )

    # Risk (separate).
    story.append(
        Paragraph("Risk (computed independently of attribution)", s["h2"])
    )
    risk_tone = {"LOW": _MUTED, "MEDIUM": _WARN, "HIGH": _BAD, "CRITICAL": _BAD}.get(
        risk.level, _MUTED
    )
    rt = _kv_table(
        [("Level", risk.level), ("Exposure score", _pct(risk.score, 0))], s
    )
    rt.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (1, 0), (1, 0), risk_tone),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(rt)
    for ind in risk.indicators[:6]:
        story.append(
            Paragraph(f"• [{_esc(ind.category)}] {_esc(ind.description)}", s["body"])
        )
    if not risk.indicators:
        story.append(
            Paragraph("No sanctioned / mixer / scam exposure detected.", s["body"])
        )

    # Graph snapshot.
    story.append(Paragraph("Transaction graph snapshot", s["h2"]))
    story.append(GraphFlowable(graph))
    prune = graph.prune
    prune_txt = f"pruned: {', '.join(prune.reasons)}" if prune.pruned else "not pruned"
    story.append(
        Paragraph(
            f"{prune.nodes_visited} nodes, depth {prune.max_depth_reached}, "
            f"{prune_txt}.",
            s["small"],
        )
    )

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Methodology: attribution is heuristics + a calibrated gradient-boosted "
            "classifier; there is no LLM in the attribution path. Every score traces "
            "to the concrete on-chain evidence above. Risk and VASP attribution are "
            "separate, independently computed values.",
            s["small"],
        )
    )

    doc.build(story)
    return buf.getvalue()


def build_case_report(
    case: CaseDetail, generated_at: datetime | None = None
) -> bytes:
    generated_at = generated_at or datetime.now(UTC)
    s = _styles()
    buf = BytesIO()
    doc = _doc(buf, f"Case report {case.id}")
    story: list[Any] = []
    _header(
        story,
        s,
        "Case Report",
        "SIH 26182 · law-enforcement crypto tracing · generated "
        f"{generated_at:%Y-%m-%d %H:%M UTC}",
    )

    story.append(Paragraph("Case summary", s["h2"]))
    story.append(
        _kv_table(
            [
                ("Case", f"#{case.id} · {case.name}"),
                ("Status", case.status),
                ("Investigator", case.investigator or "—"),
                ("Opened", f"{case.created_at:%Y-%m-%d %H:%M}"),
                ("Description", case.description or "—"),
            ],
            s,
        )
    )

    story.append(Paragraph(f"Findings ({len(case.findings)})", s["h2"]))
    if not case.findings:
        story.append(Paragraph("No findings recorded.", s["body"]))
    else:
        data: list[list[Any]] = [
            [
                Paragraph("<b>Severity</b>", s["small"]),
                Paragraph("<b>Finding</b>", s["small"]),
                Paragraph("<b>Wallet</b>", s["small"]),
            ]
        ]
        for f in case.findings:
            note = (
                f"<br/><font size=7 color='#57606A'>{_esc(f.description)}</font>"
                if f.description
                else ""
            )
            data.append(
                [
                    Paragraph(_esc(f.severity), s["small"]),
                    Paragraph(f"<b>{_esc(f.title)}</b>{note}", s["body"]),
                    Paragraph(_esc(f.wallet_address or "—"), s["mono"]),
                ]
            )
        ft = Table(data, colWidths=[22 * mm, 98 * mm, 45 * mm])
        ft.setStyle(_table_style())
        story.append(ft)

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Generated by the VASP Attribution & Investigation Platform. Attribution "
            "confidence and risk indicators are produced by an explainable, calibrated "
            "model with a traceable evidence chain per finding.",
            s["small"],
        )
    )

    doc.build(story)
    return buf.getvalue()
