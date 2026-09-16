#!/usr/bin/env python3
"""
GPS ↔ Address consistency checker for city-subject-store.json registry.

Three-layer consistency check:
  1. District-level: reverse-geocode GPS → check district appears in address
  2. GPS duplicate:  same GPS coords used by multiple entries with different addresses
  3. GPS outlier:    GPS coords that are far from the expected bbox for the address city

Nominatim (OpenStreetMap) reverse geocoding — free, no API key, 1 req/sec.

Usage:
    python3 scripts/check_gps_address_consistency.py [--vault <path>] [--limit N] [--json-out <path>] [--delay 1.1]

Output:
    - Console summary of all flagged entries
    - Optional JSON report saved to --json-out
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional


# ── Taiwan geographic helpers ──────────────────────────────────────────────

# Match 區/鄉/鎮 — but NOT preceded by 市/縣 (which are cities, not districts)
# Use a lookahead to skip past city names
_DISTRICT_RE = re.compile(r"(?:市|縣)([\u4e00-\u9fff]+?[區鄉鎮])")
_DISTRICT_SOLO_RE = re.compile(r"^([\u4e00-\u9fff]+?[區鄉鎮])")
_CITY_RE = re.compile(r"([\u4e00-\u9fff]+?[市縣])")

_CITY_ALIASES = {
    "臺北市": "台北市",
    "臺中市": "台中市",
    "臺南市": "台南市",
    "臺東縣": "台東縣",
}

# Approximate bounding boxes for major cities (lat_min, lon_min, lat_max, lon_max)
# Used to detect GPS coords that are way outside their claimed city
# Padding: +0.15° (~16km) to avoid false positives at city borders
_PAD = 0.15
_CITY_BBOX_RAW = {
    "台北市": (24.96, 121.42, 25.18, 121.67),
    "新北市": (24.70, 121.16, 25.30, 122.01),
    "基隆市": (25.05, 121.56, 25.18, 121.84),
    "桃園市": (24.75, 121.08, 25.15, 121.42),
    "新竹市": (24.70, 120.90, 24.85, 121.05),
    "新竹縣": (24.50, 121.00, 24.90, 121.30),
    "苗栗縣": (24.35, 120.55, 24.75, 121.30),
    "台中市": (24.05, 120.52, 24.35, 121.20),
    "彰化縣": (23.80, 120.38, 24.20, 120.75),
    "南投縣": (23.70, 120.50, 24.30, 121.30),
    "雲林縣": (23.50, 120.20, 23.85, 120.70),
    "嘉義市": (23.40, 120.38, 23.52, 120.52),
    "嘉義縣": (23.20, 120.15, 23.60, 120.70),
    "台南市": (22.85, 120.00, 23.30, 120.70),
    "高雄市": (22.40, 120.10, 23.50, 120.75),
    "屏東縣": (21.85, 120.25, 22.70, 120.95),
    "宜蘭縣": (24.30, 121.40, 24.85, 121.90),
    "花蓮縣": (23.10, 121.00, 24.40, 121.80),
    "台東縣": (22.20, 120.80, 23.40, 121.40),
    "澎湖縣": (23.40, 119.20, 23.80, 119.70),
}
_CITY_BBOX = {
    k: (lat_min - _PAD, lon_min - _PAD, lat_max + _PAD, lon_max + _PAD)
    for k, (lat_min, lon_min, lat_max, lon_max) in _CITY_BBOX_RAW.items()
}


@dataclass
class Issue:
    id: str
    store: str
    address: str
    gps: list
    issue_type: str  # "district_mismatch" | "city_bbox_outlier" | "duplicate_gps" | "reverse_geocode_failed"
    detail: str
    reverse_display: str = ""


def normalize_city(name: str) -> str:
    return _CITY_ALIASES.get(name, name)


def extract_district(address: str) -> Optional[str]:
    """Extract district (區/鄉/鎮) name only (without city prefix).

    e.g. "新北市三芝區木屐寮38-1號" → "三芝區"
         "台北市中正區延平南路163巷4號" → "中正區"
    """
    # First try: city precedes district (most common: "新北市三芝區...")
    m = _DISTRICT_RE.search(address)
    if m:
        return m.group(1)
    # Fallback: address starts with district (e.g. "三芝區...")
    m2 = _DISTRICT_SOLO_RE.match(address)
    if m2:
        return m2.group(1)
    return None


def extract_city(address: str) -> Optional[str]:
    """Extract city (市/縣) from address."""
    for m in _CITY_RE.finditer(address):
        return m.group(1)
    return None


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Distance in meters."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def in_bbox(lat, lon, bbox) -> bool:
    lat_min, lon_min, lat_max, lon_max = bbox
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def reverse_geocode(lat: float, lon: float, zoom: int = 14, timeout: float = 10) -> Optional[dict]:
    """Nominatim reverse geocode. Returns address dict or None."""
    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?format=json&lat={lat}&lon={lon}&zoom={zoom}&accept-language=zh-TW"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "PersonalKM-consistency-check/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        if data.get("error"):
            return None
        return data.get("address", {})
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ConnectionResetError):
        return None


def check_district_consistency(entry: dict, delay: float) -> Optional[Issue]:
    """Layer 1: reverse-geocode GPS → check district appears in reverse-geocoded display name.

    Instead of comparing the address district to a single Nominatim field (which
    may be a 里/村里 sub-district), we check whether the address's district name
    appears in the full reverse-geocoded display_name string. This handles cases
    where Nominatim returns "天母" as suburb but the display_name also contains
    "士林區" (the actual district).

    Real mismatches are caught because the display_name won't contain the
    claimed district at all (e.g. address says 信義區 but GPS is in 大安區).
    """
    gps = entry.get("gps")
    if not gps or not isinstance(gps, list) or len(gps) != 2:
        return None
    address = entry.get("address") or ""
    if not address or address == "未提供":
        return None

    lat, lon = float(gps[0]), float(gps[1])
    raddr = reverse_geocode(lat, lon, zoom=18)
    if delay:
        time.sleep(delay)

    if not raddr:
        return Issue(
            id=entry.get("id", ""),
            store=entry.get("store", ""),
            address=address,
            gps=[lat, lon],
            issue_type="reverse_geocode_failed",
            detail="Nominatim returned no result",
        )

    reverse_city = normalize_city(raddr.get("city", "") or raddr.get("county", ""))
    reverse_suburb = raddr.get("suburb", "") or raddr.get("town", "") or raddr.get("city_district", "")
    # Build a display string from all address components for fuzzy district matching
    reverse_display = " ".join(str(v) for v in raddr.values() if isinstance(v, str))

    # Check 1: City mismatch (only if cities are clearly different, not 臺/台 alias)
    addr_city = extract_city(address)
    if addr_city and reverse_city:
        addr_city_norm = normalize_city(addr_city)
        if addr_city_norm != reverse_city:
            return Issue(
                id=entry.get("id", ""),
                store=entry.get("store", ""),
                address=address,
                gps=[lat, lon],
                issue_type="city_mismatch",
                detail=f"city: address={addr_city_norm}, GPS→{reverse_city} ({reverse_suburb})",
                reverse_display=reverse_display,
            )

    # Check 2: District mismatch — check if address district appears in reverse display_name
    addr_district = extract_district(address)
    if addr_district and reverse_display:
        if addr_district not in reverse_display:
            # The district from the address doesn't appear anywhere in the
            # reverse-geocoded location → likely a real mismatch
            return Issue(
                id=entry.get("id", ""),
                store=entry.get("store", ""),
                address=address,
                gps=[lat, lon],
                issue_type="district_mismatch",
                detail=f"district '{addr_district}' not found in GPS reverse→{reverse_display[:60]}",
                reverse_display=reverse_display,
            )

    return None


_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
_DISTANCE_THRESHOLD_M = 500  # flag if forward-geocoded GPS is > 500m from registry GPS


# ── Simplified ↔ Traditional Chinese normalization ──────────────────────────
# Google Places API returns formattedAddress in simplified Chinese when
# languageCode=zh-TW is not respected (common with Taiwan addresses).
# We map common district/county characters so 简体 matches 繁體.

_T2S_MAP = {
    "臺": "台",
    "區": "区",
    "鎮": "镇",
    "鄉": "乡",
    "義": "义",
    "東": "东",
    "後": "后",
    "華": "华",
    "葉": "叶",
    "廣": "广",
    "慶": "庆",
    "濃": "浓",
    "蘆": "芦",
    "關": "关",
    "觀": "观",
    "嶺": "岭",
    "頭": "头",
    "灣": "湾",
    "縣": "县",
    "園": "园",
    "橋": "桥",
    "蓮": "莲",
    "嵐": "岚",
    "島": "岛",
    "嶼": "屿",
}


def _to_simplified(text: str) -> str:
    """Convert common Traditional Chinese characters to Simplified for comparison."""
    if not text:
        return ""
    return "".join(_T2S_MAP.get(c, c) for c in text)


def forward_geocode_places(address: str, api_key: str, timeout: float = 10) -> Optional[tuple[float, float]]:
    """Google Places Text Search: address → (lat, lon). Returns None on failure."""
    req = urllib.request.Request(
        _PLACES_URL,
        data=json.dumps({"textQuery": address}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.location,places.formattedAddress,places.displayName",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        places = data.get("places") or []
        if not places:
            return None
        loc = places[0].get("location") or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None
        return float(lat), float(lon)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ConnectionResetError):
        return None


def forward_geocode_places_full(address: str, api_key: str, timeout: float = 10) -> Optional[dict]:
    """Google Places Text Search: address → {lat, lon, formatted_address, name}. Returns None on failure.

    Richer version of forward_geocode_places that also returns the Google-formatted
    address so we can compare district/city between registry address and Google's.
    """
    req = urllib.request.Request(
        _PLACES_URL,
        data=json.dumps({"textQuery": address, "languageCode": "zh-TW", "regionCode": "TW"}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.location,places.formattedAddress,places.displayName,places.googleMapsUri",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        places = data.get("places") or []
        if not places:
            return None
        p = places[0]
        loc = p.get("location") or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None
        return {
            "lat": float(lat),
            "lon": float(lon),
            "formatted_address": p.get("formattedAddress", ""),
            "name": p.get("displayName", {}).get("text", ""),
            "maps_uri": p.get("googleMapsUri", ""),
        }
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ConnectionResetError):
        return None


def check_places_consistency(entry: dict, api_key: str) -> list[Issue]:
    """Google Places API only: forward geocode address → compare GPS distance AND
    reverse-check district/city from Google's formattedAddress.

    This replaces both Layer 1 (Nominatim reverse) and Layer 4 (forward geocode)
    with a single Google Places call per entry — ~15 seconds for 727 entries.
    """
    gps = entry.get("gps")
    if not gps or not isinstance(gps, list) or len(gps) != 2:
        return []
    address = entry.get("address") or ""
    if not address or address == "未提供":
        return []

    lat_r, lon_r = float(gps[0]), float(gps[1])
    result = forward_geocode_places_full(address, api_key)
    if not result:
        return []  # Places API returned nothing — skip, don't flag

    lat_f, lon_f = result["lat"], result["lon"]
    google_addr = result["formatted_address"]
    distance = haversine_m(lat_r, lon_r, lat_f, lon_f)

    issues: list[Issue] = []

    # Check 1: Forward-geocode distance (same as old Layer 4)
    if distance > _DISTANCE_THRESHOLD_M:
        issues.append(Issue(
            id=entry.get("id", ""),
            store=entry.get("store", ""),
            address=address,
            gps=[lat_r, lon_r],
            issue_type="forward_geocode_distance",
            detail=f"registry GPS ({lat_r:.6f},{lon_r:.6f}) vs address→GPS ({lat_f:.6f},{lon_f:.6f}): {distance:.0f}m apart (> {_DISTANCE_THRESHOLD_M}m)  Google addr: {google_addr}",
        ))

    # Check 2: District mismatch using Google's formattedAddress
    addr_district = extract_district(address)
    if addr_district and google_addr:
        # Google Places returns addresses in simplified Chinese (e.g. 信义区 vs 信義區)
        # Normalize both to simplified for comparison
        import unicodedata
        addr_district_norm = _to_simplified(addr_district)
        google_addr_norm = _to_simplified(google_addr)
        if addr_district_norm not in google_addr_norm:
            issues.append(Issue(
                id=entry.get("id", ""),
                store=entry.get("store", ""),
                address=address,
                gps=[lat_r, lon_r],
                issue_type="district_mismatch",
                detail=f"district '{addr_district}' not in Google addr '{google_addr[:60]}'",
                reverse_display=google_addr,
            ))

    # Check 3: City mismatch using Google's formattedAddress
    addr_city = extract_city(address)
    if addr_city and google_addr:
        addr_city_norm = normalize_city(addr_city)
        # Google returns addresses like "106臺北市大安區..." — extract city from there
        google_city = extract_city(google_addr)
        if google_city:
            google_city_norm = normalize_city(google_city)
            # Also normalize 臺/台 and simplified variants
            addr_city_simplified = _to_simplified(addr_city_norm)
            google_city_simplified = _to_simplified(google_city_norm)
            if addr_city_simplified != google_city_simplified:
                # Skip false positives where Google prepends "台灣" (e.g. "台灣新北市" vs "新北市")
                if google_city_norm.endswith(addr_city_norm) or addr_city_norm.endswith(google_city_norm.replace("台灣", "")):
                    pass  # it's a prefix issue, not a real mismatch
                else:
                    issues.append(Issue(
                        id=entry.get("id", ""),
                        store=entry.get("store", ""),
                        address=address,
                        gps=[lat_r, lon_r],
                        issue_type="city_mismatch",
                        detail=f"city: address={addr_city_norm}, Google→{google_city_norm} ({google_addr[:50]})",
                        reverse_display=google_addr,
                    ))

    return issues


def check_forward_geocode_distance(entry: dict, api_key: str) -> Optional[Issue]:
    """Layer 4: forward-geocode address via Google Places → compare GPS distance."""
    gps = entry.get("gps")
    if not gps or not isinstance(gps, list) or len(gps) != 2:
        return None
    address = entry.get("address") or ""
    if not address or address == "未提供":
        return None

    lat_r, lon_r = float(gps[0]), float(gps[1])
    result = forward_geocode_places(address, api_key)
    if not result:
        return None  # Places API returned nothing — skip, don't flag

    lat_f, lon_f = result
    distance = haversine_m(lat_r, lon_r, lat_f, lon_f)

    if distance > _DISTANCE_THRESHOLD_M:
        return Issue(
            id=entry.get("id", ""),
            store=entry.get("store", ""),
            address=address,
            gps=[lat_r, lon_r],
            issue_type="forward_geocode_distance",
            detail=f"registry GPS ({lat_r:.6f},{lon_r:.6f}) vs address→GPS ({lat_f:.6f},{lon_f:.6f}): {distance:.0f}m apart (> {_DISTANCE_THRESHOLD_M}m)",
        )
    return None


def check_city_bbox(entry: dict) -> Optional[Issue]:
    """Layer 3: GPS coords outside expected bbox for the address city."""
    gps = entry.get("gps")
    if not gps or not isinstance(gps, list) or len(gps) != 2:
        return None
    address = entry.get("address") or ""
    if not address or address == "未提供":
        return None

    addr_city = extract_city(address)
    if not addr_city:
        return None

    addr_city_norm = normalize_city(addr_city)
    bbox = _CITY_BBOX.get(addr_city_norm)
    if not bbox:
        return None  # unknown city, skip

    lat, lon = float(gps[0]), float(gps[1])
    if not in_bbox(lat, lon, bbox):
        return Issue(
            id=entry.get("id", ""),
            store=entry.get("store", ""),
            address=address,
            gps=[lat, lon],
            issue_type="city_bbox_outlier",
            detail=f"GPS ({lat:.4f}, {lon:.4f}) outside {addr_city_norm} bbox {bbox}",
        )

    return None


def find_duplicate_gps(entries: list[dict]) -> list[Issue]:
    """Layer 2: same GPS used by multiple entries with different addresses."""
    gps_map: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        gps = e.get("gps")
        if not gps or not isinstance(gps, list) or len(gps) != 2:
            continue
        # Round to 5 decimal places for grouping
        key = f"{round(float(gps[0]), 5)},{round(float(gps[1]), 5)}"
        gps_map[key].append(e)

    issues = []
    seen_keys = set()
    for key, group in gps_map.items():
        if len(group) < 2:
            continue
        # Check if addresses are actually different (not just formatting)
        addresses = {e.get("address", "") for e in group}
        if len(addresses) < 2:
            continue  # same address, just duplicate entries — not an issue

        # Only report first occurrence to avoid noise
        for entry in group:
            if key in seen_keys:
                continue
            other_stores = [g.get("store", "") for g in group if g is not entry]
            issues.append(
                Issue(
                    id=entry.get("id", ""),
                    store=entry.get("store", ""),
                    address=entry.get("address", ""),
                    gps=[float(entry["gps"][0]), float(entry["gps"][1])],
                    issue_type="duplicate_gps",
                    detail=f"same GPS as: {', '.join(other_stores[:3])}",
                )
            )
            seen_keys.add(key)
            break  # one issue per GPS group
    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Check GPS ↔ address consistency in city-subject-store.json"
    )
    parser.add_argument(
        "--vault",
        default=os.path.expanduser("~/Documents/PersonalKM/Personalkm-lifestyle-vault"),
        help="Vault root path",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit N entries (for testing)")
    parser.add_argument("--json-out", default=None, help="Write JSON report to this path")
    parser.add_argument("--delay", type=float, default=1.1, help="Delay between Nominatim calls (sec)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print every entry being checked")
    parser.add_argument("--skip-reverse", action="store_true", help="Skip Nominatim reverse geocoding (layers 2+3+4 only)")
    parser.add_argument("--places-key-env", default="GOOGLE_PLACES_API_KEY", help="Env var name for Google Places API key")
    parser.add_argument("--skip-places", action="store_true", help="Skip Layer 4 (Google Places forward geocode)")
    parser.add_argument("--places-only", action="store_true",
                        help="Fast mode: use Google Places API for BOTH forward + reverse geocode, skip Nominatim entirely (~15s for 727 entries)")
    args = parser.parse_args()

    vault_path = Path(args.vault)
    registry_path = vault_path / "wiki" / "_registry" / "city-subject-store.json"

    if not registry_path.exists():
        print(f"ERROR: registry not found at {registry_path}", file=sys.stderr)
        sys.exit(1)

    with open(registry_path, encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    with_gps = [e for e in entries if e.get("gps") and isinstance(e["gps"], list) and len(e["gps"]) == 2]
    total = len(with_gps)
    print(f"Total entries: {len(entries)}")
    print(f"Entries with GPS: {total}")
    if args.limit:
        with_gps = with_gps[: args.limit]
        total = len(with_gps)
        print(f"Limiting to first {args.limit}")
    print()

    all_issues: list[Issue] = []

    # ── --places-only fast mode: Google Places for everything, skip Nominatim ──
    if args.places_only:
        places_key = os.getenv(args.places_key_env, "")
        if not places_key:
            print(f"ERROR: --places-only requires {args.places_key_env} env var", file=sys.stderr)
            sys.exit(1)
        print(f"── Places-only mode: Google Places API for forward + reverse geocode ({total} entries) ──")
        distance_issues = 0
        district_issues = 0
        city_issues = 0
        for i, entry in enumerate(with_gps, 1):
            if args.verbose:
                addr_preview = (entry.get("address") or "")[:40]
                print(f"  [{i}/{total}] {entry.get('store','')} — {addr_preview}", flush=True)
            entry_issues = check_places_consistency(entry, places_key)
            for issue in entry_issues:
                all_issues.append(issue)
                if issue.issue_type == "forward_geocode_distance":
                    distance_issues += 1
                elif issue.issue_type == "district_mismatch":
                    district_issues += 1
                elif issue.issue_type == "city_mismatch":
                    city_issues += 1
                if not args.verbose:
                    print(f"  ⚠️  [{i}/{total}] {issue.id} {issue.store}: {issue.detail}")
            if args.verbose and not entry_issues:
                print(f"  ✓  OK", flush=True)
        print(f"  {distance_issues} distance, {district_issues} district, {city_issues} city issues found\n")

        # Also run fast Layer 2 (duplicate GPS, no API) and Layer 3 (bbox, no API)
        print("── Layer 2: Duplicate GPS check ──")
        dup_issues = find_duplicate_gps(with_gps)
        for issue in dup_issues:
            all_issues.append(issue)
            print(f"  ⚠️  {issue.id} {issue.store} ({issue.address[:40]}): {issue.detail}")
        print(f"  {len(dup_issues)} duplicate GPS groups found\n")

        print("── Layer 3: GPS city bbox outlier check ──")
        bbox_count = 0
        for entry in with_gps:
            issue = check_city_bbox(entry)
            if issue:
                all_issues.append(issue)
                bbox_count += 1
                print(f"  ⚠️  {issue.id} {issue.store}: {issue.detail}")
        print(f"  {bbox_count} bbox outliers found\n")

    else:
        # Layer 3: City bbox outlier (fast, no API)
        print("── Layer 3: GPS city bbox outlier check ──")
        bbox_issues = 0
        for entry in with_gps:
            issue = check_city_bbox(entry)
            if issue:
                all_issues.append(issue)
                bbox_issues += 1
                print(f"  ⚠️  {issue.id} {issue.store}: {issue.detail}")
        print(f"  {bbox_issues} bbox outliers found\n")

        # Layer 2: Duplicate GPS (fast, no API)
        print("── Layer 2: Duplicate GPS check ──")
        dup_issues = find_duplicate_gps(with_gps)
        for issue in dup_issues:
            all_issues.append(issue)
            print(f"  ⚠️  {issue.id} {issue.store} ({issue.address[:40]}): {issue.detail}")
        print(f"  {len(dup_issues)} duplicate GPS groups found\n")

        # Layer 4: Google Places forward geocode distance check (fast, 50 req/sec)
        if not args.skip_places:
            places_key = os.getenv(args.places_key_env, "")
            if not places_key:
                print(f"── Layer 4: Skipped (no {args.places_key_env} env var) ──\n")
            else:
                print(f"── Layer 4: Google Places forward-geocode distance check ({total} entries) ──")
                distance_issues = 0
                for i, entry in enumerate(with_gps, 1):
                    if args.verbose:
                        addr_preview = (entry.get("address") or "")[:40]
                        print(f"  [{i}/{total}] {entry.get('store','')} — {addr_preview}", flush=True)
                    issue = check_forward_geocode_distance(entry, places_key)
                    if issue:
                        all_issues.append(issue)
                        distance_issues += 1
                        print(f"  ⚠️  [{i}/{total}] {issue.id} {issue.store}: {issue.detail}")
                    elif args.verbose:
                        print(f"  ✓  OK ({0:.0f}m)", flush=True)
                print(f"  {distance_issues} forward-geocode distance issues found\n")
        else:
            print("── Layer 4: Skipped (--skip-places) ──\n")

        # Layer 1: District-level reverse geocode (slow, Nominatim 1 req/sec)
        if not args.skip_reverse:
            print(f"── Layer 1: District-level reverse geocode check ({total} entries, ~{total * args.delay:.0f}s) ──")
            district_issues_count = 0
            for i, entry in enumerate(with_gps, 1):
                if args.verbose:
                    addr_preview = (entry.get("address") or "")[:40]
                    print(f"  [{i}/{total}] {entry.get('store','')} — {addr_preview}", flush=True)
                issue = check_district_consistency(entry, delay=args.delay)
                if issue:
                    all_issues.append(issue)
                    district_issues_count += 1
                    print(f"  ⚠️  [{i}/{total}] {issue.id} {issue.store}: {issue.detail}")
                elif args.verbose:
                    print(f"  ✓  OK", flush=True)
            print(f"  {district_issues_count} district mismatches found\n")
        else:
            print("── Layer 1: Skipped (--skip-reverse) ──\n")

    # Summary
    print(f"{'='*60}")
    print(f"Checked {total} entries with GPS coordinates")
    print(f"Total issues: {len(all_issues)}")
    if all_issues:
        breakdown = Counter(i.issue_type for i in all_issues)
        print("\nIssue breakdown:")
        for k, v in sorted(breakdown.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

    if args.json_out:
        out_path = Path(args.json_out)
        report = {
            "checked": total,
            "issues": len(all_issues),
            "breakdown": dict(Counter(i.issue_type for i in all_issues)),
            "entries": [asdict(i) for i in all_issues],
        }
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
