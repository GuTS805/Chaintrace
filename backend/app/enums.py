"""Domain enums shared by ORM models and Pydantic schemas."""

from __future__ import annotations

from enum import StrEnum


class LabelCategory(StrEnum):
    EXCHANGE = "EXCHANGE"
    MIXER = "MIXER"
    SANCTIONED = "SANCTIONED"
    DEFI = "DEFI"
    BRIDGE = "BRIDGE"
    GAMBLING = "GAMBLING"
    SCAM = "SCAM"
    CONTRACT = "CONTRACT"
    OTHER = "OTHER"


class LabelSource(StrEnum):
    ETHEREUM_LISTS = "ETHEREUM_LISTS"
    OFAC_SDN = "OFAC_SDN"
    ETHERSCAN_TAG = "ETHERSCAN_TAG"
    MANUAL = "MANUAL"


class VaspCategory(StrEnum):
    CENTRALIZED_EXCHANGE = "CENTRALIZED_EXCHANGE"
    DEX = "DEX"
    CUSTODIAN = "CUSTODIAN"
    PAYMENT_PROCESSOR = "PAYMENT_PROCESSOR"
    OTHER = "OTHER"


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    CLOSED = "CLOSED"


class FindingSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalType(StrEnum):
    """Attribution evidence signal types (hard requirement schema)."""

    HOP_PATH = "HOP_PATH"
    DEPOSIT_SWEEP = "DEPOSIT_SWEEP"
    COUNTERPARTY_OVERLAP = "COUNTERPARTY_OVERLAP"
    TEMPORAL_CORRELATION = "TEMPORAL_CORRELATION"
    KNOWN_LABEL = "KNOWN_LABEL"
    PATTERN_SIMILARITY = "PATTERN_SIMILARITY"
