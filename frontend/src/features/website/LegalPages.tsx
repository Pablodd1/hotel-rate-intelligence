import React from 'react'
import { ArrowLeft, FileText, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export const PrivacyPolicyPage: React.FC = () => {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen ember-gradient-bg py-8 px-4">
      <div className="max-w-3xl mx-auto ember-card p-6 sm:p-10 space-y-5">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="text-xs font-bold text-blue-700 hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to HotelRateIntel
        </button>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-800 text-[11px] font-extrabold uppercase">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-600" /> Privacy Policy
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#0B1B3B]">HotelRateIntel Privacy Policy</h1>
        <p className="text-xs text-[#6D81A8]">Effective Date: November 27, 2026 · North Miami, FL 33161</p>

        <div className="space-y-4 text-sm text-[#334155] leading-relaxed">
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">1. Data Isolation Between Hotels</h2>
            <p>
              Each hotel client workspace in HotelRateIntel is strictly isolated by property account. Out-of-Order (OOO), Out-of-Service (OOS), Housekeeping holds, private competitor strategy tags, and Night Audit shift logs belong exclusively to your property and are never visible to competing hotels.
            </p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">2. Information We Collect</h2>
            <p>
              When you request a rate parity check, schedule a demo, or register a hotel portal account, we collect your hotel name, market corridor, work email address, and phone number strictly to deliver your requested audit, daily 6:00 AM rate briefs, or account access.
            </p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">3. Public Rate &amp; PMS Credentials</h2>
            <p>
              Our daily rate monitoring reads publicly available OTA and direct website pricing without requiring guest folio data or PMS credentials on Day 1. Optional 2-way PMS/Channel Manager integrations store property-scoped API tokens encrypted server-side and never share guest PII.
            </p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">4. Email Opt-Out &amp; Contact</h2>
            <p>
              Every outreach brief includes RFC-8058 1-click unsubscribe. To update or delete your property contact details, email{' '}
              <a href="mailto:jasmel@hotelrateintel.com" className="text-blue-700 font-bold underline">jasmel@hotelrateintel.com</a> or call +1 (786) 970-8366.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}

export const TermsPage: React.FC = () => {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen ember-gradient-bg py-8 px-4">
      <div className="max-w-3xl mx-auto ember-card p-6 sm:p-10 space-y-5">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="text-xs font-bold text-blue-700 hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to HotelRateIntel
        </button>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-800 text-[11px] font-extrabold uppercase">
          <FileText className="w-3.5 h-3.5 text-blue-600" /> Terms of Service
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#0B1B3B]">HotelRateIntel Terms of Service</h1>
        <p className="text-xs text-[#6D81A8]">Effective Date: November 27, 2026 · HotelRateIntel · North Miami, FL 33161</p>

        <div className="space-y-4 text-sm text-[#334155] leading-relaxed">
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">1. Month-to-Month Subscription &amp; Cancellation</h2>
            <p>
              Free Starter ($0/mo) requires no credit card. Paid plans — Boutique Core ($99/mo), Pro Revenue &amp; Call Desk ($199/mo), and Multi-Property Group ($399/mo) — operate month-to-month with no annual contract lock-in and may be canceled anytime before your next billing cycle.
            </p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">2. $99 48-Hour Custom Hospitality Setup &amp; AI Audit Guarantee</h2>
            <p>
              For properties ordering the optional $99 one-time 48-hour setup and AI audit, if our custom parity and operations audit does not uncover at least $2,500/month in combined RevPAR and payroll opportunities within 48 hours, we refund 100% of the $99 fee.
            </p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">3. Pricing Decision Responsibility &amp; Guardrails</h2>
            <p>
              HotelRateIntel provides live competitor parity observations, Suite-vs-Suite checkout normalization, and AI-assisted rate recommendations within Floor/Ceiling guardrails configured by your hotel. Final pricing and PMS/channel push approvals remain under your property&apos;s control.
            </p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-extrabold text-[#0B1B3B]">4. Governing Contact</h2>
            <p>
              Operated locally in Miami-Dade County, Florida. Questions:{' '}
              <a href="mailto:jasmel@hotelrateintel.com" className="text-blue-700 font-bold underline">jasmel@hotelrateintel.com</a> · +1 (786) 970-8366.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen ember-gradient-bg flex items-center justify-center p-4">
      <div className="max-w-md w-full ember-card p-8 text-center space-y-4">
        <div className="text-xs font-extrabold uppercase tracking-wider text-blue-700">404 · Page Not Found</div>
        <h1 className="text-2xl font-black text-[#0B1B3B]">We couldn&apos;t find that page.</h1>
        <p className="text-xs text-[#475B80] leading-relaxed">
          The page you requested does not exist on HotelRateIntel. Return to our homepage or open the interactive Miami boutique hotel demo.
        </p>
        <div className="flex flex-wrap justify-center gap-2.5 pt-2">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-extrabold hover:bg-blue-700"
          >
            Go to Homepage →
          </button>
          <button
            type="button"
            onClick={() => navigate('/portal?demo_hotel=23')}
            className="px-4 py-2 rounded-xl bg-[#F2F6FD] border border-[#DCE7F8] text-[#0B1B3B] text-xs font-bold hover:bg-blue-50"
          >
            View Live Demo
          </button>
        </div>
      </div>
    </div>
  )
}
