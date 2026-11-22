import React, { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useSearchParams } from 'react-router-dom'
import { EmberShell } from './components/layout/EmberShell'
import { ToastViewport } from './components/ui/ToastViewport'
import { WebsitePage } from './features/website/WebsitePage'
import { OverviewPage } from './features/portal/OverviewPage'
import { CompSetPage } from './features/portal/CompSetPage'
import { RoomMatchPage } from './features/portal/RoomMatchPage'
import { RoomOpsPage } from './features/portal/RoomOpsPage'
import { AutoPricingPage } from './features/portal/AutoPricingPage'
import { AnalyticsPage } from './features/portal/AnalyticsPage'
import { MemoryTagsPage } from './features/portal/MemoryTagsPage'
import { CallDeskPage } from './features/portal/CallDeskPage'
import { PlansPage } from './features/portal/PlansPage'
import { SettingsPage } from './features/portal/SettingsPage'
import { usePortalStore } from './store/usePortalStore'
import type { TierId } from './types/hospitality'

const PortalRoutes: React.FC = () => {
  const [searchParams] = useSearchParams()
  const { setAuthParams, hydratePortal, clientToken } = usePortalStore()

  useEffect(() => {
    const dh = searchParams.get('demo_hotel')
    const tok = searchParams.get('token')
    const pt = searchParams.get('preview_tier') as TierId | null
    if (tok) {
      setAuthParams(tok, null)
      hydratePortal(null, pt)
    } else if (dh) {
      setAuthParams('', dh)
      hydratePortal(dh, pt)
    } else {
      hydratePortal(undefined, pt)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.get('demo_hotel'), searchParams.get('token'), clientToken])

  return (
    <EmberShell>
      <Routes>
        <Route index element={<OverviewPage />} />
        <Route path="comp-set" element={<CompSetPage />} />
        <Route path="room-match" element={<RoomMatchPage />} />
        <Route path="room-ops" element={<RoomOpsPage />} />
        <Route path="auto-pricing" element={<AutoPricingPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="memory" element={<MemoryTagsPage />} />
        <Route path="call-desk" element={<CallDeskPage />} />
        <Route path="plans" element={<PlansPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/portal" replace />} />
      </Routes>
    </EmberShell>
  )
}

export const AppRoutes: React.FC = () => {
  const location = useLocation()
  useEffect(() => {
    if (!location.hash) {
      window.scrollTo(0, 0)
    }
  }, [location.pathname, location.hash])

  return (
    <>
      <Routes>
        <Route path="/" element={<WebsitePage />} />
        <Route path="/website" element={<WebsitePage />} />
        <Route path="/website.html" element={<WebsitePage />} />
        <Route path="/landing" element={<WebsitePage />} />
        <Route path="/portal/*" element={<PortalRoutes />} />
        <Route path="/client" element={<Navigate to="/portal" replace />} />
        <Route path="/client_portal.html" element={<Navigate to="/portal" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <ToastViewport />
    </>
  )
}

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App
