/**
 * GraphPanel — Custom force-directed SVG commitment graph.
 *
 * Layout: spring-repulsion simulation (synchronous, 500 iterations).
 * Step-ordering bias keeps earlier steps left, later steps right.
 * Pan: drag background. Zoom: scroll wheel.
 * Hover: dims unrelated nodes/edges. Click: syncs step selection.
 */
import { useState, useMemo, useRef, useCallback, useEffect } from 'react'
import type { GraphData, StepResult } from '../types'

interface Props {
  graph: GraphData
  results: StepResult[]
  selectedStep: number | null
  onSelectStep: (i: number | null) => void
}

// ── Layout constants ────────────────────────────────────────────────────
const SVG_W = 900
const SVG_H = 520
const NW = 162  // node width
const NH = 42   // node height

// Modality → colors
const MOD: Record<string, { strip: string; border: string; label: string }> = {
  asserted: { strip: '#60a5fa', border: '#2563eb', label: '#93c5fd' },
  possible: { strip: '#fbbf24', border: '#d97706', label: '#fde68a' },
  temporal: { strip: '#c084fc', border: '#9333ea', label: '#d8b4fe' },
  revised:  { strip: '#71717a', border: '#52525b', label: '#a1a1aa' },
}
const FALLBACK_MOD = MOD.asserted

// ── Force simulation ────────────────────────────────────────────────────
interface Vec2 { x: number; y: number }

function forceLayout(
  nodes: GraphData['nodes'],
  edges: GraphData['edges'],
): Map<string, Vec2> {
  const N = nodes.length
  if (N === 0) return new Map()
  if (N === 1) return new Map([[nodes[0].content, { x: SVG_W / 2, y: SVG_H / 2 }]])

  // Group by source_step
  const byStep = new Map<number, string[]>()
  nodes.forEach(n => {
    if (!byStep.has(n.source_step)) byStep.set(n.source_step, [])
    byStep.get(n.source_step)!.push(n.content)
  })
  const steps = [...byStep.keys()].sort((a, b) => a - b)
  const minS = steps[0]
  const sRange = (steps[steps.length - 1] - minS) || 1

  // Lookup
  const idx = new Map<string, number>()
  nodes.forEach((n, i) => idx.set(n.content, i))

  // Typed arrays for speed
  const px = new Float32Array(N)
  const py = new Float32Array(N)
  const vx = new Float32Array(N)
  const vy = new Float32Array(N)

  // Deterministic initial positions: x by step, y by rank within step
  nodes.forEach((n, i) => {
    const grp = byStep.get(n.source_step)!
    const gi = grp.indexOf(n.content)
    const gs = grp.length
    px[i] = 100 + ((n.source_step - minS) / sRange) * (SVG_W - 240)
    py[i] = gs === 1 ? SVG_H / 2 : 80 + (gi / (gs - 1)) * (SVG_H - 160)
  })

  // 500 iterations with cooling
  for (let iter = 0; iter < 500; iter++) {
    const a = 1 - iter / 500 // alpha (cooling)
    const s = a * a           // quadratic strength

    // Repulsion: every pair
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const dx = px[i] - px[j]
        const dy = py[i] - py[j]
        const d2 = dx * dx + dy * dy + 0.01
        if (d2 < 280 * 280) {
          const d = Math.sqrt(d2)
          const f = (7000 / d2) * s
          vx[i] += (dx / d) * f; vy[i] += (dy / d) * f
          vx[j] -= (dx / d) * f; vy[j] -= (dy / d) * f
        }
      }
    }

    // Springs: connected nodes
    edges.forEach(e => {
      const si = idx.get(e.from)
      const ti = idx.get(e.to)
      if (si === undefined || ti === undefined) return
      const dx = px[ti] - px[si]
      const dy = py[ti] - py[si]
      const d = Math.sqrt(dx * dx + dy * dy) + 0.01
      const f = (d - 175) * 0.09 * s
      vx[si] += (dx / d) * f; vy[si] += (dy / d) * f
      vx[ti] -= (dx / d) * f; vy[ti] -= (dy / d) * f
    })

    // Step-ordering pull (keeps temporal flow left→right)
    nodes.forEach((n, i) => {
      const tx = 100 + ((n.source_step - minS) / sRange) * (SVG_W - 240)
      vx[i] += (tx - px[i]) * 0.06 * a
      vy[i] += (SVG_H / 2 - py[i]) * 0.015 * a
    })

    // Integrate + damp + clamp
    for (let i = 0; i < N; i++) {
      vx[i] *= 0.6; vy[i] *= 0.6
      px[i] = Math.max(NW / 2 + 12, Math.min(SVG_W - NW / 2 - 12, px[i] + vx[i]))
      py[i] = Math.max(NH / 2 + 12, Math.min(SVG_H - NH / 2 - 12, py[i] + vy[i]))
    }
  }

  const out = new Map<string, Vec2>()
  nodes.forEach((n, i) => out.set(n.content, { x: px[i], y: py[i] }))
  return out
}

// ── Edge path (quadratic bezier) ────────────────────────────────────────
function edgePath(sx: number, sy: number, tx: number, ty: number): string {
  const dx = tx - sx, dy = ty - sy
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len < 2) return ''
  const nx = dx / len, ny = dy / len

  // Offset start/end from node center to its border
  const x1 = sx + nx * (NW / 2 + 3)
  const y1 = sy + ny * (NH / 2 + 3)
  const x2 = tx - nx * (NW / 2 + 10)
  const y2 = ty - ny * (NH / 2 + 3)

  // Perpendicular curve offset (scales with length but capped)
  const cv = Math.min(45, len * 0.22)
  const mx = (x1 + x2) / 2 + (-ny) * cv
  const my = (y1 + y2) / 2 + (nx) * cv

  return `M${x1.toFixed(1)},${y1.toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`
}

// ── Component ───────────────────────────────────────────────────────────
export function GraphPanel({ graph, results, selectedStep, onSelectStep }: Props) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [pan, setPan] = useState<Vec2>({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const dragRef = useRef({ active: false, last: { x: 0, y: 0 } })
  const svgRef = useRef<SVGSVGElement>(null)

  // Violated node set
  const violatedSet = useMemo(() => {
    const s = new Set<string>()
    results.forEach(r => { if (!r.coherent && r.violation?.violated) s.add(r.violation.violated) })
    return s
  }, [results])

  // Force layout — only recomputes when graph data changes
  const positions = useMemo(
    () => forceLayout(graph.nodes, graph.edges),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [graph.nodes.map(n => n.content).join('|'), graph.edges.length],
  )

  // Hovered node's direct neighbors
  const neighbors = useMemo(() => {
    if (!hovered) return new Set<string>()
    const s = new Set<string>()
    graph.edges.forEach(e => {
      if (e.from === hovered) s.add(e.to)
      if (e.to === hovered) s.add(e.from)
    })
    return s
  }, [hovered, graph.edges])

  // Wheel → zoom (centered)
  useEffect(() => {
    const el = svgRef.current
    if (!el) return
    const handler = (e: WheelEvent) => {
      e.preventDefault()
      const f = e.deltaY < 0 ? 1.12 : 0.89
      setZoom(z => Math.max(0.3, Math.min(3.5, z * f)))
    }
    el.addEventListener('wheel', handler, { passive: false })
    return () => el.removeEventListener('wheel', handler)
  }, [])

  // Pointer drag → pan
  const onPtrDown = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    const tag = (e.target as Element).tagName
    if (tag === 'svg' || (e.target as Element).getAttribute('data-bg')) {
      dragRef.current = { active: true, last: { x: e.clientX, y: e.clientY } }
      svgRef.current?.setPointerCapture(e.pointerId)
    }
  }, [])

  const onPtrMove = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (!dragRef.current.active) return
    const dx = (e.clientX - dragRef.current.last.x) / zoom
    const dy = (e.clientY - dragRef.current.last.y) / zoom
    dragRef.current.last = { x: e.clientX, y: e.clientY }
    setPan(p => ({ x: p.x + dx, y: p.y + dy }))
  }, [zoom])

  const onPtrUp = useCallback(() => { dragRef.current.active = false }, [])

  if (!graph.nodes.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-text-dim">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="opacity-30">
          <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 3" />
          <circle cx="16" cy="16" r="3" fill="currentColor" />
        </svg>
        <span className="text-xs font-mono">No graph data</span>
      </div>
    )
  }

  // SVG inner transform: zoom around canvas center + pan
  const innerTransform = `translate(${SVG_W / 2 + pan.x * zoom},${SVG_H / 2 + pan.y * zoom}) scale(${zoom}) translate(${-SVG_W / 2},${-SVG_H / 2})`

  return (
    <div className="flex flex-col h-full" style={{ background: '#09090b' }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="px-4 py-2.5 flex items-center justify-between border-b border-raised shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-text-dim uppercase tracking-[0.12em]">
            Commitment Graph
          </span>
          <span className="text-[10px] font-mono text-[#3f3f46] tabular">
            {graph.nodes.length}N · {graph.edges.length}E
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#3f3f46]">scroll to zoom · drag to pan</span>
          <button
            onClick={() => { setPan({ x: 0, y: 0 }); setZoom(1) }}
            className="text-[10px] font-mono text-text-dim hover:text-text-muted px-2 py-0.5 rounded border border-raised hover:border-border transition-colors"
          >
            reset
          </button>
        </div>
      </div>

      {/* ── SVG canvas ────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden relative">
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          onPointerDown={onPtrDown}
          onPointerMove={onPtrMove}
          onPointerUp={onPtrUp}
          onPointerLeave={onPtrUp}
          style={{
            display: 'block',
            userSelect: 'none',
            cursor: dragRef.current.active ? 'grabbing' : 'grab',
          }}
        >
          <defs>
            {/* Arrowheads */}
            <marker id="arr-default" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0.5 L5,3 L0,5.5 Z" fill="#3f3f46" />
            </marker>
            <marker id="arr-violated" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0.5 L5,3 L0,5.5 Z" fill="#f87171" />
            </marker>
            <marker id="arr-active" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0.5 L5,3 L0,5.5 Z" fill="#818cf8" />
            </marker>
            {/* Violated glow filter */}
            <filter id="glow-red" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="glow-indigo" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          <g transform={innerTransform}>
            {/* Background click to deselect */}
            <rect
              data-bg="1"
              x={-5000} y={-5000} width={12000} height={12000}
              fill="transparent"
              onClick={() => { setHovered(null); onSelectStep(null) }}
            />

            {/* ── Edges ───────────────────────────────────────────────── */}
            {graph.edges.map((edge, i) => {
              const sp = positions.get(edge.from)
              const tp = positions.get(edge.to)
              if (!sp || !tp) return null

              const isViolated = violatedSet.has(edge.from) || violatedSet.has(edge.to)
              const isHovered  = hovered === edge.from || hovered === edge.to
              const isDimmed   = hovered !== null && !isHovered

              let stroke = '#27272a'
              let marker = 'url(#arr-default)'
              if (isViolated) { stroke = 'rgba(248,113,113,0.45)'; marker = 'url(#arr-violated)' }
              if (isHovered)  { stroke = 'rgba(129,140,248,0.8)';  marker = 'url(#arr-active)' }

              const path = edgePath(sp.x, sp.y, tp.x, tp.y)
              if (!path) return null

              return (
                <path
                  key={i}
                  d={path}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={isHovered ? 1.5 : 1}
                  strokeDasharray={edge.confidence < 0.8 ? '5,4' : undefined}
                  opacity={isDimmed ? 0.08 : 1}
                  markerEnd={marker}
                  style={{ transition: 'opacity 0.12s' }}
                />
              )
            })}

            {/* ── Nodes ───────────────────────────────────────────────── */}
            {graph.nodes.map(node => {
              const p = positions.get(node.content)
              if (!p) return null

              const isViolated    = violatedSet.has(node.content)
              const isSelected    = selectedStep !== null && node.source_step - 1 === selectedStep
              const isHov         = hovered === node.content
              const isNeighbor    = neighbors.has(node.content)
              const isDimmed      = hovered !== null && !isHov && !isNeighbor

              const mc = MOD[node.modality] ?? FALLBACK_MOD
              const nx = p.x - NW / 2
              const ny = p.y - NH / 2

              // Label — truncate to fit node
              const label = node.content.length > 24 ? node.content.slice(0, 21) + '…' : node.content

              // Border color priority: violated > selected > hovered > default
              const borderColor = isViolated
                ? '#f87171'
                : isSelected
                  ? '#818cf8'
                  : isHov
                    ? mc.border
                    : '#27272a'

              const fillColor = isViolated
                ? 'rgba(248,113,113,0.07)'
                : isSelected
                  ? 'rgba(129,140,248,0.09)'
                  : '#111113'

              return (
                <g
                  key={node.content}
                  transform={`translate(${nx.toFixed(1)},${ny.toFixed(1)})`}
                  style={{
                    cursor: 'pointer',
                    opacity: isDimmed ? 0.15 : 1,
                    transition: 'opacity 0.12s',
                    filter: isViolated ? 'url(#glow-red)' : isSelected ? 'url(#glow-indigo)' : undefined,
                  }}
                  onClick={e => {
                    e.stopPropagation()
                    const step = node.source_step - 1
                    onSelectStep(isSelected && !isViolated ? null : step)
                  }}
                  onMouseEnter={() => setHovered(node.content)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <title>{node.content}{'\n'}[{node.modality}] Step {node.source_step}{isViolated ? '\n⚠ VIOLATED' : ''}</title>

                  {/* Node body */}
                  <rect
                    width={NW} height={NH}
                    rx={6}
                    fill={fillColor}
                    stroke={borderColor}
                    strokeWidth={isViolated || isSelected ? 1.5 : 1}
                    strokeDasharray={!node.is_explicit ? '5,3' : undefined}
                  />

                  {/* Modality strip (left edge) */}
                  <rect
                    x={0} y={0} width={3} height={NH}
                    rx="1.5"
                    fill={isViolated ? '#f87171' : mc.strip}
                    opacity={0.85}
                  />

                  {/* Content text */}
                  <text
                    x={11} y={NH / 2 - 4}
                    dominantBaseline="middle"
                    fontSize={10.5}
                    fontFamily='"JetBrains Mono", "Fira Code", monospace'
                    fill={isViolated ? '#fca5a5' : '#e4e4e7'}
                  >
                    {label}
                  </text>

                  {/* Meta row: modality + step */}
                  <text
                    x={11} y={NH / 2 + 10}
                    dominantBaseline="middle"
                    fontSize={8.5}
                    fontFamily='"JetBrains Mono", monospace'
                    fill={isViolated ? '#ef4444' : '#3f3f46'}
                  >
                    {isViolated ? '⚠ violated' : `${node.modality} · step ${node.source_step}`}
                  </text>
                </g>
              )
            })}
          </g>
        </svg>
      </div>

      {/* ── Legend ─────────────────────────────────────────────────────── */}
      <div className="px-4 py-2 border-t border-raised flex items-center gap-5 flex-wrap shrink-0">
        {[
          { color: '#60a5fa', label: 'Asserted' },
          { color: '#fbbf24', label: 'Possible' },
          { color: '#c084fc', label: 'Temporal' },
          { color: '#71717a', label: 'Revised' },
          { color: '#f87171', label: 'Violated' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: color }} />
            <span className="text-[10px] font-mono text-text-dim">{label}</span>
          </div>
        ))}
        <div className="flex items-center gap-1.5 ml-auto">
          <div className="w-8 h-px border-t border-dashed border-[#3f3f46]" />
          <span className="text-[10px] font-mono text-[#3f3f46]">derived</span>
        </div>
      </div>
    </div>
  )
}
