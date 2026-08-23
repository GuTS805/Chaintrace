"""One-click PDF report generation (reportlab, offline)."""

from app.report.pdf import build_case_report, build_wallet_report
from app.report.sahyog import build_disclosure_request, disclosure_filename

__all__ = [
    "build_case_report",
    "build_disclosure_request",
    "build_wallet_report",
    "disclosure_filename",
]
