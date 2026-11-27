import React, { useEffect, useRef, useState } from 'react'
import { Mic, MicOff, Phone, Send, Volume2, VolumeX, X, Globe, Sparkles } from 'lucide-react'
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

type BrowserSpeechRecognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onstart: (() => void) | null
  onresult: ((e: {
    resultIndex: number
    results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>
  }) => void) | null
  onerror: ((e: { error?: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

function pickWarmHospitalityVoice(voices: SpeechSynthesisVoice[], targetLang: 'en' | 'es'): SpeechSynthesisVoice | undefined {
  const prefix = targetLang === 'es' ? 'es' : 'en'
  const langVoices = voices.filter((v) => v.lang.toLowerCase().startsWith(prefix))
  if (!langVoices.length) return undefined

  const preferredPatterns =
    targetLang === 'es'
      ? [
          /dalia.*online|paloma.*online|elena.*online/i,
          /natural|neural/i,
          /google español/i,
          /paulina|monica|sabina|sofia/i,
        ]
      : [
          /aria.*online|jenny.*online|ava.*online|emma.*online|sonia.*online/i,
          /natural|neural/i,
          /google us english/i,
          /samantha|allison|karen|zira|victoria/i,
        ]

  for (const pat of preferredPatterns) {
    const found = langVoices.find((v) => pat.test(v.name))
    if (found) return found
  }
  return langVoices[0]
}

export const VoiceConcierge: React.FC<VoiceConciergeProps> = ({ selectedHotelId = 23, onAuditReceived }) => {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [voiceOn, setVoiceOn] = useState(true)
  const [handsFree, setHandsFree] = useState(true)
  const [speaking, setSpeaking] = useState(false)
  const [listening, setListening] = useState(false)
  const [liveTranscript, setLiveTranscript] = useState('')
  const [micHint, setMicHint] = useState('')
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
      text: 'Welcome to HotelRateIntel Miami! Built by local hoteliers with 20 years in luxury hospitality — tap the microphone and talk to me live, or choose any topic below!',
    },
  ])

  const scrollRef = useRef<HTMLDivElement | null>(null)
  const voicesRef = useRef<SpeechSynthesisVoice[]>([])
  const recRef = useRef<BrowserSpeechRecognition | null>(null)
  const finalHeardRef = useRef('')

  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
    const loadVoices = () => {
      const list = window.speechSynthesis.getVoices() || []
      if (list.length) voicesRef.current = list
    }
    loadVoices()
    window.speechSynthesis.onvoiceschanged = loadVoices
    return () => {
      window.speechSynthesis.onvoiceschanged = null
      try {
        recRef.current?.abort()
      } catch {
        // ignore
      }
    }
  }, [])

  const stopMic = () => {
    try {
      recRef.current?.stop()
    } catch {
      // ignore
    }
    setListening(false)
    setLiveTranscript('')
  }

  const speakText = (rawText: string, targetLang: 'en' | 'es' = lang, autoResumeMic = false) => {
    if (!voiceOn || typeof window === 'undefined' || !('speechSynthesis' in window) || !rawText) return
    try {
      stopMic()
      window.speechSynthesis.cancel()
      const clean = rawText
        .replace(/[*_`#→]/g, '')
        .replace(/\$(\d+)/g, '$1 dollars')
        .replace(/\s+/g, ' ')
        .trim()
      const u = new SpeechSynthesisUtterance(clean)
      u.lang = targetLang === 'es' ? 'es-US' : 'en-US'
      // Warm, energetic, human boutique-hotel front-desk cadence
      u.rate = targetLang === 'es' ? 1.04 : 1.05
      u.pitch = 1.08
      u.volume = 1.0
      const voices = voicesRef.current.length ? voicesRef.current : window.speechSynthesis.getVoices() || []
      const match = pickWarmHospitalityVoice(voices, targetLang)
      if (match) u.voice = match
      u.onstart = () => setSpeaking(true)
      u.onend = () => {
        setSpeaking(false)
        if (autoResumeMic && handsFree) {
          setTimeout(() => {
            startMicInternal(targetLang)
          }, 280)
        }
      }
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
          ? '¡Hola y bienvenido a HotelRateIntel Miami! Qué gusto saludarte. Fuimos creados por hoteleros locales con veinte años en hospitalidad de lujo. Presiona el micrófono y dime el nombre de tu hotel para revisar tus tarifas hoy mismo.'
          : 'Hello and welcome to HotelRateIntel Miami! So glad you stopped by. We were built right here by hoteliers with twenty years in luxury hospitality. Tap the microphone and tell me your Miami hotel name, or ask about Suite to Suite matching and overnight audit tools!'
      speakText(welcome, lang, false)
    } else if (!next) {
      stopMic()
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel()
        setSpeaking(false)
      }
    }
  }

  const handleSend = async (overrideMsg?: string, fromVoice = false) => {
    const text = (overrideMsg ?? input).trim()
    if (!text) return
    if (!overrideMsg) setInput('')
    setMicHint('')
    setMessages((prev) => [...prev, { role: 'user', text }])

    let reply =
      'Wonderful question! HotelRateIntel matches exact Suite-vs-Suite and Double-vs-Double rooms with rollaways, resort fees, and housekeeping cadence, connects live OOO/OOS holds to AI auto-pricing, and supports Pre-Audit 11:30 PM courtesy calls for Miami hotels!'
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
          'Great question! Window one before Night Audit, from 11:30 PM to 1:15 AM, captures tonight walk-in BAR and rooms left before date roll. Window two after Night Audit, from 3:30 AM to 4:45 AM, gives you clean final occupancy for your 6 AM brief!'
      } else if (/suite|double|rollaway|resort|hk|housekeeping/i.test(text)) {
        reply =
          'We compare true apples to apples — Suite vs Suite and Double-Double vs Double-Double — normalizing occupancy, rollaway beds, Miami resort fees, 14% tax, and housekeeping cadence into True Out-the-Door rates!'
      }
    }

    setMessages((prev) => [...prev, { role: 'bot', text: reply }])
    setActions(nextActions)
    speakText(reply, replyLang, fromVoice)
    setTimeout(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }, 40)
  }

  const startMicInternal = async (activeLang: 'en' | 'es' = lang) => {
    if (typeof window === 'undefined') return
    const w = window as unknown as Record<string, unknown>
    const SR = (w.SpeechRecognition || w.webkitSpeechRecognition) as (new () => BrowserSpeechRecognition) | undefined
    if (!SR) {
      setMicHint('Live voice input requires Chrome, Edge, or Safari — you can also type below.')
      return
    }

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
    }

    // Explicitly check/request microphone permission so browser prompts cleanly
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((t) => t.stop())
      } catch {
        setListening(false)
        setMicHint('Microphone access was blocked. Click the lock/mic icon in your browser address bar, allow Microphone, then tap the mic again.')
        return
      }
    }

    try {
      recRef.current?.abort()
    } catch {
      // ignore
    }

    const rec = new SR()
    recRef.current = rec
    finalHeardRef.current = ''
    rec.lang = activeLang === 'es' ? 'es-US' : 'en-US'
    rec.continuous = false
    rec.interimResults = true
    rec.maxAlternatives = 1

    rec.onstart = () => {
      setListening(true)
      setLiveTranscript('')
      setMicHint(activeLang === 'es' ? 'Escuchando… habla ahora con claridad.' : 'Listening… speak clearly now!')
    }

    rec.onresult = (ev) => {
      let interim = ''
      let finalText = ''
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const resItem = ev.results[i]
        const piece = resItem[0]?.transcript || ''
        if (resItem.isFinal) finalText += piece
        else interim += piece
      }
      if (interim) setLiveTranscript(interim)
      if (finalText.trim()) {
        finalHeardRef.current = finalText.trim()
        setLiveTranscript(finalText.trim())
        setListening(false)
        try {
          rec.stop()
        } catch {
          // ignore
        }
        handleSend(finalText.trim(), true)
      }
    }

    rec.onerror = (ev) => {
      setListening(false)
      const err = ev?.error || ''
      if (err === 'not-allowed' || err === 'service-not-allowed') {
        setMicHint('Microphone permission denied — allow microphone access in your browser bar and tap the mic again.')
      } else if (err === 'no-speech') {
        setMicHint('I did not catch that — tap the mic and speak closer to your microphone.')
      } else if (err === 'audio-capture') {
        setMicHint('No microphone detected on this device. Check your audio input or type your question below.')
      } else if (err && err !== 'aborted') {
        setMicHint(`Voice input paused (${err}). Tap the mic to try again or type below.`)
      }
    }

    rec.onend = () => {
      setListening(false)
      if (!finalHeardRef.current && liveTranscript.trim()) {
        const fallback = liveTranscript.trim()
        setLiveTranscript('')
        handleSend(fallback, true)
      } else {
        setLiveTranscript('')
      }
    }

    try {
      rec.start()
    } catch {
      setListening(false)
      setMicHint('Could not start microphone right now — tap the mic again or type your question below.')
    }
  }

  const handleMicToggle = () => {
    if (listening) {
      stopMic()
      setMicHint('')
    } else {
      startMicInternal(lang)
    }
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
      if (d.ok) speakText('Fantastic! Your callback request is locked in with our Miami hospitality desk.', lang, false)
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
        <span>Live Voice Concierge · Tap to Talk Live</span>
      </button>

      {open && (
        <div className="fixed bottom-16 right-4 z-[75] w-[min(400px,calc(100vw-24px))] rounded-3xl bg-white border border-[#DCE7F8] shadow-emberShell overflow-hidden flex flex-col max-h-[80vh]">
          <div className="px-4 py-3 text-white flex items-center justify-between gap-2 bg-gradient-to-r from-[#06122E] via-[#0D255B] to-[#1744A6]">
            <div>
              <div className="text-xs font-extrabold flex items-center gap-2">
                <span>Miami Hotel AI Concierge</span>
                <span className={`inline-flex items-center gap-0.5 h-3.5 ${speaking ? 'voice-eq-active text-emerald-300' : 'text-blue-200/70'}`}>
                  <span className="voice-eq-bar" />
                  <span className="voice-eq-bar" />
                  <span className="voice-eq-bar" />
                  <span className="voice-eq-bar" />
                </span>
              </div>
              <div className="text-[10px] text-blue-200 font-medium">Warm Boutique Front Desk Voice · EN / ES</div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setHandsFree((v) => !v)}
                title="Auto-listen after concierge finishes speaking"
                className={`px-2 py-1 rounded-lg text-[10px] font-bold ${
                  handsFree ? 'bg-emerald-500/30 text-emerald-100 border border-emerald-300/40' : 'bg-white/10 text-blue-100'
                }`}
              >
                {handsFree ? 'Auto-Mic' : 'Manual'}
              </button>
              <button
                type="button"
                onClick={() => {
                  const next = lang === 'en' ? 'es' : 'en'
                  setLang(next)
                  speakText(
                    next === 'es'
                      ? '¡Perfecto! Modo español activado. ¿En qué puedo ayudar a tu hotel en Miami hoy?'
                      : 'Awesome! English mode is active. How can I help your Miami hotel team today?',
                    next,
                    false
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

          <div ref={scrollRef} className="p-3 overflow-y-auto space-y-2.5 bg-[#F2F6FD] flex-1 max-h-[260px]">
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
            {listening && (
              <div className="ml-auto max-w-[92%] px-3 py-2 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-600 animate-ping shrink-0" />
                <span>{liveTranscript || (lang === 'es' ? 'Te escucho… habla ahora' : 'Listening to you… speak now')}</span>
              </div>
            )}
          </div>

          {micHint && (
            <div className="px-3 py-1.5 bg-amber-50 border-t border-amber-200 text-[11px] font-semibold text-amber-900">
              {micHint}
            </div>
          )}

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
                  onClick={() => handleSend(a.label, false)}
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
              onClick={handleMicToggle}
              aria-label={listening ? 'Stop listening' : 'Speak to Concierge'}
              className={`px-2.5 py-2 rounded-xl border text-xs font-bold inline-flex items-center gap-1 transition ${
                listening
                  ? 'bg-rose-600 text-white border-rose-600 animate-pulse'
                  : 'bg-[#F2F6FD] text-blue-700 border-[#DCE7F8] hover:bg-blue-50'
              }`}
            >
              {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              <span className="text-[11px]">{listening ? 'Stop' : 'Talk'}</span>
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSend()
              }}
              placeholder="Speak or type about your Miami hotel..."
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
