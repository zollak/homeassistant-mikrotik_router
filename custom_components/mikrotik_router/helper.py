"""Helper functions for Mikrotik Router."""

from __future__ import annotations

import re


# ---------------------------
#   format_attribute
# ---------------------------
def format_attribute(attr):
    res = attr.replace("-", "_")
    res = res.replace(" ", "_")
    res = res.lower()
    return res


# ---------------------------
#   format_value
# ---------------------------
def format_value(res):
    res = res.replace("dhcp", "DHCP")
    res = res.replace("dns", "DNS")
    res = res.replace("capsman", "CAPsMAN")
    res = res.replace("wireless", "Wireless")
    res = res.replace("restored", "Restored")
    return res


# ---------------------------
#   normalize_routeros_version
# ---------------------------
def normalize_routeros_version(version: str) -> str:
    """Strip channel suffixes like '7.23 (stable)' for version comparisons."""
    match = re.search(r"(\d+\.\d+(?:\.\d+)?)", str(version))
    if not match:
        raise ValueError(f"Version format is not recognized: {version}")
    return match.group(1)


# ---------------------------
#   parse_routeros_major_minor
# ---------------------------
def parse_routeros_major_minor(version: str) -> tuple[int, int]:
    """Return major/minor integers from a RouterOS version string."""
    parts = normalize_routeros_version(version).split(".")
    return int(parts[0]), int(parts[1])
