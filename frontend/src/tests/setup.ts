import '@testing-library/jest-dom'
import { vi } from 'vitest'

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserverMock
window.scrollTo = vi.fn()

// Provide deterministic speechSynthesis mock for Concierge voice testing
Object.defineProperty(window, 'speechSynthesis', {
  writable: true,
  value: {
    speak: vi.fn(),
    cancel: vi.fn(),
    getVoices: () => [{ lang: 'en-US', name: 'Google US English' }],
  },
})

if (typeof URL.createObjectURL !== 'function') {
  URL.createObjectURL = vi.fn(() => 'blob:mock-csv')
}
if (typeof URL.revokeObjectURL !== 'function') {
  URL.revokeObjectURL = vi.fn()
}

// Keep Vitest deterministic & fast offline
globalThis.fetch = vi.fn(() =>
  Promise.resolve({
    ok: false,
    json: () => Promise.resolve({}),
  } as Response)
)

window.SpeechSynthesisUtterance = function (this: { text: string; lang: string }, text: string) {
  this.text = text
  this.lang = 'en-US'
} as unknown as typeof SpeechSynthesisUtterance
