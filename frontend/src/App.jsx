import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import UploadPage from './pages/UploadPage'
import './App.css'

// The dashboard pulls in Recharts, so keep it out of the landing/upload bundle.
const DashboardPage = lazy(() => import('./pages/DashboardPage'))

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route
          path="/dashboard"
          element={
            <Suspense fallback={<div className="route-loading">Loading dashboard…</div>}>
              <DashboardPage />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
