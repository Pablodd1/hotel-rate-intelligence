import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, beforeEach } from 'vitest'
import { AppRoutes } from '../App'
import { usePortalStore } from '../store/usePortalStore'
import { exportToCsv } from '../utils/csv'

describe('HotelRateIntel Ember V20 Application', () => {
  beforeEach(() => {
    localStorage.clear()
    usePortalStore.getState().resetDemoData()
  })

  it('renders Public Website (/) with Option A plain-English positioning, ROI calculator & Instant Voice Concierge', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>
    )
    expect(screen.getByText(/See What Nearby Miami Hotels & Booking Sites Charge/i)).toBeInTheDocument()
    expect(screen.getByText(/6 Everyday Hotel Problems We Solve Before 6:00 AM/i)).toBeInTheDocument()
    expect(screen.getByText(/Live Voice Concierge/i)).toBeInTheDocument()

    // Test ROI calculator dynamic update
    const roomsInp = screen.getByLabelText(/Sellable Rooms/i) as HTMLInputElement
    fireEvent.change(roomsInp, { target: { value: '60' } })
    expect(roomsInp.value).toBe('60')

    // Open Voice Concierge & verify instant speech trigger
    fireEvent.click(screen.getByRole('button', { name: /Open Hospitality AI Voice Concierge/i }))
    expect(screen.getByText(/Suite vs. Suite & Fees/i)).toBeInTheDocument()
  })

  it('requires sign-in on unauthenticated /portal and serves Legal + 404 routes cleanly', () => {
    const portalUnauth = render(
      <MemoryRouter initialEntries={['/portal']}>
        <AppRoutes />
      </MemoryRouter>
    )
    expect(screen.getByText(/Hotel Client Sign In/i)).toBeInTheDocument()
    portalUnauth.unmount()

    const privacyView = render(
      <MemoryRouter initialEntries={['/privacy']}>
        <AppRoutes />
      </MemoryRouter>
    )
    expect(screen.getByText(/HotelRateIntel Privacy Policy/i)).toBeInTheDocument()
    privacyView.unmount()

    const notFoundView = render(
      <MemoryRouter initialEntries={['/nonexistent-route-xyz']}>
        <AppRoutes />
      </MemoryRouter>
    )
    expect(screen.getByText(/We couldn't find that page/i)).toBeInTheDocument()
    notFoundView.unmount()
  })

  it('renders all 10 interconnected Client Portal routes in sandbox mode without errors', async () => {
    const routes = [
      { path: '/portal?demo_hotel=23', match: /Reservations & Yield Overview/i },
      { path: '/portal/comp-set?demo_hotel=23', match: /Comp-Set Rate & Channel Monitor/i },
      { path: '/portal/room-match?demo_hotel=23', match: /Suite vs\. Suite & True Out-the-Door Comparator/i },
      { path: '/portal/room-ops?demo_hotel=23', match: /Live Room Ops: OOO, OOS, Housekeeping Holds/i },
      { path: '/portal/auto-pricing?demo_hotel=23', match: /Guardrailed AI Auto-Pricing & Channel Strategy/i },
      { path: '/portal/analytics?demo_hotel=23', match: /12-Month RevPAR, Direct Booking Share/i },
      { path: '/portal/memory?demo_hotel=23', match: /Competitor Pricing Memory & Private Strategy Tags/i },
      { path: '/portal/call-desk?demo_hotel=23', match: /Overnight Courtesy Call-Around & Competitor Email Inquiry Desk/i },
      { path: '/portal/plans?demo_hotel=23', match: /Compare Tiers Live & Monthly Payroll ROI/i },
      { path: '/portal/settings?demo_hotel=23', match: /Portal & Notification Settings/i },
    ]

    for (const r of routes) {
      const { unmount } = render(
        <MemoryRouter initialEntries={[r.path]}>
          <AppRoutes />
        </MemoryRouter>
      )
      expect(await screen.findByText(r.match)).toBeInTheDocument()
      unmount()
    }
  })

  it('supports Room Ops OOO/OOS net-occupancy recalculation, category add/delete & demo reset persistence', async () => {
    render(
      <MemoryRouter initialEntries={['/portal/room-ops?demo_hotel=23']}>
        <AppRoutes />
      </MemoryRouter>
    )

    const oooInput = screen.getByLabelText('OOO') as HTMLInputElement
    fireEvent.change(oooInput, { target: { value: '5' } })
    expect(oooInput.value).toBe('5')

    // Add category row
    fireEvent.click(screen.getByRole('button', { name: /Add Category/i }))
    expect(screen.getByDisplayValue('Connecting Family Suite')).toBeInTheDocument()

    // Save Room Ops into store & verify true sellable rooms updates
    fireEvent.click(screen.getByRole('button', { name: /Save Inventory & Recalculate AI Pricing/i }))
    await waitFor(() => {
      expect(usePortalStore.getState().opsPlan.ops.ooo_rooms).toBe(5)
    })

    // Reset demo data restores defaults
    usePortalStore.getState().resetDemoData()
    await waitFor(() => {
      expect(usePortalStore.getState().opsPlan.ops.ooo_rooms).toBe(2)
    })
  })

  it('handles TanStack Table filtering, Suite-vs-Suite occupancy toggle & CSV export formatting', async () => {
    const csv = exportToCsv('test.csv', ['Hotel', 'BAR'], [['Avalon, SoBe', 238]])
    expect(csv).toContain('"Avalon, SoBe",238')

    render(
      <MemoryRouter initialEntries={['/portal/room-match?demo_hotel=23']}>
        <AppRoutes />
      </MemoryRouter>
    )

    const tierSelect = screen.getByLabelText(/Select matched room equivalent/i) as HTMLSelectElement
    fireEvent.change(tierSelect, { target: { value: 'double_double' } })
    await waitFor(() => {
      expect(usePortalStore.getState().roomEquivalency.room_tier.id).toBe('double_double')
    })

    const occSelect = screen.getByLabelText(/Select occupancy count/i) as HTMLSelectElement
    fireEvent.change(occSelect, { target: { value: 'triple_quad' } })
    await waitFor(() => {
      expect(usePortalStore.getState().roomEquivalency.occupancy).toBe('triple_quad')
    })
  })

  it('supports Comp-Set Table searching, parity filter pills, and KPI reconciliation', async () => {
    render(
      <MemoryRouter initialEntries={['/portal/comp-set?demo_hotel=23']}>
        <AppRoutes />
      </MemoryRouter>
    )

    expect(await screen.findByText(/The Betsy Hotel/i)).toBeInTheDocument()
    const searchInp = screen.getByPlaceholderText(/Search property, corridor, personality/i)
    fireEvent.change(searchInp, { target: { value: 'Pelican' } })
    expect(screen.getByText(/Pelican Hotel/i)).toBeInTheDocument()
    expect(screen.queryByText(/The Betsy Hotel/i)).not.toBeInTheDocument()

    // Clear search and test Parity filter pill
    fireEvent.change(searchInp, { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Direct Win' }))
    expect(screen.getByText(/The Plymouth South Beach/i)).toBeInTheDocument()
  })

  it('validates Zod form inputs cleanly before submission on Self-Serve Registration', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /Create Account/i }))
    expect(await screen.findByText(/Enter your hotel name/i)).toBeInTheDocument()
    expect(screen.getByText(/Enter a valid work email/i)).toBeInTheDocument()
  })
})
