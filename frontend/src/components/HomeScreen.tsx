/**
 * HomeScreen — The reasoning funnel.
 *
 * Ask anything. Nous routes it through an AI, intercepts the reasoning,
 * and monitors every logical step in real time.
 */
import { useEffect, useState, useCallback, useRef } from 'react'
import { api } from '../api'
import type { AnalysisResult, Example, InputProvider } from '../types'

interface Props {
  onResult: (r: AnalysisResult) => void
  onStream: (problem: string, provider: InputProvider) => void
  initialError?: string | null
}

type Mode = 'ask' | 'paste' | 'url'

const PROVIDERS: { value: InputProvider; label: string; model: string }[] = [
  { value: 'anthropic', label: 'Claude',  model: 'claude-sonnet-4-6' },
  { value: 'openai',    label: 'GPT-4o',  model: 'gpt-4o' },
  { value: 'gemini',    label: 'Gemini',  model: 'gemini-1.5-flash' },
]

const EXAMPLE_DOMAINS = [
  { id: 'catalyst', domain: 'Chemistry' },
  { id: 'math',     domain: 'Mathematics' },
  { id: 'drug',     domain: 'Drug Discovery' },
  { id: 'code',     domain: 'Code Agent' },
]

const PLACEHOLDERS = [
  'Is it safe to add the reagent at this stage?',
  'Does compound X enhance or impair pathway Z?',
  'Can we apply the intermediate value theorem here?',
  'Will this algorithm terminate on all inputs?',
  'Is this inference valid given the prior evidence?',
  'What follows if kinase Y is essential for pathway Z?',
]

export function HomeScreen({ onResult, onStream, initialError }: Props) {
  const [mode, setMode]       = useState<Mode>('ask')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(initialError ?? null)
  const [examples, setExamples] = useState<Example[]>([])

  const [problem,  setProblem]  = useState('')
  const [provider, setProvider] = useState<InputProvider>('anthropic')
  const [paste,    setPaste]    = useState('')
  const [url,      setUrl]      = useState('')

  const [placeholder, setPlaceholder] = useState(PLACEHOLDERS[0])
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (initialError) setError(initialError)
  }, [initialError])

  useEffect(() => {
    api.examples().then(setExamples).catch(() => {})
    // Rotate placeholder hint
    let i = 0
    const t = setInterval(() => {
      i = (i + 1) % PLACEHOLDERS.length
      setPlaceholder(PLACEHOLDERS[i])
    }, 4000)
    return () => clearInterval(t)
  }, [])

  const run = useCallback(async (fn: () => Promise<AnalysisResult>) => {
    setLoading(true)
    setError(null)
    try {
      onResult(await fn())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [onResult])

  const handleAsk = () => {
    if (!problem.trim()) { setError('Enter a problem.'); return }
    // Use streaming endpoint — transitions to StreamingView immediately
    onStream(problem.trim(), provider)
  }

  const handleExample = (id: string) => {
    const ex = examples.find(e => e.id === id)
    if (!ex) return
    run(() => api.analyze(ex.steps, true))
  }

  const handlePaste = () => {
    if (!paste.trim()) { setError('Paste some text.'); return }
    run(() => api.analyzeText(paste.trim()))
  }

  const handleUrl = () => {
    if (!url.trim()) { setError('Enter a URL.'); return }
    run(() => api.importUrl(url.trim()))
  }

  const selectedProvider = PROVIDERS.find(p => p.value === provider)!

  return (
    <div className="min-h-screen bg-canvas flex flex-col">

      {/* Nav */}
      <nav className="px-6 py-4 flex items-center gap-2.5">
        <div className="w-6 h-6 rounded bg-indigo/15 border border-indigo/25 flex items-center justify-center">
          <span className="text-indigo text-[11px] font-bold leading-none">◎</span>
        </div>
        <span className="text-[13px] font-semibold text-text-primary tracking-tight">NOUS</span>
        <span className="text-[10px] font-mono text-text-dim ml-0.5">v0.5</span>
      </nav>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pb-16">
        <div className="w-full max-w-[580px]">

          {/* Hero copy */}
          <div className="mb-8">
            <h1 className="text-[30px] font-bold text-text-primary tracking-[-0.025em] leading-tight mb-3">
              Think through anything.
            </h1>
            <p className="text-[15px] text-text-muted leading-relaxed">
              Nous intercepts the reasoning, builds the commitment graph, and flags
              exactly where the logic violates its own premises — across any domain.
            </p>
          </div>

          {/* Input card */}
          <div
            className="rounded-xl border border-raised overflow-hidden"
            style={{ background: '#111113' }}
          >
            {/* Mode tabs */}
            <div className="flex border-b border-raised">
              {([
                { id: 'ask',   label: 'Ask AI' },
                { id: 'paste', label: 'Paste trace' },
                { id: 'url',   label: 'Import URL' },
              ] as { id: Mode; label: string }[]).map(t => (
                <button
                  key={t.id}
                  onClick={() => { setMode(t.id); setError(null) }}
                  className={`px-4 py-2.5 text-[12px] font-medium transition-all border-b-2 ${
                    mode === t.id
                      ? 'text-text-primary border-indigo/70'
                      : 'text-text-dim border-transparent hover:text-text-muted'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Ask mode */}
            {mode === 'ask' && (
              <div>
                <textarea
                  ref={textareaRef}
                  value={problem}
                  onChange={e => setProblem(e.target.value)}
                  onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleAsk() }}
                  placeholder={placeholder}
                  rows={4}
                  className="w-full bg-transparent px-4 pt-4 pb-2 text-[14px] text-text-primary placeholder-text-dim outline-none resize-none leading-relaxed"
                />
                <div className="px-4 pb-3 flex items-center gap-2">
                  {/* Provider selector */}
                  <div className="relative">
                    <select
                      value={provider}
                      onChange={e => setProvider(e.target.value as InputProvider)}
                      style={{ colorScheme: 'dark' }}
                      className="appearance-none bg-raised border border-raised rounded-lg pl-2.5 pr-6 py-1.5 text-[12px] text-text-secondary outline-none cursor-pointer transition-colors hover:border-border"
                    >
                      {PROVIDERS.map(p => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                      ))}
                    </select>
                    <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-[9px] text-text-dim">▾</span>
                  </div>
                  <span className="text-[10px] font-mono text-[#3f3f46]">
                    {selectedProvider.model}
                  </span>
                  <div className="flex-1" />
                  <span className="text-[10px] text-text-dim hidden sm:block">
                    <kbd className="font-mono">⌘↵</kbd> to run
                  </span>
                  <button
                    onClick={handleAsk}
                    disabled={loading || !problem.trim()}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo text-white text-[12px] font-semibold transition-all hover:bg-indigo/85 disabled:opacity-40"
                  >
                    {loading ? <Spinner /> : (
                      <>Analyze <span className="text-indigo-200">→</span></>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Paste mode */}
            {mode === 'paste' && (
              <div>
                <textarea
                  value={paste}
                  onChange={e => setPaste(e.target.value)}
                  placeholder={"Paste any reasoning trace:\n\n1. The catalyst is air-sensitive and must stay under N₂.\n2. Transfer catalyst to Schlenk flask under nitrogen.\n3. Open flask to air to add reagent via syringe."}
                  rows={7}
                  className="w-full bg-transparent px-4 pt-4 pb-2 text-[13px] text-text-primary placeholder-text-dim outline-none resize-none font-mono leading-relaxed"
                />
                <div className="px-4 pb-3 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-[#3f3f46]">
                    Numbered steps, paragraphs, or Step N: patterns
                  </span>
                  <button
                    onClick={handlePaste}
                    disabled={loading || !paste.trim()}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo text-white text-[12px] font-semibold transition-all hover:bg-indigo/85 disabled:opacity-40"
                  >
                    {loading ? <Spinner /> : 'Analyze →'}
                  </button>
                </div>
              </div>
            )}

            {/* URL mode */}
            {mode === 'url' && (
              <div>
                <input
                  type="url"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleUrl() }}
                  placeholder="https://arxiv.org/abs/…"
                  className="w-full bg-transparent px-4 py-4 text-[14px] text-text-primary placeholder-text-dim outline-none"
                />
                <div className="px-4 pb-3 flex items-center justify-between border-t border-raised">
                  <span className="text-[10px] font-mono text-[#3f3f46]">
                    arxiv, blog posts, HTML articles — not JS-rendered pages
                  </span>
                  <button
                    onClick={handleUrl}
                    disabled={loading || !url.trim()}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo text-white text-[12px] font-semibold transition-all hover:bg-indigo/85 disabled:opacity-40"
                  >
                    {loading ? <Spinner /> : 'Import →'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="mt-3 px-4 py-2.5 rounded-lg bg-red-dim border border-red/25 text-red text-[12px] leading-relaxed">
              {error}
              {error.toLowerCase().includes('provider') || error.toLowerCase().includes('key') ? (
                <span className="text-red/60 block mt-0.5">
                  Make sure <code className="font-mono text-[11px]">ANTHROPIC_API_KEY</code> (or the relevant key) is set in your server environment.
                </span>
              ) : null}
            </div>
          )}

          {/* Examples */}
          {examples.length > 0 && (
            <div className="mt-7">
              <p className="text-[10px] font-mono text-text-dim uppercase tracking-[0.12em] mb-3">
                Examples — no API key required
              </p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_DOMAINS.map(meta => (
                  <button
                    key={meta.id}
                    onClick={() => !loading && handleExample(meta.id)}
                    disabled={loading}
                    className="px-3 py-1.5 rounded-full border border-raised text-[12px] text-text-dim hover:text-text-muted hover:border-border transition-all disabled:opacity-40"
                  >
                    {meta.domain}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Footer strip */}
          <div className="flex items-center gap-5 mt-8 text-[10px] font-mono text-[#3f3f46]">
            <span>Kripke semantics</span>
            <span>·</span>
            <span>5 violation types</span>
            <span>·</span>
            <span>Any AI, any domain</span>
          </div>
        </div>
      </main>
    </div>
  )
}

function Spinner() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" className="animate-spin" fill="none">
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="7 7" />
    </svg>
  )
}
