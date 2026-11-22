import React, { useRef, useState } from 'react'
import { Mic, Phone, Send, Volume2, VolumeX, X, Globe, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface ChatItem {
  role: 'bot' | 'user'
  text: string
}

interface QuickAction {
  label: string
  type: string
  url?: string
}

interface VoiceConciergeProps {
  selectedHotelId?: number
  onAuditReceived?: (audit: unknown) => void
  initialOpen?: boolean
}

export const VoiceConcierge: React.FC<VoiceConciergeProps> = ({ selectedHotelId = 23, onAuditReceived }) => {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [voiceOn, setVoiceOn] = useState(true)
  const [speaking, setSpeaking] = useState(false)
  const [listening, setListening] = useState(false)
  const [lang, setLang] = useState<'en' | 'es'>('en')
  const [spokeWelcome, setSpokeWelcome] = useState(false)
  const [input, setInput] = useState('')
  const [showCallback, setShowCallback] = useState(false)
  const [cbPhone, setCbPhone] = useState('')
  const [cbName, setCbName] = useState('')
  const [cbStatus, setCbStatus] = useState('')
  const [actions, setActions] = useState<QuickAction[]>([
    { label: 'Suite vs. Suite & Fees', type: 'ask_suite' },
    { label: 'Pre vs. Post Night Audit', type: 'ask_audit' },
    { label: 'OOO / OOS Auto-Price', type: 'ask_ooo' },
    { label: 'Book $99 AI Audit', type: 'link', url: 'https://www.aidynamic.pro/booking' },
  ])
  const [messages, setMessages] = useState<ChatItem[]>([
    {
      role: 'bot',
      text: 'Welcome to HotelRateIntel — Made by Hoteliers with 20 years in luxury hotels & residential concierge service, powered by AI. Tap the mic to speak live or click any topic below.',
    },
  ])
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const speakText = (rawText: string, targetLang: 'en' | 'es' = lang) => {
    if (!voiceOn || typeof window === 'undefined' || !('speechSynthesis' in window) || !rawText) return
    try {
      window.speechSynthesis.cancel()
      const clean = rawText.replace(/[*_`#→⚡📞🛏️🌙🔧🎙️]/g, '').replace(/\s+/g, ' ').trim()
      const u = new SpeechSynthesisUtterance(clean)
      u.lang = targetLang === 'es' ? 'es-US' : 'en-US'
      u.rate = 1.02
      const voices = window.speechSynthesis.getVoices() || []
      const prefix = targetLang === 'es' ? 'es' : 'en'
      const match =
        voices.find((v) => v.lang.toLowerCase().startsWith(prefix) && /natural|neural|google|samantha|daniel|monica/i.test(v.name)) ||
        voices.find((v) => v.lang.toLowerCase().startsWith(prefix))
      if (match) u.voice = match
      u.onstart = () => setSpeaking(true)
      u.onend = () => setSpeaking(false)
      u.onerror = () => setSpeaking(false)
      window.speechSynthesis.speak(u)
    } catch {
      setSpeaking(false)
    }
  }

  const handleToggleOpen = (forceOpen?: boolean, withCallback?: boolean) => {
    const next = forceOpen !== undefined ? forceOpen : !open
    setOpen(next)
    if (withCallback) setShowCallback(true)
    if (next && voiceOn && !spokeWelcome) {
      setSpokeWelcome(true)
      const welcome =
        lang === 'es'
          ? 'Bienvenido a HotelRateIntel, hecho por hoteleros con veinte años en hospitalidad de lujo y potenciado con inteligencia artificial. ¿Qué propiedad manejas hoy?'
          : 'Welcome to HotelRateIntel, made by hoteliers with twenty years in luxury hospitality and powered by AI. I can audit your live OTA parity, compare Suite to Suite rates with rollaways and resort fees, or walk you through our ninety nine dollar hospitality AI audit. Which hotel are you managing?'
      speakText(welcome, lang)
    } else if (!next && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
    }
  }

  const handleSend = async (overrideMsg?: string) => {
    const text = (overrideMsg ?? input).trim()
    if (!text) return
    if (!overrideMsg) setInput('')
    setMessages((prev) => [...prev, { role: 'user', text }])

    let reply =
      'HotelRateIntel matches exact Suite-vs-Suite and Double-vs-Double rooms (including rollaway beds, resort fees, and housekeeping cadence), connects OOO/OOS holds to AI auto-pricing, and supports Pre-Audit (11:30 PM) courtesy calls.'
    let nextActions: QuickAction[] = [
      { label: 'Open Live Portal Demo →', type: 'link', url: '/portal?demo_hotel=23' },
      { label: 'Book $99 Hospitality AI Audit', type: 'link', url: 'https://www.aidynamic.pro/booking' },
    ]
    let replyLang: 'en' | 'es' = lang

    try {
      const res = await fetch('/api/public/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, hotel_id: selectedHotelId, lang }),
      })
      if (res.ok) {
        const d = await res.json()
        if (d.audit && onAuditReceived) onAuditReceived(d.audit)
        if (d.reply) reply = d.reply
        if (Array.isArray(d.actions) && d.actions.length) nextActions = d.actions
        if (d.lang === 'es' || d.lang === 'en') replyLang = d.lang
      }
    } catch {
      if (/audit|overnight|night|call/i.test(text)) {
        reply =
          'Window #1 Before Night Audit (11:30 PM–1:15 AM) captures live tonight walk-in BAR and rooms left before PMS date roll. Window #2 After Night Audit (3:30 AM–4:45 AM) collects clean final occupancy for your 6 AM brief. Avoid calling during active audit roll (1:45–3:15 AM).'
      } else if (/suite|double|rollaway|resort|hk|housekeeping/i.test(text)) {
        reply =
          'We match exact equivalents only — Suite vs. Suite and Double-Double vs. Double-Double — normalizing Single/Double occupancy, rollaway fees, Miami resort fees, 14% tax, and housekeeping cadence into True Out-the-Door rates.'
      }
    }

    setMessages((prev) => [...prev, { role: 'bot', text: reply }])
    setActions(nextActions)
    speakText(reply, replyLang)
    setTimeout(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }, 40)
  }

  const handleStartMic = () => {
    const w = window as unknown as Record<string, unknown>
    const SR = (w.SpeechRecognition || w.webkitSpeechRecognition) as (new () => {
      lang: string
      interimResults: boolean
      maxAlternatives: number
      onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void
      onerror: () => void
      onend: () => void
      start: () => void
    }) | undefined
    if (!SR) {
      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: 'Voice microphone requires Chrome, Edge, or Safari — feel free to type your question below.' },
      ])
      return
    }
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    const rec = new SR()
    rec.lang = lang === 'es' ? 'es-US' : 'en-US'
    rec.interimResults = false
    rec.maxAlternatives = 1
    setListening(true)
    rec.onresult = (ev) => {
      const tr = ev.results[0][0].transcript
      setListening(false)
      handleSend(tr)
    }
    rec.onerror = rec.onend = () => setListening(false)
    rec.start()
  }

  const handleCallbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!cbPhone.trim()) {
      setCbStatus('Please enter a valid US/Miami phone number.')
      return
    }
    try {
      const res = await fetch('/api/public/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: cbPhone, name: cbName || 'Hotel Leader', hotel_id: selectedHotelId }),
      })
      const d = await res.json()
      setCbStatus(d.ok ? d.message : d.error || 'Unable to submit callback.')
      if (d.ok) speakText('Your callback request is locked in with our Miami hospitality desk.', lang)
    } catch {
      setCbStatus('Callback request queued locally. Direct line: +1 (786) 970-8366.')
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => handleToggleOpen()}
        aria-label="Open Hospitality AI Voice Concierge"
        className="fixed bottom-4 left-4 sm:left-auto sm:right-5 z-[70] inline-flex items-center gap-2.5 px-4 py-2.5 rounded-full text-xs font-extrabold text-white shadow-xl border border-blue-300/40 bg-gradient-to-r from-[#0D255B] via-[#1744A6] to-[#2563EB] hover:brightness-110 transition"
      >
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
        <Sparkles className="w-3.5 h-3.5 text-blue-200" />
        <span>Live Voice Concierge · Tap to Hear AI Demo</span>
      </button>

      {open && (
        <div className="fixed bottom-16 right-4 z-[75] w-[min(395px,calc(100vw-24px))] rounded-3xl bg-white border border-[#DCE7F8] shadow-emberShell overflow-hidden flex flex-col max-h-[78vh]">
          <div className="px-4 py-3 text-white flex items-center justify-between gap-2 bg-gradient-to-r from-[#06122E] via-[#0D255B] to-[#1744A6]">
            <div>
              <div className="text-xs font-extrabold flex items-center gap-2">
                <span>Hospitality AI Concierge</span>
                <span className={`inline-flex items-center gap-0.5 h-3.5 ${speaking ? 'voice-eq-active text-emerald-300' : 'text-blue-200/70'}`}>
                  <span className="voice-eq-bar" />
                  <span className="voice-eq-bar" />
                  <span className="voice-eq-bar" />
                  <span className="voice-eq-bar" />
                </span>
              </div>
              <div className="text-[10px] text-blue-200 font-medium">Made by Hoteliers (20 Yrs Luxury Service)</div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => {
                  const next = lang === 'en' ? 'es' : 'en'
                  setLang(next)
                  speakText(
                    next === 'es'
                      ? 'Modo español activado. Bienvenido a HotelRateIntel, creado por hoteleros.'
                      : 'English mode active. How can I assist your Reservations team?',
                    next
                  )
                }}
                className="px-2 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-[10px] font-bold inline-flex items-center gap-1"
              >
                <Globe className="w-3 h-3" />
                {lang.toUpperCase()}
              </button>
              <button
                type="button"
                onClick={() => {
                  const n = !voiceOn
                  setVoiceOn(n)
                  if (!n && 'speechSynthesis' in window) window.speechSynthesis.cancel()
                }}
                aria-label="Toggle speech output"
                className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20"
              >
                {voiceOn ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
              </button>
              <button
                type="button"
                onClick={() => handleToggleOpen(false)}
                aria-label="Close concierge"
                className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div ref={scrollRef} className="p-3 overflow-y-auto space-y-2.5 bg-[#F2F6FD] flex-1 max-h-[270px]">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`text-xs leading-relaxed px-3 py-2.5 rounded-2xl max-w-[92%] ${
                  m.role === 'user'
                    ? 'ml-auto bg-blue-600 text-white font-semibold rounded-br-sm'
                    : 'bg-white text-[#0B1B3B] border border-[#DCE7F8] rounded-bl-sm shadow-sm'
                }`}
              >
                {m.text}
              </div>
            ))}
          </div>

          <div className="px-3 py-2 bg-white border-t border-[#EAF1FC] flex flex-wrap gap-1.5">
            {actions.map((a, idx) =>
              a.type === 'link' && a.url ? (
                a.url.startsWith('/') ? (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setOpen(false)
                      navigate(a.url || '/portal')
                    }}
                    className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[10.5px] font-bold hover:bg-blue-700"
                  >
                    {a.label}
                  </button>
                ) : (
                  <a
                    key={idx}
                    href={a.url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[10.5px] font-bold hover:bg-blue-700"
                  >
                    {a.label}
                  </a>
                )
              ) : (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSend(a.label)}
                  className="px-2.5 py-1 rounded-lg bg-[#F2F6FD] border border-[#DCE7F8] text-[#0B1B3B] text-[10.5px] font-bold hover:bg-blue-50"
                >
                  {a.label}
                </button>
              )
            )}
            <button
              type="button"
              onClick={() => setShowCallback((v) => !v)}
              className="px-2.5 py-1 rounded-lg bg-emerald-600 text-white text-[10.5px] font-bold inline-flex items-center gap-1 hover:bg-emerald-700"
            >
              <Phone className="w-3 h-3" />
              Request Call
            </button>
          </div>

          {showCallback && (
            <form onSubmit={handleCallbackSubmit} className="px-3 py-2.5 bg-blue-50/80 border-t border-blue-200 space-y-2">
              <div className="text-[10.5px] font-extrabold text-blue-900">DIRECT MIAMI HOSPITALITY CALLBACK</div>
              <div className="grid grid-cols-2 gap-1.5">
                <input
                  value={cbPhone}
                  onChange={(e) => setCbPhone(e.target.value)}
                  placeholder="+1 (305) 555-0199"
                  className="px-2.5 py-1.5 text-xs rounded-lg border border-blue-200 bg-white"
                />
                <input
                  value={cbName}
                  onChange={(e) => setCbName(e.target.value)}
                  placeholder="Name / Hotel"
                  className="px-2.5 py-1.5 text-xs rounded-lg border border-blue-200 bg-white"
                />
              </div>
              <div className="flex items-center gap-2">
                <button type="submit" className="flex-1 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-bold">
                  Request Instant Call →
                </button>
                <button type="button" onClick={() => setShowCallback(false)} className="px-2.5 py-1.5 rounded-lg bg-white border border-blue-200 text-xs font-semibold">
                  Cancel
                </button>
              </div>
              {cbStatus && <div className="text-[11px] font-bold text-emerald-700">{cbStatus}</div>}
            </form>
          )}

          <div className="p-2.5 bg-white border-t border-[#DCE7F8] flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleStartMic}
              aria-label="Speak to Concierge"
              className={`p-2 rounded-xl border text-xs font-bold ${
                listening ? 'bg-rose-600 text-white border-rose-600' : 'bg-[#F2F6FD] text-blue-700 border-[#DCE7F8] hover:bg-blue-50'
              }`}
            >
              <Mic className="w-4 h-4" />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSend()
              }}
              placeholder="Ask Suite-vs-Suite, Night Audit, OOO, or paste URL..."
              className="flex-1 px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] text-[#0B1B3B] focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            />
            <button
              type="button"
              onClick={() => handleSend()}
              aria-label="Send message"
              className="p-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
