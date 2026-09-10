"""
analytics/lead_time.py
======================
Lead-time fare curve analysis across advance-purchase booking windows:
T+45 -> T+30 -> T+15 -> T+7 -> T+1
"""

from __future__ import annotations

from typing import Any, Dict, List

WINDOW_ORDER = ["T+45", "T+30", "T+15", "T+7", "T+1"]


def compute_lead_time_curve(
    observations: List[Dict[str, Any]],
    route: str = "DEL-BOM",
) -> Dict[str, Any]:
    """
    Compute advance booking window pricing curve for a specific route.

    Returns dict formatted for dashboard lead-time charts:
    {
        "route": "DEL-BOM",
        "curve": [
            {"booking_window": "T+45", "avg_total_fare": 3900.0, ...},
            ...
        ]
    }
    """
    parts = route.upper().split("-")
    origin = parts[0] if len(parts) == 2 else "DEL"
    dest = parts[1] if len(parts) == 2 else "BOM"

    # Filter observations by route
    filtered = [
        o for o in observations
        if str(o.get("origin")).upper() == origin and str(o.get("destination")).upper() == dest
    ]

    by_window: Dict[str, List[Dict[str, Any]]] = {}
    for o in filtered:
        bw = str(o.get("booking_window", "")).strip()
        by_window.setdefault(bw, []).append(o)

    curve_items = []
    for bw in WINDOW_ORDER:
        obs_list = by_window.get(bw, [])
        if not obs_list:
            continue

        avg_total = sum(float(o["total_fare"]) for o in obs_list) / len(obs_list)
        avg_base = sum(float(o["base_fare"]) for o in obs_list) / len(obs_list)
        avg_taxes = sum(float(o["taxes"]) for o in obs_list) / len(obs_list)

        curve_items.append({
            "booking_window": bw,
            "avg_total_fare": round(avg_total, 2),
            "avg_base_fare": round(avg_base, 2),
            "avg_taxes": round(avg_taxes, 2),
            "sample_count": len(obs_list),
        })

    return {
        "route": f"{origin}-{dest}",
        "curve": curve_items,
    }
