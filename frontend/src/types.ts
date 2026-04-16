export interface Step {
  text: string
  action: string
  step?: number
}

export interface StepResult {
  step_index: number
  coherent: boolean
  violation: Violation | null
  commitments_added: number
  total_commitments: number
}

export interface Violation {
  type: string
  label: string
  confidence: number
  action: string
  violated: string
  step: number
  chain: string
  explanation?: string
}

export interface GraphNode {
  content: string
  source_step: number
  is_explicit: boolean
  modality: string
}

export interface GraphEdge {
  from: string
  to: string
  rule: string
  confidence: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  violations: { chain: string; type: string; label: string; confidence: number; step: number }[]
}

export interface AnalysisResult {
  steps: Step[]
  results: StepResult[]
  graph: GraphData
  violations: Violation[]
  summary: {
    total_steps: number
    violation_count: number
    coherent_count: number
  }
  problem?: string
  provider?: string
  source_url?: string
}

export interface Example {
  id: string
  icon: string
  title: string
  domain: string
  desc: string
  watch: string
  steps: Step[]
}

export type InputProvider = 'anthropic' | 'openai' | 'gemini'

// ── Schools of thought ───────────────────────────────────────────────────

export interface School {
  name: string
  headline: string
  analysis: string
  prescription: string
}

export interface SchoolsResult {
  dominant_style: string
  schools: School[]
}

// ── Streaming ────────────────────────────────────────────────────────────

export type StreamEvent =
  | { type: 'status'; msg: string }
  | { type: 'ready'; count: number }
  | { type: 'step'; i: number; step: Step }
  | { type: 'result'; i: number; result: StepResult }
  | { type: 'done' } & AnalysisResult
  | { type: 'error'; msg: string }

// Partial result built up during streaming
export interface StreamingState {
  status: string
  steps: Step[]
  results: StepResult[]
  totalCount: number
  done: boolean
  final: AnalysisResult | null
  error: string | null
}
