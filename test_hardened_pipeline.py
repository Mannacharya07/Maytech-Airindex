"""
test_hardened_pipeline.py
==========================
Unit & Integration tests for hardened pipeline components:
- Dynamic fare decomposer
- Data cleaner & MAD outlier rejection
- DGCA Backtesting engine
- Scheduler control
"""

from collector.decomposer import decompose_fare_dynamic
from collector.cleaner import clean_observation, filter_outliers_mad
from analytics.backtest import compute_backtest_metrics
from collector.scheduler import HarvestScheduler

def test_dynamic_fare_decomposer():
    total_fare = 5420.0
    base, taxes, fees, method = decompose_fare_dynamic(total_fare, origin="DEL")
    assert round(base + taxes + fees, 2) == total_fare
    assert method == "ESTIMATED_DGCA_TAX_MODEL"
    assert base > 0 and taxes > 0 and fees > 0

def test_cleaner_invalid_records():
    assert clean_observation(None) is None
    assert clean_observation({"total_fare": -100}) is None
    assert clean_observation({"total_fare": 0}) is None
    valid = clean_observation({"total_fare": 4500.0, "availability": -2})
    assert valid["availability"] == 0

def test_mad_outlier_filtering():
    obs_list = [
        {"total_fare": 5000.0},
        {"total_fare": 5100.0},
        {"total_fare": 4900.0},
        {"total_fare": 5050.0},
        {"total_fare": 99999.0}, # Spike outlier
    ]
    filtered = filter_outliers_mad(obs_list, threshold=3.0)
    fares = [o["total_fare"] for o in filtered]
    assert 99999.0 not in fares
    assert len(filtered) == 4

def test_backtest_metrics_calculation():
    actual = [100.0, 102.5, 105.0, 108.0]
    reference = [100.0, 102.0, 104.5, 107.5]
    metrics = compute_backtest_metrics(actual, reference)
    assert metrics["mae"] > 0
    assert metrics["rmse"] > 0
    assert metrics["pearson_r"] > 0.9

def test_harvest_scheduler_instantiation():
    sched = HarvestScheduler(interval_seconds=30)
    assert not sched.is_running
    assert sched.interval_seconds == 30
