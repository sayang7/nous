import type {
  AnalysisResult,
  Example,
  InputProvider,
  SchoolsResult,
  Step,
  StreamEvent,
} from './types'

const BASE = '/api'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  examples: () => get<Example[]>('/examples'),

  analyze: (steps: Step[], test_mode = true) =>
    post<AnalysisResult>('/analyze', { steps, test_mode }),

  reason: (problem: string, provider: InputProvider) =>
    post<AnalysisResult>('/reason', { problem, provider }),

  importUrl: (url: string) =>
    post<AnalysisResult>('/import/url', { url }),

  analyzeText: (text: string) =>
    post<AnalysisResult>('/analyze/text', { text }),

  schools: (steps: Step[], violations: unknown[], problem = '') =>
    post<SchoolsResult>('/schools', { steps, violations, problem }),
}

// ── SSE streaming ────────────────────────────────────────────────────────

export interface StreamCallbacks {
  onStatus?: (msg: string) => void
  onReady?: (count: number) => void
  onStep?: (i: number, step: Step) => void
  onResult?: (i: number, result: StreamEvent & { type: 'result' }) => void
  onDone?: (result: AnalysisResult) => void
  onError?: (msg: string) => void
}

export async function streamReason(
  problem: string,
  provider: InputProvider,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/stream/reason`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem, provider }),
    signal,
  })

  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })

    // Parse SSE lines
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const event: StreamEvent = JSON.parse(line.slice(6))
        switch (event.type) {
          case 'status': callbacks.onStatus?.(event.msg); break
          case 'ready':  callbacks.onReady?.(event.count); break
          case 'step':   callbacks.onStep?.(event.i, event.step); break
          case 'result': callbacks.onResult?.(event.i, event); break
          case 'done':
            callbacks.onDone?.({
              steps: (event as any).steps,
              results: (event as any).results,
              graph: (event as any).graph,
              violations: (event as any).violations,
              summary: (event as any).summary,
              problem: (event as any).problem,
              provider: (event as any).provider,
            })
            break
          case 'error': callbacks.onError?.(event.msg); break
        }
      } catch {
        // malformed SSE line — skip
      }
    }
  }
}
