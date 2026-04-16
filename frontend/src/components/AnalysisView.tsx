import { useState, useEffect } from 'react'
import { ArrowLeft } from 'lucide-react'
import type { AnalysisResult, SchoolsResult } from '../types'
import { StepPanel } from './StepPanel'
import { GraphPanel } from './GraphPanel'
import { SchoolsPanel } from './SchoolsPanel'
import { api } from '../api'

interface Props {
  result: AnalysisResult
  onBack: () => void
}

export function AnalysisView({ result, onBack }: Props) {
  const [selectedStep, setSelectedStep] = useState<number | null>(null)
  const [schools, setSchools] = useState<SchoolsResult | null>(null)
  const [schoolsLoading, setSchoolsLoading] = useState(false)
  const { summary, violations } = result
  const hasViolations = violations.length > 0

  // Load schools analysis after mount
  useEffect(() => {
    setSchoolsLoading(true)
    api.schools(result.steps, result.violations, result.problem ?? '')
      .then(setSchools)
      .catch(() => {})
      .finally(() => setSchoolsLoading(false))
  }, [result.steps, result.violations, result.problem])

  return (
    <div className="h-screen bg-canvas flex flex-col overflow-hidden">

      {/* Header */}
      <header className="border-b border-raised px-5 py-3 flex items-center gap-3 shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-text-muted hover:text-text-primary text-[13px] transition-colors"
        >
          <ArrowLeft size={13} />
          Back
        </button>
        <div className="w-px h-4 bg-raised" />
        <div className="flex-1 flex items-center gap-3 overflow-x-auto min-w-0">
          {result.problem && (
            <span className="text-[12px] text-text-muted truncate max-w-xs">{result.problem}</span>
          )}
          {result.problem && <div className="w-px h-3 bg-raised shrink-0" />}
          <span className="text-[11px] font-mono text-text-dim tabular shrink-0">
            {summary.total_steps} steps
          </span>
          <span
            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${
              hasViolations
                ? 'bg-red-dim border border-red/25 text-red'
                : 'bg-green-dim border border-green/20 text-green'
            }`}
          >
            {hasViolations
              ? `${violations.length} violation${violations.length !== 1 ? 's' : ''}`
              : 'Coherent'}
          </span>
          <span className="text-[11px] font-mono text-text-dim tabular shrink-0">
            {result.graph.nodes.length} commitments
          </span>
          {result.provider && (
            <span className="text-[11px] font-mono text-[#3f3f46] shrink-0 capitalize">{result.provider}</span>
          )}
        </div>
        <div className="w-5 h-5 rounded bg-indigo/15 border border-indigo/25 flex items-center justify-center shrink-0">
          <span className="text-indigo text-[10px] font-bold leading-none">◎</span>
        </div>
      </header>

      {/* Body — responsive two-panel */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left: Step timeline + Schools of thought */}
        <div
          className="flex flex-col border-r border-raised overflow-hidden"
          style={{ width: '55%', minWidth: 300 }}
        >
          {/* Steps */}
          <div className="flex-1 overflow-y-auto min-h-0">
            <StepPanel
              steps={result.steps}
              results={result.results}
              selectedStep={selectedStep}
              onSelectStep={setSelectedStep}
              problem={result.problem}
              sourceUrl={result.source_url}
            />
          </div>

          {/* Schools panel — accordion-style below steps */}
          {(schools || schoolsLoading) && (
            <div className="shrink-0" style={{ height: 220 }}>
              <SchoolsPanel data={schools} loading={schoolsLoading} />
            </div>
          )}
        </div>

        {/* Right: Commitment graph */}
        <div className="flex-1 overflow-hidden">
          <GraphPanel
            graph={result.graph}
            results={result.results}
            selectedStep={selectedStep}
            onSelectStep={setSelectedStep}
          />
        </div>

      </div>
    </div>
  )
}
