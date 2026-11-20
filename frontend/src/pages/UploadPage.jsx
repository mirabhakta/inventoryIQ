import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { analyzeDataset, parseApiError } from '../api/client'
import './UploadPage.css'

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
const MAX_UPLOAD_ROWS = 200_000

function UploadPage() {
  const navigate = useNavigate()
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState('')

  function handleFile(file) {
    if (!file) return

    const extension = file.name.split('.').pop()?.toLowerCase()
    if (extension === 'xls') {
      setError('Legacy .xls files are not supported. Save the file as .xlsx or .csv and try again.')
      setUploadedFile(null)
      return
    }
    if (extension !== 'csv' && extension !== 'xlsx') {
      setError('Please upload a CSV or Excel (.xlsx) file.')
      setUploadedFile(null)
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError('That file is larger than the 10 MB limit. Filter to a recent date range or a subset of stores/products and try again.')
      setUploadedFile(null)
      return
    }

    setError(null)
    setUploadedFile(file)
  }

  function handleDragOver(event) {
    event.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave() {
    setIsDragging(false)
  }

  function handleDrop(event) {
    event.preventDefault()
    setIsDragging(false)
    handleFile(event.dataTransfer.files[0])
  }

  function handleInputChange(event) {
    handleFile(event.target.files[0])
    event.target.value = ''
  }

  async function handleContinue() {
    if (!uploadedFile || loading) return

    setLoading(true)
    setError(null)
    setLoadingStep('Uploading and analyzing your data…')

    try {
      const analysis = await analyzeDataset(uploadedFile, {
        futureDays: 90,
        includeBenchmark: true,
      })

      setLoadingStep('Preparing your dashboard…')
      navigate('/dashboard', {
        state: {
          analysis,
          fileName: uploadedFile.name,
          file: uploadedFile,
        },
      })
    } catch (err) {
      setError(parseApiError(err))
      setLoading(false)
      setLoadingStep('')
    }
  }

  const showBackendHint =
    error &&
    (error.includes('backend') ||
      error.includes('API') ||
      error.includes('Network') ||
      error.includes('reach'))

  const showSizeHint =
    error &&
    (error.includes('rows') ||
      error.includes('MB') ||
      error.toLowerCase().includes('larger'))

  return (
    <div className="upload-page">

      <nav className="upload-nav">
        <button
          type="button"
          className="upload-nav-logo-button"
          onClick={() => !loading && navigate('/')}
          disabled={loading}
          aria-label="InventoryIQ home"
        >
          <img src="/logo.webp" alt="InventoryIQ" className="upload-nav-logo" />
        </button>
      </nav>

      <div className="upload-center">
        <div className="upload-card">

          {loading ? (
            <div className="upload-loading" role="status" aria-live="polite">
              <div className="upload-spinner" />
              <p className="upload-loading-title">Analyzing your data</p>
              <p className="upload-loading-step">{loadingStep}</p>
              <p className="upload-loading-note">
                Cleaning rows, running the forecast, and checking for risks. This can take a few seconds.
              </p>
            </div>
          ) : (
            <>
              <div className="upload-header">
                <h1>Upload Your Data</h1>
                <p>Drop your retail CSV or Excel file. We handle the rest.</p>
              </div>

              <div className="upload-req-grid">

                <div className="upload-req-card upload-req-card--required">
                  <div className="upload-req-card-label">
                    <span className="upload-req-dot upload-req-dot--required" />
                    Required Columns
                  </div>
                  <div className="upload-req-field">
                    <div className="upload-req-icon upload-req-icon--required">📅</div>
                    <div>
                      <strong>Date</strong>
                      <span>date, order_date, transaction_date…</span>
                    </div>
                  </div>
                  <div className="upload-req-field">
                    <div className="upload-req-icon upload-req-icon--required">💰</div>
                    <div>
                      <strong>Sales / Revenue</strong>
                      <span>sales, revenue, amount, total…</span>
                    </div>
                  </div>
                </div>

                <div className="upload-req-card upload-req-card--optional">
                  <div className="upload-req-card-label">
                    <span className="upload-req-dot upload-req-dot--optional" />
                    Optional — Highly Recommended
                  </div>
                  <div className="upload-req-field">
                    <div className="upload-req-icon upload-req-icon--optional">🏪</div>
                    <div>
                      <strong>Store / Branch</strong>
                      <span>Unlocks store filters &amp; comparison</span>
                    </div>
                  </div>
                  <div className="upload-req-field">
                    <div className="upload-req-icon upload-req-icon--optional">📦</div>
                    <div>
                      <strong>Product Name / SKU</strong>
                      <span>Unlocks top &amp; bottom performers</span>
                    </div>
                  </div>
                  <div className="upload-req-field">
                    <div className="upload-req-icon upload-req-icon--optional">🏷️</div>
                    <div>
                      <strong>Category / Department</strong>
                      <span>Unlocks category breakdown</span>
                    </div>
                  </div>
                  <div className="upload-req-field">
                    <div className="upload-req-icon upload-req-icon--optional">🗺️</div>
                    <div>
                      <strong>Region / Market</strong>
                      <span>Unlocks regional filters &amp; insights</span>
                    </div>
                  </div>
                </div>

              </div>

              <div className="upload-disclaimer">
                <span className="upload-disclaimer-icon">⚠️</span>
                <p>
                  <strong>Optional columns are highly recommended.</strong> Without them, several dashboard sections will be limited or empty — including Top &amp; Bottom Performers, Category Breakdown, Store Comparison, and regional filters. You'll still get forecasts and trend data, but the full power of InventoryIQ comes from richer data.
                </p>
              </div>

              <p className="upload-limit-note">
                Up to 10 MB and {MAX_UPLOAD_ROWS.toLocaleString()} rows per file. For larger
                exports, filter to a recent date range or a subset of stores/products.
              </p>

              <label
                htmlFor="upload-input"
                className={`upload-dropzone ${isDragging ? 'dragging' : ''} ${uploadedFile ? 'success' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input
                  id="upload-input"
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={handleInputChange}
                  className="upload-input"
                />

                {uploadedFile ? (
                  <div className="upload-success-state">
                    <div className="upload-success-icon">✓</div>
                    <p className="upload-success-name">{uploadedFile.name}</p>
                    <p className="upload-success-size">
                      {(uploadedFile.size / 1024).toFixed(1)} KB · Click to change
                    </p>
                  </div>
                ) : (
                  <div className="upload-idle-state">
                    <div className="upload-folder-icon">📂</div>
                    <p className="upload-main-text">
                      {isDragging ? 'Drop it here!' : 'Drag & drop your file here'}
                    </p>
                    <p className="upload-sub-text">or click to browse</p>
                    <span className="upload-formats">CSV · XLSX · up to 10 MB</span>
                  </div>
                )}
              </label>

              {error && (
                <div className="upload-error" role="alert">
                  <p className="upload-error-title">⚠️ Unable to process your file</p>
                  <p className="upload-error-body">{error}</p>
                  {showBackendHint && (
                    <p className="upload-error-hint">Make sure the backend server is running.</p>
                  )}
                  {showSizeHint && (
                    <p className="upload-error-hint">
                      Tip: filter your export to the last 12 months, or select a subset of
                      stores and products, then try again.
                    </p>
                  )}
                </div>
              )}

              <button
                type="button"
                className={`upload-btn ${uploadedFile ? 'active' : 'disabled'}`}
                onClick={handleContinue}
                disabled={!uploadedFile}
              >
                {uploadedFile ? 'Continue to Dashboard →' : 'Select a file to continue'}
              </button>

              <div className="upload-reassurance">
                <span>✓ Auto column detection</span>
                <span>✓ No formatting needed</span>
                <span>✓ Up to 200k rows</span>
              </div>
            </>
          )}

        </div>
      </div>

    </div>
  )
}

export default UploadPage
