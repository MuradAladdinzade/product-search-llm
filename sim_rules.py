import re
from enum import Enum
from typing import Optional


class SimCardType(str, Enum):
    PHYSICAL_SINGLE = "PHYSICAL_SINGLE"  # no eSIM slot
    PHYSICAL_DUAL               = "PHYSICAL_DUAL"
    ESIM_ONLY_SINGLE            = "ESIM_ONLY_SINGLE"
    PHYSICAL_PLUS_ESIM          = "PHYSICAL_PLUS_ESIM"


# ── Lookup table: (model_lowercase, country_code) -> SimCardType ──────────────
# Generated from iphone_comprehensive_sim_guide_v2_with_se.csv

SIM_LOOKUP: dict[tuple[str, str], SimCardType] = {
    # iPhone 11
    ("11", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "CN"): SimCardType.PHYSICAL_DUAL,
    ("11", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "HK"): SimCardType.PHYSICAL_DUAL,
    ("11", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 11 Pro
    ("11 pro", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "CN"): SimCardType.PHYSICAL_DUAL,
    ("11 pro", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "HK"): SimCardType.PHYSICAL_DUAL,
    ("11 pro", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 11 Pro Max
    ("11 pro max", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "CN"): SimCardType.PHYSICAL_DUAL,
    ("11 pro max", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "HK"): SimCardType.PHYSICAL_DUAL,
    ("11 pro max", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("11 pro max", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 12
    ("12", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "CN"): SimCardType.PHYSICAL_DUAL,
    ("12", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "HK"): SimCardType.PHYSICAL_DUAL,
    ("12", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 12 Mini
    ("12 mini", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "CN"): SimCardType.PHYSICAL_SINGLE,
    ("12 mini", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "HK"): SimCardType.PHYSICAL_SINGLE,
    ("12 mini", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 mini", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 12 Pro
    ("12 pro", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "CN"): SimCardType.PHYSICAL_DUAL,
    ("12 pro", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "HK"): SimCardType.PHYSICAL_DUAL,
    ("12 pro", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 12 Pro Max
    ("12 pro max", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "CN"): SimCardType.PHYSICAL_DUAL,
    ("12 pro max", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "HK"): SimCardType.PHYSICAL_DUAL,
    ("12 pro max", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("12 pro max", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 13
    ("13", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "CN"): SimCardType.PHYSICAL_DUAL,
    ("13", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "HK"): SimCardType.PHYSICAL_DUAL,
    ("13", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 13 Mini
    ("13 mini", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "CN"): SimCardType.PHYSICAL_SINGLE,
    ("13 mini", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "HK"): SimCardType.PHYSICAL_SINGLE,
    ("13 mini", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 mini", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 13 Pro
    ("13 pro", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "CN"): SimCardType.PHYSICAL_DUAL,
    ("13 pro", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "HK"): SimCardType.PHYSICAL_DUAL,
    ("13 pro", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 13 Pro Max
    ("13 pro max", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "CN"): SimCardType.PHYSICAL_DUAL,
    ("13 pro max", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "HK"): SimCardType.PHYSICAL_DUAL,
    ("13 pro max", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("13 pro max", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 14
    ("14", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "CN"): SimCardType.PHYSICAL_DUAL,
    ("14", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "HK"): SimCardType.PHYSICAL_DUAL,
    ("14", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("14", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 14 Plus
    ("14 plus", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "CN"): SimCardType.PHYSICAL_DUAL,
    ("14 plus", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "HK"): SimCardType.PHYSICAL_DUAL,
    ("14 plus", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 plus", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("14 plus", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 14 Pro
    ("14 pro", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "CN"): SimCardType.PHYSICAL_DUAL,
    ("14 pro", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "HK"): SimCardType.PHYSICAL_DUAL,
    ("14 pro", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("14 pro", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 14 Pro Max
    ("14 pro max", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "CN"): SimCardType.PHYSICAL_DUAL,
    ("14 pro max", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "HK"): SimCardType.PHYSICAL_DUAL,
    ("14 pro max", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("14 pro max", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("14 pro max", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 15
    ("15", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "CN"): SimCardType.PHYSICAL_DUAL,
    ("15", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "HK"): SimCardType.PHYSICAL_DUAL,
    ("15", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("15", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 15 Plus
    ("15 plus", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "CN"): SimCardType.PHYSICAL_DUAL,
    ("15 plus", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "HK"): SimCardType.PHYSICAL_DUAL,
    ("15 plus", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 plus", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("15 plus", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 15 Pro
    ("15 pro", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "CN"): SimCardType.PHYSICAL_DUAL,
    ("15 pro", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "HK"): SimCardType.PHYSICAL_DUAL,
    ("15 pro", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("15 pro", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 15 Pro Max
    ("15 pro max", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "CN"): SimCardType.PHYSICAL_DUAL,
    ("15 pro max", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "HK"): SimCardType.PHYSICAL_DUAL,
    ("15 pro max", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("15 pro max", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("15 pro max", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 16
    ("16", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "CN"): SimCardType.PHYSICAL_DUAL,
    ("16", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "HK"): SimCardType.PHYSICAL_DUAL,
    ("16", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("16", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 16 Plus
    ("16 plus", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "CN"): SimCardType.PHYSICAL_DUAL,
    ("16 plus", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "HK"): SimCardType.PHYSICAL_DUAL,
    ("16 plus", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 plus", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("16 plus", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 16 Pro
    ("16 pro", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "CN"): SimCardType.PHYSICAL_DUAL,
    ("16 pro", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "HK"): SimCardType.PHYSICAL_DUAL,
    ("16 pro", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("16 pro", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 16 Pro Max
    ("16 pro max", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "CN"): SimCardType.PHYSICAL_DUAL,
    ("16 pro max", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "HK"): SimCardType.PHYSICAL_DUAL,
    ("16 pro max", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16 pro max", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("16 pro max", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 16E
    ("16e", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "CN"): SimCardType.PHYSICAL_DUAL,
    ("16e", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "HK"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("16e", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("16e", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 17
    ("17", "AE"): SimCardType.ESIM_ONLY_SINGLE,
    ("17", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17", "CA"): SimCardType.ESIM_ONLY_SINGLE,
    ("17", "CN"): SimCardType.PHYSICAL_DUAL,
    ("17", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17", "HK"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17", "JP"): SimCardType.ESIM_ONLY_SINGLE,
    ("17", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("17", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    
    # iPhone 17 Air
    ("17 air", "AE"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "AU"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "CA"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "CN"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "EU"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "GB"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "HK"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "IN"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "JP"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "KR"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "SG"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 air", "VN"): SimCardType.ESIM_ONLY_SINGLE,
    # iPhone 17 Plus
    ("17 plus", "AE"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 plus", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 plus", "CA"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 plus", "CN"): SimCardType.PHYSICAL_DUAL,
    ("17 plus", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 plus", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 plus", "HK"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 plus", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 plus", "JP"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 plus", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 plus", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 plus", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 plus", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 17 Pro
    ("17 pro", "AE"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro", "CA"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro", "CN"): SimCardType.PHYSICAL_DUAL,
    ("17 pro", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro", "HK"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro", "JP"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 17 Pro Max
    ("17 pro max", "AE"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro max", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro max", "CA"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro max", "CN"): SimCardType.PHYSICAL_DUAL,
    ("17 pro max", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro max", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro max", "HK"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro max", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro max", "JP"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro max", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro max", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17 pro max", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("17 pro max", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone 17E
    ("17e", "AE"): SimCardType.ESIM_ONLY_SINGLE,
    ("17e", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "CA"): SimCardType.ESIM_ONLY_SINGLE,
    ("17e", "CN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "HK"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "JP"): SimCardType.ESIM_ONLY_SINGLE,
    ("17e", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("17e", "US"): SimCardType.ESIM_ONLY_SINGLE,
    ("17e", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone SE (all generations — identical rules)
    ("se", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "CN"): SimCardType.PHYSICAL_SINGLE,
    ("se", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "HK"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("se", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
    # iPhone XR
    ("xr", "AE"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "AU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "CA"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "CN"): SimCardType.PHYSICAL_DUAL,
    ("xr", "EU"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "GB"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "HK"): SimCardType.PHYSICAL_DUAL,
    ("xr", "IN"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "JP"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "KR"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "SG"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "US"): SimCardType.PHYSICAL_PLUS_ESIM,
    ("xr", "VN"): SimCardType.PHYSICAL_PLUS_ESIM,
}


# ── Explicit SIM from text ────────────────────────────────────────────────────

def _from_text(text: str) -> Optional[SimCardType]:
    t, c = text.lower(), text.lower().replace(" ", "")
    has_esim = "esim" in t or "есим" in t or "только esim" in t or "только есим" in t or "толькоesim" in c or "толькоесим" in c
    # "sim"/"сим" alone — not preceded by a digit or "e" (to avoid matching "esim", "2sim")
    has_bare_sim = bool(re.search(r'(?<![0-9e])sim', t) or re.search(r'(?<![0-9])сим', t))
    has_1sim = "1sim" in c or "1сим" in c or has_bare_sim
    has_2sim = "2sim" in c or "2сим" in c

    # Combined sim+esim patterns (check FIRST before esim-only)
    has_sim_plus_esim = (
        (has_1sim and has_esim)
        or "sim-esim" in c or "esim-sim" in c
        or "sim/esim" in c or "esim/sim" in c
        or "sim+esim" in c or "esim+sim" in c
        or "сим-есим" in c or "есим-сим" in c
        or "сим/есим" in c or "есим/сим" in c
        or "сим+есим" in c or "есим+сим" in c
    )

    if has_2sim:          return SimCardType.PHYSICAL_DUAL
    if has_sim_plus_esim: return SimCardType.PHYSICAL_PLUS_ESIM
    if has_esim:          return SimCardType.ESIM_ONLY_SINGLE
    if has_1sim:          return SimCardType.PHYSICAL_PLUS_ESIM
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def resolve_sim_type(
    product_type: Optional[str],
    model: Optional[str],
    country_code: Optional[str],
    requested_text: str = "",
    llm_sim_type: Optional[SimCardType] = None,
) -> dict:
    """
    Priority:
      1. Country present + in lookup → country wins (flag conflict if mismatch)
      2. No country → explicit SIM from text
      3. No text indicator → llm_sim_type (extracted by LLM in Step 1)
      4. Nothing → null
    """
    null = {"simType": None, "simConflict": False, "simExtracted": None, "simCountry": None}

    if not product_type or product_type.lower() != "iphone":
        return null
    if not model:
        return null

    explicit      = _from_text(requested_text)
    cc            = (country_code or "").strip().upper()
    model_key     = model.strip().lower()

    # Normalize SE variants → "se" (e.g. "SE 2", "SE 3", "SE (2nd Gen)", "SE (3rd Gen)")
    if model_key.startswith("se"):
        model_key = "se"

    country_sim   = SIM_LOOKUP.get((model_key, cc))
    best_explicit = explicit or llm_sim_type

    if country_sim is not None:
        return {
            "simType":      country_sim,
            "simConflict":  best_explicit is not None and best_explicit != country_sim,
            "simExtracted": best_explicit,
            "simCountry":   country_sim,
        }

    return {
        "simType":      best_explicit,
        "simConflict":  False,
        "simExtracted": best_explicit,
        "simCountry":   None,
    }


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        # (product_type, model, country, text, expected_sim, expected_conflict)
        ("iPhone", "11",             "US", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "11",             "CN", "",                 "PHYSICAL_DUAL",      False),
        ("iPhone", "11 Pro",         "US", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "12 Mini",        "CN", "",                 "PHYSICAL_SINGLE", False),
        ("iPhone", "13",             "CN", "",                 "PHYSICAL_DUAL",      False),
        ("iPhone", "13",             "IN", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "13",             None, "",                 None,                 False),
        ("iPhone", "13 Mini",        "HK", "",                 "PHYSICAL_SINGLE", False),
        ("iPhone", "14",             "US", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "14",             "IN", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "14",             "HK", "",                 "PHYSICAL_DUAL",      False),
        ("iPhone", "16 Pro",         "US", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "16 Pro",         "IN", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "16 Pro",         "HK", "",                 "PHYSICAL_DUAL",      False),
        ("iPhone", "16 Plus",        "IN", "16 Plus esim 🇮🇳", "PHYSICAL_PLUS_ESIM", True),
        ("iPhone", "16 Plus",        "US", "16 Plus esim 🇺🇸", "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "16 Plus",        None, "16 Plus eSIM",     "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "16 Plus",        None, "16 Plus 2Sim",     "PHYSICAL_DUAL",      False),
        ("iPhone", "16 Plus",        None, "",                 None,                 False),
        ("iPhone", "16E",            "US", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "16E",            "IN", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "17",             "CN", "",                 "PHYSICAL_DUAL",      False),
        ("iPhone", "17",             "IN", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "17",             "JP", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "17",             None, "",                 None,                 False),
        ("iPhone", "17 Air",         "US", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "17 Air",         "IN", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "17 Plus",        "US", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "17 Plus",        "IN", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "17 Pro",         "US", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "17 Pro",         "HK", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "17 Pro Max",     "CA", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "17 Pro Max",     "HK", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "17E",            "US", "",                 "ESIM_ONLY_SINGLE",   False),
        ("iPhone", "17E",            "IN", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "SE",             "US", "",                 "PHYSICAL_PLUS_ESIM", False),
        ("iPhone", "SE",             "CN", "",                 "PHYSICAL_SINGLE", False),
        ("Samsung",     None,        "US", "",                 None,                 False),
        ("Apple Watch", None,        "US", "",                 None,                 False),
    ]

    passed = failed = 0
    for pt, model, cc, text, exp_sim, exp_conflict in cases:
        r = resolve_sim_type(pt, model, cc, text)
        exp_val = SimCardType(exp_sim) if exp_sim else None
        ok = r["simType"] == exp_val and r["simConflict"] == exp_conflict
        if not ok:
            failed += 1
            print(f"❌ {pt} {model!r} cc={cc!r}")
            print(f"   got      simType={r['simType']} conflict={r['simConflict']}")
            print(f"   expected simType={exp_sim} conflict={exp_conflict}")
        else:
            passed += 1
            note = " ⚠ conflict" if r["simConflict"] else ""
            print(f"✅ {pt} {model!r} cc={cc!r} → {r['simType']}{note}")

    print(f"\n{passed} passed, {failed} failed")