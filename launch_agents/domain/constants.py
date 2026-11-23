"""Shared constants (ADR-0008, ADR-0031, ADR-0041).

This is the only source file in ``launch_agents/`` that spells out the brand name; every
other module reads ``BRAND_NAME`` or ``Settings.brand_name`` (ADR-0041).
"""

from __future__ import annotations

__all__ = [
    "AUTHORIZED_SHARES",
    "BRAND_NAME",
    "DEFAULT_CLIFF_MONTHS",
    "DEFAULT_SITE_PAGES",
    "DEFAULT_VESTING_MONTHS",
    "DOMAIN_TLDS",
    "ELECTION_83B_DAYS",
    "EQUITY_DECIMALS",
    "ESIGN_CONSENT_TEXT",
    "ESIGN_CONSENT_VERSION",
    "FULL_GUIDE_STATES",
    "LEGAL_NOTICE",
    "MAX_QA_FIX_ROUNDS",
    "USPTO_TRADEMARK_SEARCH_URL",
]

# Brand (ADR-0041: the product owner renamed the product Keelstart; supersedes ADR-0039).
BRAND_NAME = "Keelstart"

# Case rules (ADR-0008, ADR-0013).
AUTHORIZED_SHARES = 10_000_000
DEFAULT_VESTING_MONTHS = 48
DEFAULT_CLIFF_MONTHS = 12
ELECTION_83B_DAYS = 30
MAX_QA_FIX_ROUNDS = 2
DOMAIN_TLDS = (".com", ".co", ".io")  # checked in this order
FULL_GUIDE_STATES = ("DE", "WY")
DEFAULT_SITE_PAGES = ("Home", "About", "Services", "Contact")
EQUITY_DECIMALS = 2  # max decimal places of equity_percent
LEGAL_NOTICE = (
    "This is not legal advice. It was generated automatically; "
    "have a licensed attorney review it before you rely on it."
)
USPTO_TRADEMARK_SEARCH_URL = "https://tmsearch.uspto.gov/search/search-information"

# Electronic signatures (ADR-0031).
ESIGN_CONSENT_VERSION = "2026-11-23"
ESIGN_CONSENT_TEXT = (
    "I agree to sign this document electronically. I understand my typed name is my "
    "signature and has the same effect as a handwritten signature, and that a record of "
    "this signature (time, account, IP address and a fingerprint of the document) is kept."
)
