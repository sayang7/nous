# Lean 4 Proofs

Formal soundness proofs for the Nous violation taxonomy, written in Lean 4.

## Building

```bash
# Install Lean 4 via elan (if not already installed)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Build all proofs
lake build
```

Requires Lean 4 toolchain version pinned in `lean-toolchain` (currently `leanprover/lean4:v4.16.0`).

## Files

### `ClosureViolation.lean`

The main theory file. Contains:
- `CommitmentSet` — formal model of an agent's belief state as a set of propositions
- `closure` — the epistemic closure operator: the deductive consequences of a belief set
- `isCoherent` — coherence predicate: an action is coherent iff it does not contradict the closure
- Violation type definitions (inductive type) with one constructor per violation type
- Soundness theorem: `violationImpliesIncoherence` — if a violation is detected, the agent is incoherent

### `Examples.lean`

Concrete worked examples instantiating each violation type. Used to validate the definitions are non-trivially satisfiable.

## The One `sorry`

`ClosureViolation.lean` contains one `sorry` in the proof of `temporalCoherenceSound`. This is a known gap: the temporal coherence theorem requires a well-founded ordering on time indices, which requires a more involved proof than the other types. The statement is believed to be correct — the `sorry` is a proof stub, not a claim of truth. Fixing this is tracked in the issues.

## Decidability

Not all violation types are Lean-decidable in full generality:

| Violation Type | Decidable? | Notes |
|----------------|-----------|-------|
| `ModusPonensViolation` | ✓ Decidable | Over stated propositions only |
| `ModalScopeError` | ✓ Decidable | Within stated modal frame |
| `BeliefRevisionFailure` | ✓ Decidable | If assertions are timestamped |
| `TemporalCoherenceViolation` | ✓ Decidable | If temporal operators are explicit |
| `ReferentialOpacityFailure` | ✗ Not decidable | Requires world knowledge (co-reference resolution) |

The Lean proofs cover the decidable subset. Detection of `ReferentialOpacityFailure` in Python falls back to LLM-based entailment.
