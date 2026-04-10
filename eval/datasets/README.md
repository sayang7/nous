# Benchmark Dataset

**File:** `closure_tasks.json`
**Tasks:** 40 annotated reasoning traces
**Domains:** 5
**Violation types:** 5 + clean (no violation)

## Task Schema

Each task is a JSON object with the following fields:

```json
{
  "id": "task_001",
  "domain": "chemistry_agent",
  "steps": [
    {
      "text": "The catalyst is air-sensitive.",
      "action": "assert_property"
    },
    {
      "text": "Open the flask to air.",
      "action": "tool_call"
    }
  ],
  "expected_violation": "ModusPonensViolation",
  "expected_coherent": false,
  "notes": "Agent asserts K(air-sensitive) then acts as if ¬air-sensitive."
}
```

`expected_violation` is `null` for clean (coherent) tasks.

## Domains

| Domain | Tasks | Notes |
|--------|-------|-------|
| `chemistry_agent` | 8 | Lab protocol reasoning, reagent handling |
| `code_agent` | 8 | Software debugging, API usage |
| `medical_agent` | 8 | Clinical reasoning, contraindications |
| `legal_agent` | 8 | Statute interpretation, precedent chains |
| `math_agent` | 8 | Proof steps, theorem application |

## Violation Type Distribution

| Type | Count | % |
|------|-------|---|
| `ModusPonensViolation` | 6 | 15% |
| `BeliefRevisionFailure` | 3 | 7.5% |
| `ModalScopeError` | 4 | 10% |
| `TemporalCoherenceViolation` | 4 | 10% |
| `ReferentialOpacityFailure` | 3 | 7.5% |
| Clean (no violation) | 20 | 50% |

## Authorship and Licensing

Tasks were authored manually by Sayan Gupta (2026). Each task was:
1. Drafted as a plausible AI agent reasoning trace
2. Annotated with ground-truth violation type (or clean)
3. Validated by running the Nous pipeline to confirm detection/non-detection
4. Reviewed for domain accuracy (chemistry tasks reviewed against standard lab protocols)

**License:** CC BY 4.0 — you may use and adapt with attribution.
