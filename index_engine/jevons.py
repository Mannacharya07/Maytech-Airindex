"""
index_engine/jevons.py
======================
Jevons Index calculation using Geometric Mean aggregation of price relatives.

Why Jevons (Geometric Mean)?
----------------------------
1. Time-reversibility property (passing base vs current swaps ratio cleanly).
2. Avoids upward bias present in arithmetic mean of price ratios (Carli index bias).
3. Standard method recommended by ILO/IMF/WB for elementary price index aggregation.
"""

from __future__ import annotations

import math
from typing import Sequence


def compute_jevons_index(price_relatives: Sequence[float]) -> float:
    """
    Compute Jevons Index value.

    Formula:
        Jevons Index = 100 * exp( (1/N) * sum( ln(price_relative_i) ) )

    Returns 100.0 if relatives list is empty.
    """
    if not price_relatives:
        return 100.0

    valid_relatives = [r for r in price_relatives if r > 0]
    if not valid_relatives:
        raise ValueError("Price relatives list contains no positive numbers")

    # Sum of logarithms avoids floating-point overflow for large N
    log_sum = sum(math.log(r) for r in valid_relatives)
    geometric_mean = math.exp(log_sum / len(valid_relatives))

    return round(100.0 * geometric_mean, 2)
