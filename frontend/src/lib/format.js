const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

export function formatCurrency(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'

  const sign = number < 0 ? '-' : ''
  const absolute = Math.abs(number)
  if (absolute >= 1_000_000_000) return `${sign}$${(absolute / 1_000_000_000).toFixed(1)}B`
  if (absolute >= 1_000_000) return `${sign}$${(absolute / 1_000_000).toFixed(1)}M`
  if (absolute >= 1_000) return `${sign}$${(absolute / 1_000).toFixed(0)}K`
  return `${sign}$${absolute.toFixed(0)}`
}

export function capitalize(value) {
  if (!value) return 'Unknown'
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function formatStore(value) {
  const text = String(value)
  return /^\d+$/.test(text) ? `Store ${text}` : text
}

export function formatMonth(value) {
  const [year, month] = String(value).split('-')
  const index = Number(month) - 1
  if (!year || Number.isNaN(index) || !MONTHS[index]) return String(value)
  return `${MONTHS[index]} ${year.slice(2)}`
}

export function monthName(value) {
  const index = Number(value) - 1
  return MONTHS[index] ?? String(value)
}
