/**
 * StreamingView — Live analysis screen.
 *
 * Shows reasoning steps appearing one by one as the AI generates them,
 * with Nous analyzing each in real time. Steps fade in with violation
 * highlights appearing inline — like a Grammarly annotation unfolding live.
 */
import { useEffect, useRef } from 'react'
import type { Step, StepResult } from '../types'

interface Props {
  problem: string
  provider: string
  status: string
  steps: Step[]
  results: StepResult[]  // may have fewer entries than steps while streaming
  totalCount: number
  onCancel: () => void
}

const VIOLATION_COLOR: Record<string, string> = {
  ModusPonensViolation:        '#f87171',
  BeliefRevisionFailure:       '#fbbf24',
  ModalScopeError:             '#60a5fa',
  TemporalCoherenceViolation:  '#fbbf24',
  ReferentialOpacityFailure:   '#c084fc',
}

export function StreamingView({
  problem, provider, status, steps, results, totalCount, onCancel,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll as steps arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [steps.length])

  const violationCount = results.filter(r => !r.coherent).length

  return (
    <div className="h-screen bg-canvas flex flex-col overflow-hidden">

      {/* Header */}
      <header className="border-b border-raised px-5 py-3 flex items-center gap-3 shrink-0">
        <div className="w-6 h-6 rounded bg-indigo/15 border border-indigo/25 flex items-center justify-center">
          <span className="text-indigo text-[11px] font-bold leading-none">◎</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-mono text-text-dim truncate">{problem}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {steps.length > 0 && (
            <span className="text-[11px] font-mono text-text-dim tabular">
              {steps.length}{totalCount > 0 ? `/${totalCount}` : ''} steps
              {violationCount > 0 && (
                <span className="text-red ml-2">· {violationCount} ⚠</span>
              )}
            </span>
          )}
          <span className="text-[11px] font-mono text-text-dim capitalize">{provider}</span>
          <button
            onClick={onCancel}
            className="text-[11px] text-text-dim hover:text-text-muted px-2 py-0.5 rounded border border-raised hover:border-border transition-colors"
          >
            cancel
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">

        {/* Status / thinking indicator */}
        {steps.length === 0 && (
          <div className="flex items-center gap-3 text-text-dim mb-8">
            <ThinkingDots />
            <span className="text-[13px]">{status || `Thinking with ${provider}…`}</span>
          </div>
        )}

        {/* Live steps */}
        <div className="space-y-4">
          {steps.map((step, i) => {
            const result = results[i]
            const isAnalyzed = result !== undefined
            const isViolation = isAnalyzed && !result.coherent
            const vcolor = isViolation && result.violation
              ? VIOLATION_COLOR[result.violation.type] ?? '#f87171'
              : null

            return (
              <div
                key={i}
                className="relative pl-8"
                style={{ animation: 'fadeSlideIn 0.3s ease forwards' }}
              >
                {/* Timeline dot */}
                <div className="absolute left-1.5 top-3.5">
                  {!isAnalyzed ? (
                    <div className="w-3 h-3 rounded-full border border-[#3f3f46] bg-canvas">
                      <ThinkingPulse />
                    </div>
                  ) : isViolation ? (
                    <div
                      className="w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center"
                      style={{ borderColor: vcolor!, background: vcolor! + '15' }}
                    >
                      <span style={{ fontSize: 7, color: vcolor! }}>⚠</span>
                    </div>
                  ) : (
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-green bg-green/10" />
                  )}
                </div>

                {/* Step card */}
                <div
                  className="rounded-lg overflow-hidden transition-all"
                  style={{
                    background: isViolation ? vcolor! + '08' : '#111113',
                    border: `1px solid ${isViolation ? vcolor! + '30' : '#27272a'}`,
                  }}
                >
                  {/* Step meta */}
                  <div className="px-4 py-3">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[10px] font-mono text-text-dim">Step {i + 1}</span>
                      {isAnalyzed && (
                        <span className="text-[10px] font-mono text-[#3f3f46]">
                          +{result.commitments_added} commitment{result.commitments_added !== 1 ? 's' : ''}
                        </span>
                      )}
                      {isViolation && result.violation && (
                        <span
                          className="ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded"
                          style={{ color: vcolor!, background: vcolor! + '15', border: `1px solid ${vcolor! + '30'}` }}
                        >
                          {result.violation.label}
                        </span>
                      )}
                      {!isAnalyzed && (
                        <span className="ml-auto text-[10px] font-mono text-[#3f3f46] flex items-center gap-1">
                          <ThinkingDots small /> analyzing
                        </span>
                      )}
                    </div>

                    {/* Reasoning text */}
                    <p className="text-[13px] text-text-primary leading-relaxed mb-2">
                      {step.text}
                    </p>

                    {/* Action */}
                    <p className="text-[11px] text-text-muted font-mono">
                      <span className="text-[#3f3f46]">→ </span>{step.action}
                    </p>
                  </div>

                  {/* Violation inline callout */}
                  {isViolation && result.violation && (
                    <div
                      className="px-4 py-3 border-t"
                      style={{
                        borderColor: vcolor! + '20',
                        borderLeft: `3px solid ${vcolor!}`,
                        background: vcolor! + '05',
                      }}
                    >
                      <p className="text-[11px] leading-relaxed mb-1">
                        <span className="font-semibold" style={{ color: vcolor! }}>
                          Violated: </span>
                        <span className="text-text-muted">{result.violation.violated}</span>
                      </p>
                      {result.violation.chain && (
                        <pre
                          className="text-[10px] font-mono leading-relaxed whitespace-pre-wrap break-words mt-1"
                          style={{ color: vcolor! + 'aa' }}
                        >
                          {result.violation.chain}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Streaming indicator (after steps start appearing) */}
        {steps.length > 0 && steps.length === results.length && steps.length < (totalCount || Infinity) && (
          <div className="flex items-center gap-2 mt-4 pl-8 text-text-dim">
            <ThinkingDots />
            <span className="text-[12px] font-mono">more steps…</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}

// ── Micro-components ─────────────────────────────────────────────────────

function ThinkingDots({ small }: { small?: boolean }) {
  const sz = small ? 4 : 5
  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map(i => (
        <div
          key={i}
          className="rounded-full bg-current"
          style={{
            width: sz, height: sz,
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}

function ThinkingPulse() {
  return (
    <div
      className="w-3 h-3 rounded-full"
      style={{
        background: '#3f3f46',
        animation: 'ringPulse 1.5s ease-in-out infinite',
      }}
    >
      <style>{`
        @keyframes ringPulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  )
}
