from app.analysis import build_comparison, metrics


def test_picks_latest_forecast_before_cutoff():
    # Delivery 2026-01-10 12:00Z; cutoff = 2026-01-09 09:00 UK (= 09:00Z in winter).
    actuals = [{"startTime": "2026-01-10T12:00:00Z", "generation": 1000}]
    forecasts = [
        {"startTime": "2026-01-10T12:00:00Z", "publishTime": "2026-01-08T20:00:00Z", "generation": 700},
        {"startTime": "2026-01-10T12:00:00Z", "publishTime": "2026-01-09T08:30:00Z", "generation": 900},
        # Published after the cutoff: trader could not have seen it.
        {"startTime": "2026-01-10T12:00:00Z", "publishTime": "2026-01-09T10:00:00Z", "generation": 1000},
    ]
    df = build_comparison(actuals, forecasts, cutoff_hour=9)
    assert len(df) == 1
    assert df.loc[0, "forecast"] == 900
    assert df.loc[0, "error"] == -100


def test_metrics():
    actuals = [{"startTime": f"2026-01-10T1{h}:00:00Z", "generation": 1000} for h in range(2)]
    forecasts = [
        {"startTime": "2026-01-10T10:00:00Z", "publishTime": "2026-01-09T00:00:00Z", "generation": 1100},
        {"startTime": "2026-01-10T11:00:00Z", "publishTime": "2026-01-09T00:00:00Z", "generation": 700},
    ]
    m = metrics(build_comparison(actuals, forecasts, cutoff_hour=9))
    assert m["mae"] == 200
    assert m["bias"] == -100
    assert m["maxAbsError"] == 300
