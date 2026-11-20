import { formatStore } from '../lib/format'

const NAV_ITEMS = [
  { id: 'overview', icon: '📊', label: 'Overview' },
  { id: 'products', icon: '🏆', label: 'Products' },
  { id: 'analysis', icon: '📈', label: 'Analysis' },
]

function Sidebar({
  open,
  onClose,
  meta,
  fileName,
  activeTab,
  onTabChange,
  horizons,
  horizon,
  onHorizonChange,
  selectedStores,
  selectedCategories,
  selectedRegions,
  onToggleStore,
  onToggleCategory,
  onToggleRegion,
  onReset,
  hasActiveFilters,
  onGoHome,
  onUploadNew,
}) {
  return (
    <>
      <div
        className={`db-sidebar-overlay ${open ? 'open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        id="dashboard-filters"
        className={`db-sidebar ${open ? 'open' : ''}`}
        aria-label="Dashboard filters"
      >
        <button
          type="button"
          className="db-sidebar-logo"
          onClick={onGoHome}
          aria-label="InventoryIQ home"
        >
          <img src="/logo.webp" alt="InventoryIQ" className="db-sidebar-logo-img" />
        </button>

        <button
          type="button"
          className="db-sidebar-close"
          onClick={onClose}
          aria-label="Close filters"
        >
          ×
        </button>

        <div className="db-sidebar-section">
          <p className="db-sidebar-label">Menu</p>
          <nav className="db-nav">
            {NAV_ITEMS.map((item) => {
              const active = activeTab === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`db-nav-btn ${active ? 'active' : ''}`}
                  onClick={() => {
                    onTabChange(item.id)
                    onClose()
                  }}
                  aria-current={active ? 'page' : undefined}
                >
                  <span className="db-nav-icon" aria-hidden="true">{item.icon}</span>
                  <span>{item.label}</span>
                  {active && <span className="db-nav-pip" />}
                </button>
              )
            })}
          </nav>
        </div>

        <div className="db-sidebar-section">
          <p className="db-sidebar-label">Forecast Horizon</p>
          <div className="db-radio-group">
            {horizons.map((option) => (
              <label key={option.label} className="db-radio-item">
                <input
                  type="radio"
                  name="horizon"
                  value={option.label}
                  checked={horizon === option.label}
                  onChange={() => onHorizonChange(option.label)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="db-sidebar-section">
          <p className="db-sidebar-label">
            Stores
            {selectedStores.length > 0 && (
              <span className="db-filter-count">{selectedStores.length}</span>
            )}
          </p>
          <div className="db-checkbox-group">
            {meta.stores.map((store) => (
              <label key={store} className="db-checkbox-item">
                <input
                  type="checkbox"
                  checked={selectedStores.includes(String(store))}
                  onChange={() => onToggleStore(String(store))}
                />
                <span>{formatStore(store)}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="db-sidebar-section">
          <p className="db-sidebar-label">
            Categories
            {selectedCategories.length > 0 && (
              <span className="db-filter-count">{selectedCategories.length}</span>
            )}
          </p>
          <div className="db-checkbox-group">
            {meta.categories.map((category) => (
              <label key={category} className="db-checkbox-item">
                <input
                  type="checkbox"
                  checked={selectedCategories.includes(category)}
                  onChange={() => onToggleCategory(category)}
                />
                <span>{category}</span>
              </label>
            ))}
          </div>
        </div>

        {meta.regions.length > 0 && (
          <div className="db-sidebar-section">
            <p className="db-sidebar-label">
              Regions
              {selectedRegions.length > 0 && (
                <span className="db-filter-count">{selectedRegions.length}</span>
              )}
            </p>
            <div className="db-checkbox-group">
              {meta.regions.map((region) => (
                <label key={region} className="db-checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedRegions.includes(region)}
                    onChange={() => onToggleRegion(region)}
                  />
                  <span>{region}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="db-sidebar-bottom">
          {hasActiveFilters && (
            <button type="button" className="db-reset-btn" onClick={onReset}>
              ↺ Reset Filters
            </button>
          )}
          <div className="db-file-chip">
            <span aria-hidden="true">📄</span>
            <span className="db-file-name">{fileName}</span>
          </div>
          <button type="button" className="db-new-file" onClick={onUploadNew}>
            + Upload New File
          </button>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
