import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency, formatMonth } from '../lib/format'

function buildChartData(history, forecast) {
  const monthlyHistory = history?.monthly ?? []
  const forecastMonthly = forecast?.monthly ?? []
  const byMonth = new Map()

  monthlyHistory.forEach((row) => {
    byMonth.set(row.month, {
      month: row.month,
      actual: row.total_sales,
      prediction: null,
    })
  })

  const lastHistory = monthlyHistory[monthlyHistory.length - 1]
  if (lastHistory) {
    const bridge = byMonth.get(lastHistory.month)
    byMonth.set(lastHistory.month, {
      ...bridge,
      prediction: lastHistory.total_sales,
    })
  }

  forecastMonthly
    .filter((row) => !lastHistory || row.month > lastHistory.month)
    .forEach((row) => {
      const existing = byMonth.get(row.month) ?? {
        month: row.month,
        actual: null,
        prediction: null,
      }
      byMonth.set(row.month, { ...existing, prediction: row.prediction })
    })

  return [...byMonth.values()].sort((left, right) => left.month.localeCompare(right.month))
}

function ForecastChart({ history, forecast, benchmark, benchmarkNote, isFiltering }) {
  const data = buildChartData(history, forecast)
  const methodLabel =
    forecast?.method === 'lightgbm_global_lag' ? 'LightGBM' : 'seasonal baseline'
  const accuracy = benchmark?.metrics?.mae
  const futureDays = forecast?.future_days ?? 0

  return (
    <div className="panel">
      <div className="panel-header-row">
        <div>
          <p className="panel-title">Sales Forecast</p>
          <p className="panel-sub">
            {futureDays}-day {methodLabel} forecast
            {forecast?.total ? ` · projected ${formatCurrency(forecast.total)}` : ''}
          </p>
        </div>
        {accuracy != null ? (
          <span className="model-chip" title="Mean absolute error on the full-dataset holdout">
            MAE {Number(accuracy).toFixed(1)}
          </span>
        ) : benchmarkNote ? (
          <span className="model-note">{benchmarkNote}</span>
        ) : null}
      </div>

      <div className="chart-legend">
        <span>
          <span className="chart-dot chart-dot-navy" />
          Historical
        </span>
        <span>
          <span className="chart-dot chart-dot-blue" />
          Forecast
        </span>
      </div>

      {data.length === 0 ? (
        <div className="chart-zone">No forecast data for this view.</div>
      ) : (
        <div
          className={`chart-wrap ${isFiltering ? 'updating' : ''}`}
          role="img"
          aria-label={`Monthly sales history and a ${futureDays}-day forecast.`}
        >
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f4f8" vertical={false} />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 10, fill: '#8aaac8' }}
                axisLine={false}
                tickLine={false}
                interval={Math.max(0, Math.floor(data.length / 8))}
                tickFormatter={formatMonth}
              />
              <YAxis
                tick={{ fontSize: 10, fill: '#8aaac8' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={formatCurrency}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  background: '#fff',
                  border: '1px solid #dce3ed',
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelFormatter={formatMonth}
                formatter={(value, name) => [
                  formatCurrency(value),
                  name === 'actual' ? 'Historical' : 'Forecast',
                ]}
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#1e3a5f"
                strokeWidth={2.5}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="prediction"
                stroke="#2196f3"
                strokeWidth={2.5}
                strokeDasharray="5 5"
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default ForecastChart
