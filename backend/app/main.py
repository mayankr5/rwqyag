"""FastAPI app: serves the analysis API and (in production) the built React frontend."""
import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import analysis, elexon

# Purchase decisions in January 2026 cover delivery days 2 Jan – 1 Feb.
# Forecasts are fetched from a few days earlier so early-horizon forecasts exist.
FORECAST_FROM = datetime(2025, 12, 29, tzinfo=timezone.utc)
ACTUAL_FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)
DATA_TO = datetime(2026, 2, 2, tzinfo=timezone.utc)
CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path(__file__).resolve().parent.parent / "cache"))

app = FastAPI(title="Wind Forecast Monitor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])


def _cached(name: str, loader):
    path = CACHE_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    data = loader()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


@lru_cache(maxsize=1)
def load_data():
    actuals = _cached("actuals", lambda: elexon.fetch_actuals(ACTUAL_FROM, DATA_TO))
    forecasts = _cached("forecasts", lambda: elexon.fetch_forecasts(FORECAST_FROM, DATA_TO))
    return actuals, forecasts


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/comparison")
def comparison(cutoff_hour: int = Query(9, ge=0, le=23,
                                        description="UK local hour on D-1 when the purchase decision is made")):
    try:
        actuals, forecasts = load_data()
    except Exception as exc:  # upstream outage
        raise HTTPException(502, f"Failed to load Elexon data: {exc}")
    df = analysis.build_comparison(actuals, forecasts, cutoff_hour)
    series = [{"startTime": r.startTime.isoformat(), "actual": r.actual, "forecast": r.forecast,
               "publishTime": r.publishTime.isoformat(), "error": r.error,
               "horizonHours": r.horizonHours}
              for r in df.itertuples()]
    return {"cutoffHour": cutoff_hour, "metrics": analysis.metrics(df),
            "daily": analysis.daily_metrics(df), "series": series}


STATIC = Path(__file__).resolve().parent.parent / "static"
if STATIC.exists():
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
