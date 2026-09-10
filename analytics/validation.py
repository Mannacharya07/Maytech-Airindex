"""
analytics/validation.py
========================
Statistical validation metrics comparing AirIndex values against benchmark reference data.
Calculates MAE, RMSE, MAPE, and Pearson Correlation Coefficient r.
"""

from __future__ import annotations

import math
from typing import Dict, List


def validate_against_reference(
    airindex_series: List[float],
    reference_series: List[float],
) -> Dict[str, float]:
    """
    Compute statistical validation metrics between AirIndex series and reference series.

    Returns:
    {
        "mae": Mean Absolute Error,
        "rmse": Root Mean Square Error,
        "mape": Mean Absolute Percentage Error (%),
        "pearson_r": Pearson Correlation Coefficient (-1.0 to 1.0)
    }
    """
    if len(airindex_series) != len(reference_series):
        raise ValueError(
            f"Series length mismatch: AirIndex ({len(airindex_series)}) vs Reference ({len(reference_series)})"
        )

    n = len(airindex_series)
    if n == 0:
        return {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "pearson_r": 1.0}

    # 1. MAE
    abs_errors = [abs(a - r) for a, r in zip(airindex_series, reference_series)]
    mae = sum(abs_errors) / n

    # 2. RMSE
    sq_errors = [(a - r) ** 2 for a, r in zip(airindex_series, reference_series)]
    rmse = math.sqrt(sum(sq_errors) / n)

    # 3. MAPE (%)
    mape_errors = [abs(a - r) / r for a, r in zip(airindex_series, reference_series) if r != 0]
    mape = (sum(mape_errors) / len(mape_errors)) * 100 if mape_errors else 0.0

    # 4. Pearson r
    mean_a = sum(airindex_series) / n
    mean_r = sum(reference_series) / n

    cov = sum((a - mean_a) * (r - mean_r) for a, r in zip(airindex_series, reference_series))
    var_a = sum((a - mean_a) ** 2 for a in airindex_series)
    var_r = sum((r - mean_r) ** 2 for r in reference_series)

    denom = math.sqrt(var_a * var_r)
    pearson_r = (cov / denom) if denom != 0 else 1.0

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 4),
        "pearson_r": round(pearson_r, 4),
    }
