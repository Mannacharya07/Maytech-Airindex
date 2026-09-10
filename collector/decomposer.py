"""
collector/decomposer.py
========================
Dynamic Indian aviation tax decomposition engine.

Calculates realistic fare components (base_fare, taxes, fees) based on:
- GST: 5% on Economy base fare (Indian Statutory Tax rule)
- Airport Fees (PSF/UDF): Route-specific passenger service & user development fees
- Base Fare: Computed remainder ensuring base_fare + taxes + fees == total_fare strictly.
"""

from __future__ import annotations

# Airport PSF (Passenger Service Fee) + UDF (User Development Fee) averages in INR by origin airport
AIRPORT_FEE_MAP = {
    "DEL": 420.0,
    "BOM": 380.0,
    "BLR": 350.0,
    "CCU": 290.0,
    "HYD": 310.0,
    "MAA": 280.0,
}

def decompose_fare_dynamic(total_fare: float, origin: str = "DEL") -> tuple[float, float, float, str]:
    """
    Decompose total fare into (base_fare, taxes, fees, method).
    
    Guarantees: round(base_fare + taxes + fees, 2) == round(total_fare, 2)
    """
    if total_fare <= 0:
        return 0.0, 0.0, 0.0, "INVALID"

    # Fixed airport user fee estimate based on origin airport
    fees = round(AIRPORT_FEE_MAP.get(origin.upper(), 350.0), 2)
    
    # If total fare is unusually low, adjust fees to not exceed 25% of total
    if fees >= total_fare * 0.25:
        fees = round(total_fare * 0.08, 2)

    # Taxable amount excluding fixed fees
    taxable_remainder = total_fare - fees
    
    # GST is ~5% of base_fare => taxable_remainder = base_fare * 1.05
    base_fare = round(taxable_remainder / 1.05, 2)
    taxes = round(total_fare - base_fare - fees, 2)

    return base_fare, taxes, fees, "ESTIMATED_DGCA_TAX_MODEL"
