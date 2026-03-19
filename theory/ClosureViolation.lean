/-
  ClosureGuard: Formal Definitions for Epistemic Closure Violations
  in LLM Agent Reasoning Traces

  This formalization has two layers:

  LAYER 1 — Kripke semantics for epistemic logic (S5-style).
  We define possible worlds, accessibility relations, epistemic formulas
  with a knowledge operator K, and prove Hintikka's closure axiom:
    K(P) ∧ K(P → Q) → K(Q)
  as a theorem from the semantics (not an axiom).

  LAYER 2 — Trace-level violation detection structures.
  We define the data types used by the Python detector: belief, action,
  agent step, violation type taxonomy, and scoring. These are the
  "empirical interface" — they map formal concepts to observable
  properties of LLM reasoning traces.

  The connection: Layer 1 establishes that closure is a *necessary*
  property of any rational epistemic state. Layer 2 provides the
  vocabulary for detecting *empirical* violations of that property
  in actual agent outputs.

  Philosophical grounding:
  - Hintikka (1962): K(P) ∧ K(P→Q) → K(Q)
  - Brandom: inferential commitments from assertions persist as
    structural obligations in discourse, regardless of internal state.
  - Kripke (1963): Semantical analysis of modal logic.
-/

-- ═══════════════════════════════════════════════════════════════════
-- LAYER 1: KRIPKE SEMANTICS FOR EPISTEMIC LOGIC
-- ═══════════════════════════════════════════════════════════════════

/-- A Kripke frame: a type of possible worlds with an accessibility
    relation R. In epistemic logic, wRw' means "world w' is compatible
    with what the agent knows at world w." -/
structure KripkeFrame where
  World : Type
  R : World → World → Prop

/-- Epistemic formulas: propositional logic extended with a
    knowledge operator K. This is the language of single-agent
    epistemic logic (system K, or S5 with additional axioms). -/
inductive EpistemicFormula where
  /-- Atomic proposition, identified by name. -/
  | atom : String → EpistemicFormula
  /-- Negation: ¬φ -/
  | neg : EpistemicFormula → EpistemicFormula
  /-- Conjunction: φ ∧ ψ -/
  | conj : EpistemicFormula → EpistemicFormula → EpistemicFormula
  /-- Material implication: φ → ψ -/
  | impl : EpistemicFormula → EpistemicFormula → EpistemicFormula
  /-- Knowledge operator: Kφ ("the agent knows φ") -/
  | know : EpistemicFormula → EpistemicFormula
  deriving Repr, Inhabited

/-- A Kripke model: a frame plus a valuation function that assigns
    truth values to atomic propositions at each world. -/
structure KripkeModel (F : KripkeFrame) where
  val : F.World → String → Prop

/-- Satisfaction relation: M, w ⊨ φ.
    Defined recursively on the structure of formulas.

    The critical clause is `know`: M, w ⊨ Kφ iff for all worlds w'
    accessible from w, M, w' ⊨ φ. This is the standard Kripke
    semantics for knowledge — the agent knows φ at w iff φ holds
    in every world the agent considers possible. -/
def satisfies (F : KripkeFrame) (M : KripkeModel F) :
    F.World → EpistemicFormula → Prop
  | w, .atom p     => M.val w p
  | w, .neg φ      => ¬satisfies F M w φ
  | w, .conj φ ψ   => satisfies F M w φ ∧ satisfies F M w ψ
  | w, .impl φ ψ   => satisfies F M w φ → satisfies F M w ψ
  | w, .know φ     => ∀ (w' : F.World), F.R w w' → satisfies F M w' φ

-- ─── CORE THEOREM: EPISTEMIC CLOSURE (AXIOM K) ──────────────────
--
-- This is Hintikka's principle, proven from the Kripke semantics:
-- If the agent knows P, and knows that P implies Q, then the agent
-- knows Q. This is NOT assumed as an axiom — it follows from the
-- definition of `satisfies` for the `know` operator.
--
-- This is the formal anchor for ClosureGuard: any violation of this
-- property in an agent's trace constitutes epistemic incoherence.

/-- **Axiom K (Distribution)**: K(P) ∧ K(P → Q) → K(Q).
    Knowledge is closed under known implication. -/
theorem epistemic_closure
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P Q : EpistemicFormula)
    (hKP : satisfies F M w (.know P))
    (hKPQ : satisfies F M w (.know (.impl P Q))) :
    satisfies F M w (.know Q) := by
  intro w' hw'
  have hP : satisfies F M w' P := hKP w' hw'
  have hPQ : satisfies F M w' P → satisfies F M w' Q := hKPQ w' hw'
  exact hPQ hP

/-- **Axiom T (Factivity)**: If the accessibility relation is reflexive,
    then K(P) → P. Knowledge implies truth.
    This requires reflexivity: the actual world is among those the
    agent considers possible. -/
theorem knowledge_is_factive
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P : EpistemicFormula)
    (h_refl : F.R w w)
    (hKP : satisfies F M w (.know P)) :
    satisfies F M w P :=
  hKP w h_refl

/-- If the agent knows P, and knows P → Q, and the frame is reflexive
    at the actual world, then Q actually holds at the actual world.
    This combines Axiom K and Axiom T: the agent's knowledge
    commitments have consequences for the actual world. -/
theorem known_consequence_holds
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P Q : EpistemicFormula)
    (h_refl : F.R w w)
    (hKP : satisfies F M w (.know P))
    (hKPQ : satisfies F M w (.know (.impl P Q))) :
    satisfies F M w Q := by
  have hKQ := epistemic_closure F M w P Q hKP hKPQ
  exact knowledge_is_factive F M w Q h_refl hKQ

/-- **Positive Introspection (Axiom 4)**: If accessibility is transitive,
    then K(P) → K(K(P)). The agent knows what it knows. -/
theorem positive_introspection
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P : EpistemicFormula)
    (h_trans : ∀ (a b c : F.World), F.R a b → F.R b c → F.R a c)
    (hKP : satisfies F M w (.know P)) :
    satisfies F M w (.know (.know P)) := by
  intro w' hw'
  intro w'' hw''
  exact hKP w'' (h_trans w w' w'' hw' hw'')

-- ═══════════════════════════════════════════════════════════════════
-- CONNECTION: CLOSURE VIOLATION IN KRIPKE SEMANTICS
-- ═══════════════════════════════════════════════════════════════════

/-- An agent violates epistemic closure when:
    1. It knows P (has committed to P in its trace)
    2. It knows P → Q (the entailment is part of its knowledge)
    3. Its action is inconsistent with Q

    The `actionContradictsQ` parameter represents the empirical
    observation that the agent's action presupposes ¬Q. This is
    the bridge between the formal model and the Python detector. -/
structure EpistemicViolation (F : KripkeFrame) where
  M : KripkeModel F
  w : F.World
  P : EpistemicFormula
  Q : EpistemicFormula
  h_knows_P : satisfies F M w (.know P)
  h_knows_PQ : satisfies F M w (.know (.impl P Q))
  actionContradictsQ : Prop
  h_action_contradicts : actionContradictsQ

/-- Any epistemic violation witnesses that Q actually holds (assuming
    reflexivity), so the agent's action contradicts a fact entailed
    by its own knowledge. This is the key soundness result:
    if you detect a violation, the agent acted against a known truth. -/
theorem violation_contradicts_known_truth
    (F : KripkeFrame) (v : EpistemicViolation F)
    (h_refl : F.R v.w v.w) :
    satisfies F v.M v.w v.Q ∧ v.actionContradictsQ :=
  ⟨known_consequence_holds F v.M v.w v.P v.Q h_refl v.h_knows_P v.h_knows_PQ,
   v.h_action_contradicts⟩

-- ═══════════════════════════════════════════════════════════════════
-- LAYER 2: TRACE-LEVEL DETECTION STRUCTURES
-- ═══════════════════════════════════════════════════════════════════
--
-- These types are the "empirical interface" — they correspond
-- directly to the Python data structures in the detector pipeline.
-- The formal guarantees from Layer 1 justify why detecting these
-- patterns constitutes finding genuine epistemic incoherence.

/-- A proposition the agent has committed to in its trace.
    In the Kripke model, this corresponds to an atom p such that
    K(atom p) holds at the actual world. -/
structure Belief where
  content : String
  deriving Repr, BEq, Inhabited

/-- An action the agent performed. -/
structure Action where
  description : String
  deriving Repr, BEq, Inhabited

/-- A single step in a reasoning trace. -/
structure AgentStep where
  text : String
  action : Action
  stepIndex : Nat
  deriving Repr, Inhabited

/-- A reasoning trace is a list of agent steps. -/
def ReasoningTrace := List AgentStep

/-- Taxonomy of epistemic closure violation types.
    Each maps to a specific pattern of failure in the Kripke model:

    - ModusPonensViolation: K(P), K(P→Q), action presupposes ¬Q
    - BeliefRevisionFailure: K(P) at step t, evidence for ¬P at step t',
      but agent still acts on P at step t'' > t'
    - ModalScopeError: K(◇P) confused with K(□P), i.e., "possible"
      treated as "necessary" in downstream action
    - TemporalCoherenceViolation: K(P-at-t₁), action at t₁ presupposes ¬P
    - ReferentialOpacityFailure: K(a = b), but agent treats Ka(φ) and
      Kb(φ) as independent — failure of substitutivity
-/
inductive ViolationType where
  | ModusPonensViolation
  | BeliefRevisionFailure
  | ModalScopeError
  | TemporalCoherenceViolation
  | ReferentialOpacityFailure
  deriving Repr, BEq, Inhabited

/-- A detected closure violation in a reasoning trace. -/
structure ClosureViolation where
  antecedent : Belief
  entailed : Belief
  step : AgentStep
  contradictionType : ViolationType
  deriving Repr

/-- Closure score: ratio of violations to steps, bounded [0, 1]. -/
def ClosureScore (violations steps : Nat) : Float :=
  if steps == 0 then 0.0
  else min 1.0 (violations.toFloat / steps.toFloat)

-- ═══════════════════════════════════════════════════════════════════
-- DEDUCTIVE CLOSURE (for list-based belief sets)
-- ═══════════════════════════════════════════════════════════════════

/-- An entailment relation over beliefs (empirical interface). -/
def EntailmentRelation := Belief → Belief → Prop

/-- A belief set (list) is deductively closed under an entailment
    relation: for every φ in the set and ψ entailed by φ, ψ is
    also in the set.

    Note: this is *deductive* closure over a belief list, which is
    a weaker notion than epistemic closure in the Kripke sense.
    The Kripke theorems above establish *why* this property should
    hold; this definition provides the operational check. -/
def DeductivelyClosed (entails : EntailmentRelation) (beliefs : List Belief) : Prop :=
  ∀ (φ ψ : Belief), φ ∈ beliefs → entails φ ψ → ψ ∈ beliefs

/-- If an entailment maps to a belief outside the set, the set is
    not deductively closed. Used by the Python detector to witness
    violations: finding any such pair is sufficient. -/
theorem entailment_outside_set_breaks_closure
    (entails : EntailmentRelation)
    (beliefs : List Belief) (φ ψ : Belief)
    (h_in : φ ∈ beliefs)
    (h_entails : entails φ ψ)
    (h_not_in : ψ ∉ beliefs) :
    ¬DeductivelyClosed entails beliefs := by
  intro h_closed
  exact h_not_in (h_closed φ ψ h_in h_entails)
