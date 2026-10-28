import { useEffect, useMemo, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  CartesianGrid, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import './App.css'

const API = import.meta.env.VITE_API_URL ?? ''
const gw = (mw) => (mw / 1000).toFixed(2)
const ukTime = (iso) =>
  new Date(iso).toLocaleString('en-GB', { timeZone: 'Europe/London', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

function Stat({ label, value, hint }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

export default function App() {
  const [cutoffHour, setCutoffHour] = useState(9)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [range, setRange] = useState({ from: '2026-01-01', to: '2026-01-31' })

  useEffect(() => {
    setError(null)
    fetch(`${API}/api/comparison?cutoff_hour=${cutoffHour}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
      .then(setData)
      .catch((e) => setError(e.message))
  }, [cutoffHour])

  const series = useMemo(() => {
    if (!data) return []
    return data.series
      .filter((p) => {
        const day = p.startTime.slice(0, 10)
        return day >= range.from && day <= range.to
      })
      .map((p) => ({ ...p, label: ukTime(p.startTime) }))
  }, [data, range])

  const m = data?.metrics

  return (
    <main>
      <header>
        <h1>GB Wind Forecast Monitor</h1>
        <p>
          Day-ahead wind forecasts vs actual generation, January 2026. For each delivery day we show the
          latest Elexon forecast that existed when the purchase decision was made.
        </p>
      </header>

      <section className="controls">
        <label>
          Decision time (day before, UK)
          <select value={cutoffHour} onChange={(e) => setCutoffHour(Number(e.target.value))}>
            {Array.from({ length: 24 }, (_, h) => (
              <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>
            ))}
          </select>
        </label>
        <label>
          From
          <input type="date" min="2026-01-01" max="2026-02-01" value={range.from}
            onChange={(e) => setRange({ ...range, from: e.target.value })} />
        </label>
        <label>
          To
          <input type="date" min="2026-01-01" max="2026-02-01" value={range.to}
            onChange={(e) => setRange({ ...range, to: e.target.value })} />
        </label>
      </section>

      {error && <div className="error">Could not load data: {error}</div>}
      {!data && !error && <div className="loading">Loading Elexon data…</div>}

      {m && (
        <>
          <section className="stats">
            <Stat label="Mean absolute error" value={`${gw(m.mae)} GW`} hint={`${m.nmaePct.toFixed(1)}% of mean output`} />
            <Stat label="Bias" value={`${m.bias > 0 ? '+' : ''}${gw(m.bias)} GW`} hint={m.bias > 0 ? 'Forecast runs high' : 'Forecast runs low'} />
            <Stat label="90th pct error" value={`${gw(m.p90AbsError)} GW`} hint="9 in 10 hours within this" />
            <Stat label="Worst miss" value={`${gw(m.maxAbsError)} GW`} />
            <Stat label="RMSE" value={`${gw(m.rmse)} GW`} />
          </section>

          <section className="card">
            <h2>Forecast vs actual</h2>
            <ResponsiveContainer width="100%" height={360}>
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                <XAxis dataKey="label" minTickGap={60} tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={gw} unit=" GW" width={70} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => `${gw(v)} GW`} />
                <Legend />
                <Line dataKey="actual" name="Actual" stroke="var(--actual)" dot={false} strokeWidth={2} />
                <Line dataKey="forecast" name="Forecast at decision time" stroke="var(--forecast)" dot={false} strokeWidth={2} strokeDasharray="5 3" />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="card">
            <h2>Daily mean absolute error</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.daily.filter((d) => d.day >= range.from && d.day <= range.to)}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                <XAxis dataKey="day" tickFormatter={(d) => d.slice(8)} tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={gw} unit=" GW" width={70} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => `${gw(v)} GW`} />
                <ReferenceLine y={m.mae} stroke="var(--forecast)" strokeDasharray="4 4" />
                <Bar dataKey="mae" name="MAE" fill="var(--actual)" />
              </BarChart>
            </ResponsiveContainer>
          </section>
        </>
      )}
      <footer>Data: Elexon BMRS (FUELHH wind outturn, WINDFOR forecasts). {m && `${m.count} hourly points.`}</footer>
    </main>
  )
}
