function KPICard({ label, value, delta, tone = 'default' }) {
  if (tone === 'hero') {
    return (
      <div className="kpi-hero">
        <div className="kpi-hero-bg" />
        <p className="kpi-hero-label">{label}</p>
        <p className="kpi-hero-value">{value}</p>
        {delta && <span className="kpi-hero-badge">{delta}</span>}
      </div>
    )
  }

  const toneClass = tone === 'alert' ? ' kpi-alert' : tone === 'clear' ? ' kpi-clear' : ''

  return (
    <div className={`kpi-card${toneClass}`}>
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">{value}</p>
      {delta && <p className="kpi-delta kpi-neutral">{delta}</p>}
    </div>
  )
}

export default KPICard
