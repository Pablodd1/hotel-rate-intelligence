import React, { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useSearchParams } from 'react-router-dom'
import { EmberShell } from './components/layout/EmberShell'
import { ToastViewport } from './components/ui/ToastViewport'
import { WebsitePage } from './features/website/WebsitePage'
import { OverviewPage } from './features/portal/OverviewPage'
import { PortalLoginGate } from './features/portal/PortalLoginGate'
import { CompSetPage } from './features/portal/CompSetPage'
import { RoomMatchPage } from './features/portal/RoomMatchPage'
import { RoomOpsPage } from './features/portal/RoomOpsPage'
import { AutoPricingPage } from './features/portal/AutoPricingPage'
import { AnalyticsPage } from './features/portal/AnalyticsPage'
import { MemoryTagsPage } from './features/portal/MemoryTagsPage'
import { CallDeskPage } from './features/portal/CallDeskPage'
import { PlansPage } from './features/portal/PlansPage'
import { SettingsPage } from './features/portal/SettingsPage'
import { NotFoundPage, PrivacyPolicyPage, TermsPage } from './features/website/LegalPages'
import { usePortalStore } from './store/usePortalStore'
import type { TierId } from './types/hospitality'

const PortalRoutes: React.FC = () => {
  const [searchParams] = useSearchParams()
  const { setAuthParams, hydratePortal, clientToken, demoHotelId } = usePortalStore()
  const dhParam = searchParams.get('demo_hotel')
  const tokParam = searchParams.get('token')
  const demoParam = searchParams.get('demo')
  const isAuthenticatedOrDemo = Boolean(
    tokParam || dhParam || (demoParam && ['1', 'true', 'yes'].includes(demoParam)) || clientToken || demoHotelId
  )

  useEffect(() => {
    const pt = searchParams.get('preview_tier') as TierId | null
    if (tokParam) {
      setAuthParams(tokParam, null)
      hydratePortal(null, pt)
    } else if (dhParam) {
      setAuthParams('', dhParam)
      hydratePortal(dhParam, pt)
    } else if (demoParam && ['1', 'true', 'yes'].includes(demoParam)) {
      setAuthParams('', '23')
      hydratePortal('23', pt)
    } else if (clientToken) {
      hydratePortal(null, pt)
    } else if (demoHotelId) {
      hydratePortal(demoHotelId, pt)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dhParam, tokParam, demoParam, clientToken, demoHotelId])

  if (!isAuthenticatedOrDemo) {
    return <PortalLoginGate />
  }

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
        <Route path="/pricing" element={<WebsitePage initialSection="pricing" />} />
        <Route path="/blog" element={<WebsitePage initialSection="blogs" />} />
        <Route path="/blogs" element={<WebsitePage initialSection="blogs" />} />
        <Route path="/contact" element={<WebsitePage initialSection="contact-desk" />} />
        <Route path="/demo" element={<Navigate to="/portal?demo_hotel=23" replace />} />
        <Route path="/privacy" element={<PrivacyPolicyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/portal/*" element={<PortalRoutes />} />
        <Route path="/client" element={<Navigate to="/portal" replace />} />
        <Route path="/client_portal.html" element={<Navigate to="/portal" replace />} />
        <Route path="*" element={<NotFoundPage />} />
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
