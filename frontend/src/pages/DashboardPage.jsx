import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import AlertPanel from '../components/AlertPanel'
import ForecastChart from '../components/ForecastChart'
import KPICard from '../components/KPICard'
import Sidebar from '../components/Sidebar'
import { analyzeDataset, getSummary, isCancel, parseApiError } from '../api/client'
import { capitalize, formatCurrency, formatStore, monthName } from '../lib/format'
import './DashboardPage.css'

const HORIZONS = [
  { label: 'Next 30 days', days: 30 },
  { label: 'Next 90 days', days: 90 },
  { label: 'Next 6 months', days: 180 },
]

const HORIZON_DAYS = Object.fromEntries(HORIZONS.map((option) => [option.label, option.days]))

const TAB_COPY = {
  overview: { title: 'Dashboard Overview', subtitle: 'Your retail performance at a glance' },
  products: { title: 'Products', subtitle: 'Top and bottom performing products' },
  analysis: { title: 'Analysis', subtitle: 'Category trends and store performance' },
}

const BAR_COLORS = [
  '#1565c0', '#1976d2', '#1e88e5', '#2196f3',
  '#42a5f5', '#0288d1', '#0097a7', '#00838f',
  '#006064', '#0d47a1',
]

function DashboardPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const analysis = location.state?.analysis
  const file = location.state?.file

  useEffect(() => {
    if (!analysis || !file) {
      navigate('/upload', { replace: true })
    }
  }, [analysis, file, navigate])

  if (!analysis || !file) {
    return null
  }

  return (
    <DashboardView
      initialAnalysis={analysis}
      file={file}
      fileName={location.state.fileName ?? file.name}
    />
  )
}

function DashboardView({ initialAnalysis, file, fileName }) {
  const navigate = useNavigate()
  const [analysis, setAnalysis] = useState(initialAnalysis)
  const [activeTab, setActiveTab] = useState('overview')
  const [horizon, setHorizon] = useState('Next 90 days')
  const [selectedStores, setSelectedStores] = useState([])
  const [selectedCategories, setSelectedCategories] = useState([])
  const [selectedRegions, setSelectedRegions] = useState([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isFiltering, setIsFiltering] = useState(false)
  const [filterError, setFilterError] = useState(null)
  const [summary, setSummary] = useState('')
  const [summaryError, setSummaryError] = useState('')
  const [summaryState, setSummaryState] = useState('idle')
  const controllerRef = useRef(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const meta = analysis.meta
  const kpis = analysis.kpis
  const alerts = analysis.alerts
  const benchmark = analysis.benchmark ?? initialAnalysis.benchmark
  const benchmarkNote = analysis.benchmark_note ?? initialAnalysis.benchmark_note
  const hasActiveFilters =
    selectedStores.length > 0 ||
    selectedCategories.length > 0 ||
    selectedRegions.length > 0 ||
    horizon !== 'Next 90 days'

  function requestAnalysis({ stores, categories, regions, horizonLabel }) {
    const isDefault =
      stores.length === 0 &&
      categories.length === 0 &&
      regions.length === 0 &&
      horizonLabel === 'Next 90 days'

    controllerRef.current?.abort()
    setSummaryState('idle')
    setFilterError(null)

    if (isDefault) {
      setAnalysis(initialAnalysis)
      setIsFiltering(false)
      return
    }

    const controller = new AbortController()
    controllerRef.current = controller
    setIsFiltering(true)

    analyzeDataset(file, {
      futureDays: HORIZON_DAYS[horizonLabel],
      stores,
      categories,
      regions,
      includeBenchmark: false,
      signal: controller.signal,
    })
      .then((result) => {
        if (!controller.signal.aborted) setAnalysis(result)
      })
      .catch((error) => {
        if (!isCancel(error)) setFilterError(parseApiError(error))
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsFiltering(false)
      })
  }

  function toggleStore(store) {
    const next = selectedStores.includes(store)
      ? selectedStores.filter((value) => value !== store)
      : [...selectedStores, store]
    setSelectedStores(next)
    requestAnalysis({
      stores: next,
      categories: selectedCategories,
      regions: selectedRegions,
      horizonLabel: horizon,
    })
  }

  function toggleCategory(category) {
    const next = selectedCategories.includes(category)
      ? selectedCategories.filter((value) => value !== category)
      : [...selectedCategories, category]
    setSelectedCategories(next)
    requestAnalysis({
      stores: selectedStores,
      categories: next,
      regions: selectedRegions,
      horizonLabel: horizon,
    })
  }

  function toggleRegion(region) {
    const next = selectedRegions.includes(region)
      ? selectedRegions.filter((value) => value !== region)
      : [...selectedRegions, region]
    setSelectedRegions(next)
    requestAnalysis({
      stores: selectedStores,
      categories: selectedCategories,
      regions: next,
      horizonLabel: horizon,
    })
  }

  function changeHorizon(nextHorizon) {
    if (nextHorizon === horizon) return
    setHorizon(nextHorizon)
    requestAnalysis({
      stores: selectedStores,
      categories: selectedCategories,
      regions: selectedRegions,
      horizonLabel: nextHorizon,
    })
  }

  function resetFilters() {
    controllerRef.current?.abort()
    setSelectedStores([])
    setSelectedCategories([])
    setSelectedRegions([])
    setHorizon('Next 90 days')
    setAnalysis(initialAnalysis)
    setIsFiltering(false)
    setFilterError(null)
    setSummaryState('idle')
  }

  async function handleSummary() {
    setSummary('')
    setSummaryError('')
    setSummaryState('loading')

    try {
      const result = await getSummary({
        trend: kpis.forecast_direction,
        winner_model: kpis.winner_model ?? benchmark?.winner ?? null,
        mae: kpis.mae ?? benchmark?.metrics?.mae ?? null,
        total_sales: kpis.total_sales,
        alert_count: alerts.total,
        top_product: kpis.top_product,
        top_category: kpis.top_category,
      })
      setSummary(result.summary || 'No summary was returned.')
      setSummaryState('ready')
    } catch (error) {
      setSummaryError(parseApiError(error))
      setSummaryState('error')
    }
  }

  const summaryHint = summaryError.includes('GEMINI_API_KEY')
    ? 'Set GEMINI_API_KEY on the API server to enable live summaries.'
    : null

  const tabCopy = TAB_COPY[activeTab]

  return (
    <div className="db">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        meta={meta}
        fileName={fileName}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        horizons={HORIZONS}
        horizon={horizon}
        onHorizonChange={changeHorizon}
        selectedStores={selectedStores}
        selectedCategories={selectedCategories}
        selectedRegions={selectedRegions}
        onToggleStore={toggleStore}
        onToggleCategory={toggleCategory}
        onToggleRegion={toggleRegion}
        onReset={resetFilters}
        hasActiveFilters={hasActiveFilters}
        onGoHome={() => navigate('/')}
        onUploadNew={() => navigate('/upload')}
      />

      <div className="db-main">
        <header className="db-header">
          <div className="db-header-left-group">
            <button
              type="button"
              className="db-hamburger"
              onClick={() => setSidebarOpen((open) => !open)}
              aria-label="Toggle filters"
              aria-expanded={sidebarOpen}
              aria-controls="dashboard-filters"
            >
              ☰
            </button>
            <div className="db-header-left">
              <h1 className="db-header-title">{tabCopy.title}</h1>
              <p className="db-header-sub">{tabCopy.subtitle}</p>
            </div>
          </div>

          <div className="db-header-actions">
            {isFiltering && (
              <span className="db-filtering" role="status">⟳ Updating…</span>
            )}
            <button
              type="button"
              className="db-ai-btn"
              onClick={handleSummary}
              disabled={summaryState === 'loading'}
              aria-label="Generate AI summary"
              aria-expanded={summaryState !== 'idle'}
              aria-controls="ai-summary-panel"
            >
              <span aria-hidden="true">✦</span>
              <span className="db-ai-label">
                {summaryState === 'loading' ? 'Generating…' : 'AI Summary'}
              </span>
            </button>
          </div>
        </header>

        <div className="db-content">
          {summaryState !== 'idle' && (
            <section id="ai-summary-panel" className="ai-summary" aria-live="polite">
              <div className="ai-summary-header">
                <div>
                  <p className="ai-summary-label">AI summary</p>
                  <p className="ai-summary-sub">
                    {summaryState === 'ready' ? 'Generated by Gemini' : 'Gemini'}
                  </p>
                </div>
                <button
                  type="button"
                  className="ai-summary-close"
                  onClick={() => setSummaryState('idle')}
                  aria-label="Close AI summary"
                >
                  ×
                </button>
              </div>

              {summaryState === 'loading' && (
                <p className="ai-summary-body">Writing a summary from the current dashboard…</p>
              )}

              {summaryState === 'error' && (
                <div className="ai-summary-body">
                  <p role="alert">{summaryError}</p>
                  {summaryHint && <p className="ai-summary-hint">{summaryHint}</p>}
                  <button type="button" className="ai-insight-btn" onClick={handleSummary}>
                    Try again
                  </button>
                </div>
              )}

              {summaryState === 'ready' && (
                <>
                  <p className="ai-summary-body">{summary}</p>
                  <p className="ai-summary-hint">AI-generated — verify before making decisions.</p>
                </>
              )}
            </section>
          )}

          {filterError && (
            <div className="filter-error" role="alert">
              <span>{filterError}</span>
              <button
                type="button"
                className="filter-error-close"
                onClick={() => setFilterError(null)}
                aria-label="Dismiss filter error"
              >
                ×
              </button>
            </div>
          )}

          {activeTab === 'overview' && (
            <OverviewTab
              analysis={analysis}
              benchmark={benchmark}
              benchmarkNote={benchmarkNote}
              horizonLabel={horizon}
              isFiltering={isFiltering}
              onSummary={handleSummary}
              summaryState={summaryState}
            />
          )}
          {activeTab === 'products' && (
            <ProductsTab analysis={analysis} isFiltering={isFiltering} />
          )}
          {activeTab === 'analysis' && (
            <AnalysisTab analysis={analysis} isFiltering={isFiltering} />
          )}
        </div>
      </div>
    </div>
  )
}

function OverviewTab({ analysis, benchmark, benchmarkNote, horizonLabel, isFiltering, onSummary, summaryState }) {
  const { kpis, alerts } = analysis
  const alertTotal = alerts.total
  const insight = `Sales are ${kpis.forecast_direction}. ${alertTotal} alert${
    alertTotal === 1 ? '' : 's'
  } need attention. Top product: ${kpis.top_product ?? 'not available'}.`

  return (
    <div className="tab">
      <div className="ai-insight">
        <span className="ai-insight-icon" aria-hidden="true">✦</span>
        <span className="ai-insight-label">QUICK INSIGHT</span>
        <span className="ai-insight-text">{insight}</span>
        <button
          type="button"
          className="ai-insight-btn"
          onClick={onSummary}
          disabled={summaryState === 'loading'}
        >
          Full Summary
        </button>
      </div>

      <div className="kpi-grid">
        <KPICard
          tone="hero"
          label="Total Revenue"
          value={formatCurrency(kpis.total_sales)}
          delta={`${kpis.row_count.toLocaleString()} rows in view`}
        />
        <KPICard
          label="Sales Trend"
          value={capitalize(kpis.forecast_direction)}
          delta={`${kpis.forecast_method === 'lightgbm_global_lag' ? 'LightGBM' : 'Seasonal'} forecast`}
        />
        <KPICard
          label="Active Alerts"
          value={alertTotal}
          tone={alertTotal > 0 ? 'alert' : 'clear'}
          delta={alertTotal > 0 ? 'Needs attention' : 'All clear'}
        />
        <KPICard
          label="Projected Revenue"
          value={formatCurrency(kpis.projected_sales)}
          delta={`→ ${horizonLabel}`}
        />
      </div>

      <div className="bottom-row">
        <ForecastChart
          history={analysis.history}
          forecast={analysis.forecast}
          benchmark={benchmark}
          benchmarkNote={benchmarkNote}
          isFiltering={isFiltering}
        />
        <AlertPanel alerts={alerts.items} total={alertTotal} />
      </div>
    </div>
  )
}

function ProductsTab({ analysis, isFiltering }) {
  const top = analysis.products.top
  const bottom = analysis.products.bottom
  const hasBottom = bottom.length > 0
  const chartData = top
    .slice(0, 10)
    .slice()
    .reverse()
    .map((product) => ({ name: product.product, revenue: product.total_sales }))

  return (
    <div className="tab">
      <div className={hasBottom ? 'two-col' : ''}>
        <div className="panel">
          <p className="panel-title">Top Performers</p>
          <p className="panel-sub">Products driving the most revenue</p>
          <div className="product-list">
            {top.length === 0 ? (
              <p className="empty-copy">No product data in this dataset.</p>
            ) : (
              top.slice(0, 5).map((row, index) => (
                <div key={row.product_id ?? row.product} className="product-row">
                  <div className="product-left">
                    <span className="rank rank-blue">{index + 1}</span>
                    <span className="product-name">{row.product}</span>
                  </div>
                  <span className="product-val val-blue">{formatCurrency(row.total_sales)}</span>
                </div>
              ))
            )}
          </div>
          {!hasBottom && top.length > 0 && (
            <p className="empty-copy">
              Add more than ten products to unlock the underperformer ranking.
            </p>
          )}
        </div>

        {hasBottom && (
          <div className="panel">
            <p className="panel-title">Underperformers</p>
            <p className="panel-sub">Products generating the least revenue</p>
            <div className="product-list">
              {bottom.slice(0, 5).map((row, index) => (
                <div key={row.product_id ?? row.product} className="product-row">
                  <div className="product-left">
                    <span className="rank rank-red">{index + 1}</span>
                    <span className="product-name">{row.product}</span>
                  </div>
                  <span className="product-val val-red">{formatCurrency(row.total_sales)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <p className="panel-title">Top 10 Products by Revenue</p>
        <p className="panel-sub">Highest earning products in the current view</p>
        {chartData.length === 0 ? (
          <div className="chart-zone">No product data in this dataset.</div>
        ) : (
          <div
            className={`chart-wrap ${isFiltering ? 'updating' : ''}`}
            role="img"
            aria-label="Bar chart of the top ten products by revenue."
          >
            <ResponsiveContainer width="100%" height={400}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 10, right: 80, left: 20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f4f8" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 10, fill: '#8aaac8' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={formatCurrency}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 11, fill: '#1e3a5f', fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  width={160}
                  interval={0}
                />
                <Tooltip
                  contentStyle={{
                    background: '#fff',
                    border: '1px solid #dce3ed',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(value, name, props) => [formatCurrency(value), props.payload.name]}
                  labelFormatter={() => ''}
                />
                <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                  {chartData.map((row, index) => (
                    <Cell key={`${row.name}-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}

function AnalysisTab({ analysis, isFiltering }) {
  const { history, categories, stores } = analysis

  const byMonth = {}
  history.monthly.forEach((row) => {
    const [year, month] = row.month.split('-')
    if (!byMonth[month]) byMonth[month] = { month }
    byMonth[month][year] = row.total_sales
  })
  const yoyData = Object.values(byMonth).sort((left, right) =>
    left.month.localeCompare(right.month),
  )
  const years = [...new Set(history.monthly.map((row) => row.month.slice(0, 4)))].sort()
  const hasMultipleYears = years.length > 1

  const categoryData = categories.map((row) => ({
    name: row.category,
    revenue: row.total_sales,
  }))

  const storeData = [...stores]
    .sort((left, right) =>
      String(left.store_id).localeCompare(String(right.store_id), undefined, { numeric: true }),
    )
    .map((row) => ({
      name: formatStore(row.store_id),
      revenue: row.total_sales,
    }))

  return (
    <div className="tab">
      <div className="panel">
        <p className="panel-title">
          {hasMultipleYears ? 'Year-over-Year Revenue Comparison' : 'Monthly Revenue'}
        </p>
        <p className="panel-sub">
          {hasMultipleYears
            ? 'Monthly revenue compared across each year in your dataset'
            : 'Revenue by month for the current view'}
        </p>
        {yoyData.length === 0 ? (
          <div className="chart-zone">No monthly data in this dataset.</div>
        ) : (
          <div
            className={`chart-wrap ${isFiltering ? 'updating' : ''}`}
            role="img"
            aria-label="Monthly revenue line chart."
          >
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={yoyData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f4f8" vertical={false} />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 10, fill: '#8aaac8' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={monthName}
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
                  labelFormatter={monthName}
                  formatter={(value, name) => [formatCurrency(value), name]}
                />
                {years.map((year, index) => (
                  <Line
                    key={year}
                    type="monotone"
                    dataKey={year}
                    stroke={BAR_COLORS[index % BAR_COLORS.length]}
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 5 }}
                    name={year}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="two-col">
        <div className="panel">
          <p className="panel-title">Revenue by Category</p>
          <p className="panel-sub">Total sales per category</p>
          {categoryData.length === 0 ? (
            <div className="chart-zone">No category data in this dataset.</div>
          ) : (
            <div
              className={`chart-wrap ${isFiltering ? 'updating' : ''}`}
              role="img"
              aria-label="Bar chart of revenue by category."
            >
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={categoryData}
                  margin={{ top: 10, right: 20, left: 10, bottom: 50 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f4f8" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: '#8aaac8' }}
                    axisLine={false}
                    tickLine={false}
                    angle={-30}
                    textAnchor="end"
                    interval={0}
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
                    formatter={(value) => [formatCurrency(value), 'Revenue']}
                  />
                  <Bar dataKey="revenue" radius={[4, 4, 0, 0]}>
                    {categoryData.map((row, index) => (
                      <Cell key={`${row.name}-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="panel">
          <p className="panel-title">Store Comparison</p>
          <p className="panel-sub">Total revenue by store</p>
          {storeData.length === 0 ? (
            <div className="chart-zone">No store data in this dataset.</div>
          ) : (
            <div
              className={`chart-wrap ${isFiltering ? 'updating' : ''}`}
              role="img"
              aria-label="Bar chart of revenue by store."
            >
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={storeData}
                  margin={{ top: 10, right: 20, left: 10, bottom: 50 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f4f8" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: '#8aaac8' }}
                    axisLine={false}
                    tickLine={false}
                    angle={-30}
                    textAnchor="end"
                    interval={0}
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
                    formatter={(value) => [formatCurrency(value), 'Revenue']}
                  />
                  <Bar dataKey="revenue" radius={[4, 4, 0, 0]}>
                    {storeData.map((row, index) => (
                      <Cell key={`${row.name}-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
