"""One-click PDF report generation (reportlab, offline)."""

from app.report.pdf import build_case_report, build_wallet_report

__all__ = ["build_case_report", "build_wallet_report"]
