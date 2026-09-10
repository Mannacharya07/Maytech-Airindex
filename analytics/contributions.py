"""
analytics/contributions.py
===========================
Index Change Driver Decomposition: answers "Why did the national index change?"
Decomposes index movements into top route contributions & top booking window drivers.
"""

from __future__ import annotations

from typing import Any, Dict, List


def explain_index_change(
    previous_result: Dict[str, Any],
    current_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Decompose national airfare index change between previous and current period.

    Returns explanation contract:
    {
        "national_index_previous": 100.00,
        "national_index_current": 104.20,
        "total_index_change": 4.20,
        "percentage_change": "4.2%",
        "top_routes": [
            {"route": "DEL-BOM", "weight": 0.28, "index_change": 6.43, "contribution": 1.80},
            {"route": "DEL-BLR", "weight": 0.22, "index_change": 5.45, "contribution": 1.20}
        ]
    }
    """
    prev_national = float(previous_result.get("national_index", 100.0))
    curr_national = float(current_result.get("national_index", 100.0))
    total_change = round(curr_national - prev_national, 2)

    prev_routes = previous_result.get("route_indices", {})
    curr_routes = current_result.get("route_indices", {})
    weights = current_result.get("route_weights", {})

    top_routes: List[Dict[str, Any]] = []

    for route, curr_idx in curr_routes.items():
        prev_idx = prev_routes.get(route, 100.0)
        route_delta = curr_idx - prev_idx
        weight = weights.get(route, 0.0)

        # Contribution = Weight * Delta_Route_Index
        contrib = round(weight * route_delta, 2)

        top_routes.append({
            "route": route,
            "weight": weight,
            "weight_percentage": f"{round(weight * 100)}%",
            "previous_index": round(prev_idx, 2),
            "current_index": round(curr_idx, 2),
            "route_index_change": round(route_delta, 2),
            "contribution": contrib,
        })

    # Sort routes by highest magnitude contribution
    top_routes.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    pct_change_str = f"{round(((curr_national - prev_national) / prev_national) * 100, 2)}%"

    return {
        "national_index_previous": prev_national,
        "national_index_current": curr_national,
        "total_index_change": total_change,
        "percentage_change": pct_change_str,
        "top_routes": top_routes,
    }
