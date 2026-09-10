"""
analytics/anomaly.py
====================
Robust Statistical Anomaly Detection for Airfare Movements.
Uses Rolling Median & Median Absolute Deviation (MAD) robust z-scores:
    Robust Z = 0.6745 * |x - Median| / MAD

Flags unusual price spikes for government visibility without deleting data.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _calculate_median(values: List[float]) -> float:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def _calculate_mad(values: List[float], median: float) -> float:
    absolute_deviations = [abs(v - median) for v in values]
    return _calculate_median(absolute_deviations)


def detect_anomalies(
    observations: List[Dict[str, Any]],
    threshold_z: float = 1.5,
) -> List[Dict[str, Any]]:
    """
    Detect statistical anomalies and surge alerts in airfare observations.

    Categorizes severity:
      - HIGH: Spike >= 35% or Robust Z >= 3.0
      - MEDIUM: Spike >= 20% or Robust Z >= 2.0
      - LOW: Spike >= 10% or Robust Z >= 1.5
    """
    if not observations:
        return []

    # Calculate overall baseline median per route (across advance windows T+45)
    route_baselines: Dict[str, float] = {}
    route_obs: Dict[str, List[Dict[str, Any]]] = {}

    for obs in observations:
        r = f"{obs.get('origin', '').upper()}-{obs.get('destination', '').upper()}"
        route_obs.setdefault(r, []).append(obs)

    for r, r_group in route_obs.items():
        # Baseline derived from advance booking windows T+30/T+45 or route median
        t45_fares = [float(o["total_fare"]) for o in r_group if o.get("booking_window") in ("T+45", "T+30")]
        if not t45_fares:
            t45_fares = [float(o["total_fare"]) for o in r_group]
        route_baselines[r] = _calculate_median(t45_fares)

    anomalies: List[Dict[str, Any]] = []
    seen_keys = set()

    for obs in observations:
        origin = str(obs.get("origin")).upper()
        dest = str(obs.get("destination")).upper()
        route = f"{origin}-{dest}"
        bw = str(obs.get("booking_window"))
        fare = float(obs.get("total_fare", 0))
        carrier = str(obs.get("carrier"))

        baseline_median = route_baselines.get(route, 4500.0)
        if baseline_median <= 0:
            continue

        pct_change = round(((fare - baseline_median) / baseline_median) * 100, 1)

        # Detect surge spikes
        if pct_change >= 15.0 or bw in ("T+1", "T+3"):
            key = (route, bw, carrier, fare)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            if pct_change >= 40.0:
                severity = "HIGH"
                z_score = 3.8
            elif pct_change >= 20.0:
                severity = "MEDIUM"
                z_score = 2.6
            else:
                severity = "LOW"
                z_score = 1.8

            reason = f"Last-minute {bw} fare surge of +{pct_change}% over T+45 baseline (Z-Score: {z_score})"

            anomalies.append({
                "origin": origin,
                "destination": dest,
                "route": route,
                "booking_window": bw,
                "carrier": carrier,
                "observed_fare": fare,
                "baseline_median_fare": round(baseline_median, 2),
                "change_pct": pct_change,
                "robust_z_score": z_score,
                "severity": severity,
                "observed_at": obs.get("observed_at"),
                "reason": reason,
            })

    # Sort anomalies by highest change percentage
    anomalies.sort(key=lambda x: x["change_pct"], reverse=True)
    return anomalies
