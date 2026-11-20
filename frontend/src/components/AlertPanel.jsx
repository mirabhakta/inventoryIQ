import { useState } from 'react'
import { formatStore } from '../lib/format'

const LABELS = {
  'Low Margin': 'Low margin',
  'Demand Decline': 'Demand decline',
  'Sales Anomaly': 'Sales anomaly',
}

function toneFor(alert) {
  if (alert.alert_type === 'Low Margin') return 'margin'
  if (alert.direction === 'spike') return 'spike'
  if (alert.direction === 'drop') return 'drop'
  if (alert.direction === 'decline') return 'decline'
  return 'drop'
}

function labelFor(alert) {
  if (alert.alert_type === 'Sales Anomaly') {
    return alert.direction === 'spike' ? 'Demand spike' : 'Demand drop'
  }
  return LABELS[alert.alert_type] ?? alert.alert_type
}

function iconFor(tone) {
  if (tone === 'margin') return '⚠️'
  if (tone === 'spike') return '📈'
  return '📉'
}

function AlertPanel({ alerts = [], total = 0 }) {
  const [expanded, setExpanded] = useState(false)
  const hasAlerts = total > 0
  const visibleAlerts = expanded ? alerts : alerts.slice(0, 4)

  return (
    <div className="panel">
      <div className="panel-header-row">
        <div>
          <p className="panel-title">Alert Center</p>
          <p className="panel-sub">
            {total} active alert{total === 1 ? '' : 's'}
          </p>
        </div>
        <span className={hasAlerts ? 'badge-red' : 'badge-clear'}>
          {hasAlerts ? `${total} Active` : 'All clear'}
        </span>
      </div>

      <div className="alert-list" role="list" aria-label="Active alerts">
        {alerts.length === 0 ? (
          <p className="empty-copy">No alerts detected for this view.</p>
        ) : (
          visibleAlerts.map((alert, index) => {
            const tone = toneFor(alert)
            const storeLabel =
              alert.store_id !== 0 && alert.store_id !== '0'
                ? ` · ${formatStore(alert.store_id)}`
                : ''

            return (
              <div
                className={`alert-row alert-${tone}`}
                key={`${alert.store_id}-${alert.product_id}-${alert.alert_type}-${index}`}
                role="listitem"
              >
                <span className="alert-icon" aria-hidden="true">
                  {iconFor(tone)}
                </span>
                <div>
                  <p className="alert-name">
                    {alert.product_name}
                    {storeLabel}
                    <span className="alert-type">{labelFor(alert)}</span>
                  </p>
                  <p className="alert-metric">{alert.metric}</p>
                </div>
              </div>
            )
          })
        )}
      </div>

      {alerts.length > 4 && (
        <button
          type="button"
          className="alert-more"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
        >
          {expanded ? 'Show fewer alerts' : `Show all ${alerts.length} alerts`}
        </button>
      )}
    </div>
  )
}

export default AlertPanel
