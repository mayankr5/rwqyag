# GB Wind Forecast Monitor

A web app for a UK utility's day-ahead trading desk. It shows the **latest wind generation forecast available at the moment a day-ahead purchase decision is made**, compares it with actual generation, and measures the forecast error, for decisions made in January 2026.

## How it works
- **Actuals:** Elexon `FUELHH` (fuelType `WIND`), half-hourly MW.
- **Forecasts:** Elexon `WINDFOR`, hourly MW, re-published about 8 times a day.
- **Decision-time forecast:** for delivery day *D*, the decision is made on *D-1* at a configurable UK hour (09:00 by default). For each target hour we take the most recent forecast with `publishTime <= cutoff`. Later, more accurate forecasts are excluded because the trader couldn't have seen them.
- **Metrics:** MAE, RMSE, bias, P50/P90 absolute error, worst miss, and normalised MAE (% of mean output), plus a daily breakdown.

## Repository layout
```
backend/            Python (FastAPI)
  app/elexon.py     Elexon BMRS client (chunked stream fetches)
  app/analysis.py   Decision-time forecast selection + error metrics
  app/main.py       API (/api/comparison, /api/health) + serves the built frontend
  tests/            pytest unit tests for the selection logic and metrics
  cache/            JSON cache of fetched data (created at runtime)
frontend/           React (Vite) + Recharts dashboard
  src/App.jsx       Controls, KPI tiles, forecast-vs-actual and daily error charts
Dockerfile          Multi-stage build: frontend -> static files served by FastAPI
heroku.yml          Heroku container deploy
```

## Running it
**Docker (recommended)**
```bash
docker build -t wind-monitor .
docker run -p 8000:8000 wind-monitor   # open http://localhost:8000
```

**Local development**
```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload          # API on :8000
cd frontend && npm install && npm run dev        # UI on :5173 (proxies /api)
cd backend && .venv/bin/pytest                    # tests
```

## Deployment
Heroku (container stack):
```bash
heroku create && heroku stack:set container && git push heroku main
```
Live app: _TODO: add link_

## AI usage
This project was built with help from Claude Code (Anthropic) for scaffolding, code and documentation. All logic was reviewed and checked against live Elexon data.
