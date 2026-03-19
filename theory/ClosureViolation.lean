/-
  ClosureGuard: Formal Definitions for Epistemic Closure Violations
  in LLM Agent Reasoning Traces

  Philosophical grounding:
  - Hintikka (1962): K(P) ∧ K(P→Q) → K(Q)
  - Brandom: inferential commitments from assertions persist as
    structural obligations in discourse, regardless of internal state.

  We formalize the detection of *belief-action* incoherence: an agent
  asserts P, P entails Q, yet the agent acts as though ¬Q. This is
  distinct from self-contradiction (P ∧ ¬P) — it targets the gap
  between stated beliefs and downstream actions.
-/

/-- A proposition the agent has committed to in its trace. -/
structure Belief where
  content : String
  deriving Repr, BEq, Inhabited

/-- An action the agent performed. -/
structure Action where
  description : String
  deriving Repr, BEq, Inhabited

/-- A single step in a reasoning trace, containing
    the agent's text output and action taken. -/
structure AgentStep where
  text : String
  action : Action
  stepIndex : Nat
  deriving Repr, Inhabited

/-- A reasoning trace is a list of agent steps. -/
def ReasoningTrace := List AgentStep

/-- An entailment relationship between two beliefs:
    `premise` commits the agent to `conclusion`. -/
structure Entailment where
  premise : Belief
  conclusion : Belief
  deriving Repr

/-- Taxonomy of epistemic closure violation types.
    This is the core theoretical contribution. -/
inductive ViolationType where
  /-- Stated P, stated P→Q, acted as ¬Q.
      Classical modus ponens failure in the action layer. -/
  | ModusPonensViolation
  /-- New evidence contradicts prior belief P, but P is not updated.
      Failure to perform belief revision per AGM theory. -/
  | BeliefRevisionFailure
  /-- Confused "X is possible" (◇X) with "X is necessary" (□X),
      or vice versa. Modal operator scope error. -/
  | ModalScopeError
  /-- Committed to P-at-t₁, later acted as ¬P-at-t₁.
      Violation of temporal coherence for time-indexed beliefs. -/
  | TemporalCoherenceViolation
  /-- Treated co-referential terms as if they denote distinct entities.
      Failure of substitutivity in epistemic contexts. -/
  | ReferentialOpacityFailure
  deriving Repr, BEq, Inhabited

/-- A detected closure violation in a reasoning trace. -/
structure ClosureViolation where
  /-- The belief the agent explicitly stated (P). -/
  antecedent : Belief
  /-- The belief that P commits the agent to (Q). -/
  entailed : Belief
  /-- The step where the agent's action contradicts Q. -/
  step : AgentStep
  /-- The type of violation from the taxonomy. -/
  contradictionType : ViolationType
  deriving Repr

/-- An entailment relation: a function that, given two beliefs,
    determines whether the first entails the second. -/
def EntailmentRelation := Belief → Belief → Prop

/-- A belief set is epistemically closed under a given entailment
    relation if for every belief φ in the set and every ψ such
    that φ entails ψ, ψ is also in the set. -/
def EpistemicallyClosed (entails : EntailmentRelation) (beliefs : List Belief) : Prop :=
  ∀ (φ ψ : Belief), φ ∈ beliefs → entails φ ψ → ψ ∈ beliefs

/-- Negation of an action with respect to a belief: the action
    is inconsistent with the belief being true. -/
def ActionContradictsbelief (_action : Action) (_belief : Belief) : Prop :=
  True  -- In the formal model, this is an oracle/parameter.
          -- The Python detector provides the empirical instantiation.

/-- A reasoning trace is epistemically closed if the belief set
    extracted from all steps is closed, and no action contradicts
    any entailed belief. -/
def TraceEpistemicallyClosed
    (entails : EntailmentRelation)
    (extractBeliefs : AgentStep → List Belief)
    (actionContradicts : Action → Belief → Prop)
    (steps : List AgentStep) : Prop :=
  let allBeliefs := steps.flatMap extractBeliefs
  EpistemicallyClosed entails allBeliefs ∧
  ∀ (s : AgentStep), s ∈ steps →
    ∀ (ψ : Belief), ψ ∈ allBeliefs →
      ¬(actionContradicts s.action ψ)

/-- Closure score: ratio of violations to steps, bounded [0, 1]. -/
def ClosureScore (violations steps : Nat) : Float :=
  if steps == 0 then 0.0
  else min 1.0 (violations.toFloat / steps.toFloat)

/-- Core theorem: if a closure violation exists, then the belief set
    containing the antecedent and entailed belief is not epistemically
    closed (under any entailment relation that validates the violation). -/
theorem violation_implies_incoherence
    (v : ClosureViolation)
    (entails : EntailmentRelation)
    (h_entails : entails v.antecedent v.entailed)
    (h_not_member : ¬(v.entailed ∈ [v.antecedent])) :
    ¬EpistemicallyClosed entails [v.antecedent] := by
  intro h_closed
  have := h_closed v.antecedent v.entailed (List.mem_cons_self _ _) h_entails
  exact h_not_member this

/-- Corollary: a violation witness provides a concrete counterexample
    to closure of any belief set containing only the antecedent. -/
theorem violation_witness_breaks_closure
    (v : ClosureViolation)
    (entails : EntailmentRelation)
    (h_entails : entails v.antecedent v.entailed)
    (h_distinct : v.antecedent.content ≠ v.entailed.content) :
    ¬EpistemicallyClosed entails [v.antecedent] := by
  apply violation_implies_incoherence v entails h_entails
  intro h_mem
  simp [List.mem_cons, List.mem_nil_iff] at h_mem
  exact h_distinct (congrArg Belief.content h_mem.symm)
