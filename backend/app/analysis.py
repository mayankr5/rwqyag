"""Core logic: pick the forecast a day-ahead trader actually had, and score it."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

UK = ZoneInfo("Europe/London")


def decision_cutoff(delivery_day, cutoff_hour: int) -> pd.Timestamp:
    """The day-ahead decision for delivery_day is made on the previous day at cutoff_hour UK time."""
    local = datetime.combine(delivery_day - timedelta(days=1), time(cutoff_hour), tzinfo=UK)
    return pd.Timestamp(local).tz_convert("UTC")


def build_comparison(actuals: list[dict], forecasts: list[dict], cutoff_hour: int) -> pd.DataFrame:
    """One row per forecast target hour: actual MW, decision-time forecast MW, error."""
    act = pd.DataFrame(actuals)
    fc = pd.DataFrame(forecasts)
    if act.empty or fc.empty:
        return pd.DataFrame(columns=["startTime", "actual", "forecast", "publishTime", "error"])

    act["startTime"] = pd.to_datetime(act["startTime"], utc=True)
    act = act.drop_duplicates("startTime").rename(columns={"generation": "actual"})

    fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    # The delivery day is the UK local date of the target period.
    fc["deliveryDay"] = fc["startTime"].dt.tz_convert(UK).dt.date
    fc["cutoff"] = fc["deliveryDay"].map(lambda d: decision_cutoff(d, cutoff_hour))

    # Only forecasts that existed at decision time; keep the latest one per target.
    usable = fc[fc["publishTime"] <= fc["cutoff"]]
    latest = (usable.sort_values("publishTime")
                    .groupby("startTime", as_index=False).last()
                    .rename(columns={"generation": "forecast"}))

    out = latest.merge(act, on="startTime", how="inner")
    out["error"] = out["forecast"] - out["actual"]
    out["horizonHours"] = (out["startTime"] - out["publishTime"]).dt.total_seconds() / 3600
    return out[["startTime", "actual", "forecast", "publishTime", "error", "horizonHours"]] \
        .sort_values("startTime").reset_index(drop=True)


def metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    err = df["error"]
    abs_err = err.abs()
    return {
        "count": int(len(df)),
        "mae": float(abs_err.mean()),
        "rmse": float((err ** 2).mean() ** 0.5),
        "bias": float(err.mean()),
        "p50AbsError": float(abs_err.quantile(0.5)),
        "p90AbsError": float(abs_err.quantile(0.9)),
        "maxAbsError": float(abs_err.max()),
        "meanActual": float(df["actual"].mean()),
        # Normalised MAE: error relative to average output, robust to near-zero hours.
        "nmaePct": float(abs_err.sum() / df["actual"].sum() * 100),
    }


def daily_metrics(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    d = df.assign(day=df["startTime"].dt.tz_convert(UK).dt.date)
    g = d.groupby("day").agg(mae=("error", lambda e: e.abs().mean()),
                             bias=("error", "mean"),
                             actualMWh=("actual", "sum"),
                             forecastMWh=("forecast", "sum"))
    return [{"day": str(k), **{c: float(v) for c, v in row.items()}} for k, row in g.iterrows()]
