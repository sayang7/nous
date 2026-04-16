import type { Step, StepResult, Violation } from '../types'

interface Props {
  steps: Step[]
  results: StepResult[]
  selectedStep: number | null
  onSelectStep: (i: number | null) => void
  problem?: string
  sourceUrl?: string
}

const VIOLATION_STYLE: Record<string, { pill: string; border: string; label: string }> = {
  ModusPonensViolation:       { pill: 'bg-red-dim border-red/30 text-red',        border: '#f87171', label: 'text-red' },
  BeliefRevisionFailure:      { pill: 'bg-amber-dim border-amber/30 text-amber',   border: '#fbbf24', label: 'text-amber' },
  ModalScopeError:            { pill: 'bg-blue-dim border-blue/30 text-blue',      border: '#60a5fa', label: 'text-blue' },
  TemporalCoherenceViolation: { pill: 'bg-amber-dim border-amber/30 text-amber',   border: '#fbbf24', label: 'text-amber' },
  ReferentialOpacityFailure:  { pill: 'bg-purple-dim border-purple/30 text-purple',border: '#c084fc', label: 'text-purple' },
}
const DEFAULT_VSTYLE = VIOLATION_STYLE.ModusPonensViolation

function ViolationCard({ v }: { v: Violation }) {
  const style = VIOLATION_STYLE[v.type] ?? DEFAULT_VSTYLE
  return (
    <div
      className="mt-2 rounded-md overflow-hidden"
      style={{ borderLeft: `3px solid ${style.border}`, background: 'rgba(255,255,255,0.03)', border: `1px solid rgba(255,255,255,0.07)`, borderLeftColor: style.border }}
    >
      <div className="px-3 py-2.5">
        <div className="flex items-center justify-between mb-1.5">
          <span className={`text-[11px] font-semibold ${style.label}`}>{v.label}</span>
          {v.confidence !== undefined && (
            <span className="text-[10px] font-mono text-text-dim tabular">
              {Math.round(v.confidence * 100)}% confidence
            </span>
          )}
        </div>
        <p className="text-[12px] text-text-muted leading-relaxed mb-1">
          <span className="text-text-dim">Violated: </span>{v.violated}
        </p>
        {v.chain && (
          <pre className="text-[10px] font-mono text-text-dim mt-1.5 leading-relaxed whitespace-pre-wrap break-words">
            {v.chain}
          </pre>
        )}
        {v.explanation && (
          <p className="text-[11px] text-text-dim mt-1.5 leading-relaxed italic">{v.explanation}</p>
        )}
      </div>
    </div>
  )
}

export function StepPanel({ steps, results, selectedStep, onSelectStep, problem, sourceUrl }: Props) {
  const totalCommitments = results.length > 0 ? (results[results.length - 1]?.total_commitments ?? 0) : 0
  const violationCount = results.filter(r => !r.coherent).length

  return (
    <div className="flex flex-col h-full">

      {/* ── Source context ──────────────────────────────────────────── */}
      {(problem || sourceUrl) && (
        <div className="px-5 py-4 border-b border-raised">
          <p className="text-[10px] font-mono text-text-dim uppercase tracking-[0.12em] mb-1.5">
            {sourceUrl ? 'Source' : 'Problem'}
          </p>
          <p className="text-[13px] text-text-secondary leading-relaxed">
            {problem || sourceUrl}
          </p>
        </div>
      )}

      {/* ── Stats bar ───────────────────────────────────────────────── */}
      <div className="px-5 py-2.5 border-b border-raised flex items-center gap-5 shrink-0">
        <StatChip value={steps.length} label="steps" />
        <StatChip value={violationCount} label="violations" alert={violationCount > 0} />
        <StatChip value={totalCommitments} label="commitments" />
        <StatChip value={results.filter(r => r.coherent).length} label="coherent" success />
      </div>

      {/* ── Timeline ────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="relative">
          {/* Connector line — sits behind all step cards */}
          <div
            aria-hidden
            className="absolute left-[19px] top-3 bottom-3 w-px"
            style={{ background: 'linear-gradient(to bottom, #27272a 0%, #27272a 100%)' }}
          />

          <div className="space-y-3">
            {steps.map((step, i) => {
              const res = results[i]
              const violation = res?.violation ?? null
              const isViolation = res && !res.coherent
              const isSelected = selectedStep === i

              return (
                <StepCard
                  key={i}
                  index={i}
                  step={step}
                  res={res}
                  violation={violation}
                  isViolation={!!isViolation}
                  isSelected={isSelected}
                  onClick={() => onSelectStep(isSelected ? null : i)}
                />
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────────

function StatChip({ value, label, alert, success }: {
  value: number; label: string; alert?: boolean; success?: boolean
}) {
  const color = alert ? 'text-red' : success ? 'text-green' : 'text-text-secondary'
  return (
    <div className="flex items-baseline gap-1">
      <span className={`text-sm font-semibold tabular ${color}`}>{value}</span>
      <span className="text-[10px] font-mono text-text-dim">{label}</span>
    </div>
  )
}

function StepCard({ index, step, res, violation, isViolation, isSelected, onClick }: {
  index: number
  step: Step
  res?: StepResult
  violation: Violation | null
  isViolation: boolean
  isSelected: boolean
  onClick: () => void
}) {
  const vstyle = violation ? (VIOLATION_STYLE[violation.type] ?? DEFAULT_VSTYLE) : null

  return (
    <div
      className="relative pl-9 cursor-pointer group"
      onClick={onClick}
    >
      {/* Timeline dot */}
      <div
        className="absolute left-3 top-3.5 flex items-center justify-center"
        style={{ zIndex: 1 }}
      >
        <div
          className="w-3.5 h-3.5 rounded-full border-2 transition-all"
          style={{
            background: isViolation ? 'rgba(248,113,113,0.15)' : 'rgba(74,222,128,0.12)',
            borderColor: isViolation ? '#f87171' : '#4ade80',
            boxShadow: isSelected
              ? isViolation
                ? '0 0 0 3px rgba(248,113,113,0.2)'
                : '0 0 0 3px rgba(129,140,248,0.25)'
              : 'none',
          }}
        />
      </div>

      {/* Card */}
      <div
        className="rounded-lg overflow-hidden transition-all"
        style={{
          background: isSelected
            ? 'rgba(129,140,248,0.06)'
            : isViolation
              ? 'rgba(248,113,113,0.05)'
              : '#111113',
          border: `1px solid ${
            isSelected
              ? 'rgba(129,140,248,0.35)'
              : isViolation
                ? 'rgba(248,113,113,0.25)'
                : '#27272a'
          }`,
        }}
      >
        {/* Card header */}
        <div className="px-3.5 py-3">
          {/* Step meta row */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-mono text-text-dim">Step {index + 1}</span>
            {res && (
              <span className="text-[10px] font-mono text-[#3f3f46]">
                +{res.commitments_added} commitment{res.commitments_added !== 1 ? 's' : ''}
              </span>
            )}
            {violation && vstyle && (
              <span className={`ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded border ${vstyle.pill}`}>
                {violation.label}
              </span>
            )}
          </div>

          {/* Reasoning text */}
          <p className="text-[13px] text-text-primary leading-relaxed mb-2" style={{ fontWeight: 400 }}>
            {isSelected
              ? step.text
              : step.text.length > 130
                ? step.text.slice(0, 127) + '…'
                : step.text}
          </p>

          {/* Action row */}
          <div className="flex items-start gap-1.5">
            <span className="text-[11px] text-[#3f3f46] mt-0.5">→</span>
            <p className="text-[11px] text-text-muted leading-relaxed font-mono">{step.action}</p>
          </div>
        </div>

        {/* Violation detail — visible when expanded or always for violations */}
        {violation && (isSelected || isViolation) && (
          <div className="px-3.5 pb-3">
            <ViolationCard v={violation} />
          </div>
        )}
      </div>
    </div>
  )
}
