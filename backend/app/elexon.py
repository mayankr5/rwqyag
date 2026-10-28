"""Thin client for the Elexon BMRS stream endpoints (FUELHH actuals, WINDFOR forecasts)."""
from datetime import datetime, timedelta, timezone

import httpx

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_chunked(client: httpx.Client, dataset: str, start: datetime, end: datetime,
                   extra: dict, chunk_days: int = 7) -> list[dict]:
    rows: list[dict] = []
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=chunk_days), end)
        params = {"publishDateTimeFrom": _iso(cur), "publishDateTimeTo": _iso(nxt), **extra}
        resp = client.get(f"{BASE}/{dataset}/stream", params=params, timeout=60)
        resp.raise_for_status()
        rows.extend(resp.json())
        cur = nxt
    return rows


def fetch_actuals(start: datetime, end: datetime) -> list[dict]:
    """Half-hourly outturn wind generation (MW), keyed by startTime."""
    with httpx.Client() as client:
        rows = _fetch_chunked(client, "FUELHH", start, end, {"fuelType": "WIND"})
    return [{"startTime": r["startTime"], "generation": r["generation"]}
            for r in rows if r.get("fuelType") == "WIND"]


def fetch_forecasts(start: datetime, end: datetime) -> list[dict]:
    """Every published hourly wind forecast, with its publishTime."""
    with httpx.Client() as client:
        rows = _fetch_chunked(client, "WINDFOR", start, end, {})
    return [{"startTime": r["startTime"], "publishTime": r["publishTime"],
             "generation": r["generation"]} for r in rows]
