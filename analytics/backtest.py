"""
analytics/backtest.py
======================
DGCA Price Index Backtesting & Validation Suite.

Evaluates Jevons Geometric Mean Index vs reference price benchmarks:
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- MAPE (Mean Absolute Percentage Error)
- Pearson Correlation (r)
- Tracking Error
"""

from __future__ import annotations

import numpy as np

def compute_backtest_metrics(actual_series: list[float], reference_series: list[float]) -> dict[str, float]:
    """
    Compare generated index series against reference baseline series.
    """
    if not actual_series or not reference_series or len(actual_series) != len(reference_series):
        return {
            "mae": 0.0,
            "rmse": 0.0,
            "mape": 0.0,
            "pearson_r": 0.0,
            "tracking_error": 0.0,
        }

    y_true = np.array(reference_series, dtype=float)
    y_pred = np.array(actual_series, dtype=float)

    mae = float(np.mean(np.abs(y_pred - y_true)))
    rmse = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
    
    # Avoid zero division
    with np.errstate(divide='ignore', invalid='ignore'):
        mape_arr = np.abs((y_true - y_pred) / y_true) * 100.0
        mape_arr = np.nan_to_num(mape_arr, nan=0.0, posinf=0.0, neginf=0.0)
        mape = float(np.mean(mape_arr))

    # Pearson correlation coefficient r
    if np.std(y_true) == 0 or np.std(y_pred) == 0:
        r = 1.0 if np.array_equal(y_true, y_pred) else 0.0
    else:
        r = float(np.corrcoef(y_true, y_pred)[0, 1])

    # Tracking error = std dev of difference
    diff = y_pred - y_true
    tracking_error = float(np.std(diff))

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 4),
        "pearson_r": round(r, 4),
        "tracking_error": round(tracking_error, 4),
    }
