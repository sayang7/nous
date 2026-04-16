/**
 * SchoolsPanel — Multi-perspective philosophical analysis of a reasoning trace.
 *
 * Shows how five philosophical schools view the reasoning:
 * Bayesian | Formal Logic | Popperian | Pragmatism | Dialectical
 */
import { useState } from 'react'
import type { School, SchoolsResult } from '../types'

interface Props {
  data: SchoolsResult | null
  loading: boolean
}

const SCHOOL_META: Record<string, { color: string; bg: string; abbr: string }> = {
  'Bayesian Epistemology':     { color: '#60a5fa', bg: 'rgba(96,165,250,0.08)',  abbr: 'B' },
  'Formal Logic':              { color: '#818cf8', bg: 'rgba(129,140,248,0.08)', abbr: 'F' },
  'Popperian Falsificationism':{ color: '#4ade80', bg: 'rgba(74,222,128,0.08)',  abbr: 'P' },
  'Pragmatism':                { color: '#fbbf24', bg: 'rgba(251,191,36,0.08)',  abbr: 'Pr' },
  'Dialectical Analysis':      { color: '#c084fc', bg: 'rgba(192,132,252,0.08)', abbr: 'D' },
}

function getMeta(name: string) {
  return SCHOOL_META[name] ?? { color: '#a1a1aa', bg: 'rgba(161,161,170,0.08)', abbr: '?' }
}

export function SchoolsPanel({ data, loading }: Props) {
  const [active, setActive] = useState(0)

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <SectionHeader />
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-2 text-text-dim">
            <svg width="14" height="14" viewBox="0 0 14 14" className="animate-spin" fill="none">
              <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="8 8" />
            </svg>
            <span className="text-xs font-mono">Analyzing perspectives…</span>
          </div>
        </div>
      </div>
    )
  }

  if (!data) return null

  const schools = data.schools
  if (!schools?.length) return null

  const current: School = schools[active]
  const meta = getMeta(current.name)

  return (
    <div className="flex flex-col h-full border-t border-raised">
      <SectionHeader dominantStyle={data.dominant_style} />

      {/* Tab bar */}
      <div className="flex gap-px px-3 py-2 overflow-x-auto shrink-0">
        {schools.map((s, i) => {
          const m = getMeta(s.name)
          const isActive = active === i
          return (
            <button
              key={s.name}
              onClick={() => setActive(i)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all shrink-0"
              style={{
                background: isActive ? m.bg : 'transparent',
                color: isActive ? m.color : '#52525b',
                border: `1px solid ${isActive ? m.color + '40' : 'transparent'}`,
              }}
            >
              <span
                className="w-4 h-4 rounded text-[9px] font-bold flex items-center justify-center shrink-0"
                style={{ background: isActive ? m.color + '25' : '#27272a', color: isActive ? m.color : '#52525b' }}
              >
                {m.abbr}
              </span>
              <span className="hidden sm:inline">{s.name.split(' ')[0]}</span>
            </button>
          )
        })}
      </div>

      {/* Active school content */}
      <div
        className="flex-1 overflow-y-auto px-4 pb-4"
        key={active}
      >
        <div className="space-y-3">
          {/* Headline */}
          <div
            className="px-3 py-2.5 rounded-lg"
            style={{ background: meta.bg, border: `1px solid ${meta.color}25` }}
          >
            <p
              className="text-[13px] font-semibold leading-snug"
              style={{ color: meta.color }}
            >
              {current.headline}
            </p>
          </div>

          {/* Analysis */}
          <div>
            <p className="text-[10px] font-mono text-text-dim uppercase tracking-[0.1em] mb-1.5">Analysis</p>
            <p className="text-[13px] text-text-secondary leading-relaxed">{current.analysis}</p>
          </div>

          {/* Prescription */}
          <div className="pt-1">
            <p className="text-[10px] font-mono text-text-dim uppercase tracking-[0.1em] mb-1.5">Prescription</p>
            <p
              className="text-[12px] leading-relaxed italic"
              style={{ color: meta.color + 'cc' }}
            >
              "{current.prescription}"
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function SectionHeader({ dominantStyle }: { dominantStyle?: string }) {
  return (
    <div className="px-4 py-2 flex items-center gap-2 shrink-0">
      <span className="text-[10px] font-mono text-text-dim uppercase tracking-[0.12em]">
        Perspectives
      </span>
      {dominantStyle && (
        <span className="text-[10px] font-mono text-[#3f3f46] ml-1">
          · {dominantStyle}
        </span>
      )}
    </div>
  )
}
