import { useState, useCallback, useRef } from 'react'
import { HomeScreen } from './components/HomeScreen'
import { StreamingView } from './components/StreamingView'
import { AnalysisView } from './components/AnalysisView'
import { streamReason } from './api'
import type { AnalysisResult, InputProvider, Step, StepResult } from './types'

type Screen = 'home' | 'streaming' | 'analysis'

export default function App() {
  const [screen, setScreen] = useState<Screen>('home')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [homeError, setHomeError] = useState<string | null>(null)

  // Streaming state
  const [streamProblem,  setStreamProblem]  = useState('')
  const [streamProvider, setStreamProvider] = useState<InputProvider>('anthropic')
  const [streamStatus,   setStreamStatus]   = useState('')
  const [streamSteps,    setStreamSteps]    = useState<Step[]>([])
  const [streamResults,  setStreamResults]  = useState<StepResult[]>([])
  const [streamTotal,    setStreamTotal]    = useState(0)

  const abortRef = useRef<AbortController | null>(null)

  const handleStream = useCallback(async (problem: string, provider: InputProvider) => {
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    setStreamProblem(problem)
    setStreamProvider(provider)
    setStreamStatus('')
    setStreamSteps([])
    setStreamResults([])
    setStreamTotal(0)
    setHomeError(null)
    setScreen('streaming')

    try {
      await streamReason(problem, provider, {
        onStatus: msg  => setStreamStatus(msg),
        onReady:  n    => setStreamTotal(n),
        onStep:   (i, step) => setStreamSteps(prev => {
          const next = [...prev]; next[i] = step; return next
        }),
        onResult: (i, ev) => setStreamResults(prev => {
          const next = [...prev]; next[i] = ev.result as StepResult; return next
        }),
        onDone: r => {
          setResult(r)
          setScreen('analysis')
        },
        onError: msg => {
          setHomeError(msg)
          setScreen('home')
        },
      }, abortRef.current.signal)
    } catch (err: unknown) {
      const e = err as Error
      if (e?.name !== 'AbortError') {
        setHomeError(e?.message || 'Streaming failed. Check server logs.')
        setScreen('home')
      }
    }
  }, [])

  const handleBack = useCallback(() => {
    abortRef.current?.abort()
    setResult(null)
    setHomeError(null)
    setScreen('home')
  }, [])

  if (screen === 'streaming') {
    return (
      <StreamingView
        problem={streamProblem}
        provider={streamProvider}
        status={streamStatus}
        steps={streamSteps}
        results={streamResults}
        totalCount={streamTotal}
        onCancel={handleBack}
      />
    )
  }

  if (screen === 'analysis' && result) {
    return <AnalysisView result={result} onBack={handleBack} />
  }

  return (
    <HomeScreen
      onResult={r => { setResult(r); setScreen('analysis') }}
      onStream={handleStream}
      initialError={homeError}
    />
  )
}
