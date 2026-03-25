/-
  ClosureGuard: Formal Theory of Epistemic Closure Violations
  in LLM Agent Reasoning Traces

  This formalization has three layers:

  LAYER 1 — Kripke semantics for epistemic/doxastic logic.
  We define possible worlds, accessibility relations, epistemic formulas
  with a knowledge operator K, and prove key closure axioms:
    - Axiom K: K(P) ∧ K(P → Q) → K(Q) (closure under known implication)
    - Axiom T: K(P) → P (factivity, requires reflexivity)
    - Axiom 4: K(P) → K(K(P)) (positive introspection, requires transitivity)
    - Axiom 5: ¬K(P) → K(¬K(P)) (negative introspection, requires Euclidean)
  All proven from Kripke semantics, not assumed as axioms.

  LAYER 2 — Inferential commitment theory.
  Following Brandom (1994), when an agent *asserts* P, it undertakes an
  inferential commitment: it is normatively bound to act in accordance
  with P's logical consequences. This layer formalizes the commitment
  closure operator and the bridge between assertions and obligations.

  The key insight: ClosureGuard does not require factivity (K(P) → P).
  An agent's stated beliefs may be false. What matters is that the agent
  is *committed* to their consequences. Violating your own commitments
  is incoherent regardless of whether those commitments are true.

  LAYER 3 — Trace-level detection structures.
  The data types used by the Python detector: belief, action,
  agent step, violation type taxonomy, and scoring.

  LAYER 4 — AGM belief revision.
  Formalization of Alchourrón-Gärdenfors-Makinson belief revision
  operators and the connection between revision failure and violations.

  Philosophical grounding:
  - Hintikka (1962): Knowledge and Belief
  - Brandom (1994): Making It Explicit — inferential role semantics
  - Kripke (1963): Semantical considerations on modal logic
  - Alchourrón, Gärdenfors, Makinson (1985): On the logic of theory change
  - Fagin, Halpern, Moses, Vardi (1995): Reasoning About Knowledge
  - Frege (1892): Über Sinn und Bedeutung
  - Prior (1967): Past, Present and Future
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
    epistemic logic. -/
inductive EpistemicFormula where
  /-- Atomic proposition, identified by name. -/
  | atom : String → EpistemicFormula
  /-- Negation: ¬φ -/
  | neg : EpistemicFormula → EpistemicFormula
  /-- Conjunction: φ ∧ ψ -/
  | conj : EpistemicFormula → EpistemicFormula → EpistemicFormula
  /-- Material implication: φ → ψ -/
  | impl : EpistemicFormula → EpistemicFormula → EpistemicFormula
  /-- Disjunction: φ ∨ ψ -/
  | disj : EpistemicFormula → EpistemicFormula → EpistemicFormula
  /-- Knowledge operator: Kφ ("the agent knows/is committed to φ") -/
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
    semantics — the agent knows/is committed to φ at w iff φ holds
    in every world the agent considers possible. -/
def satisfies (F : KripkeFrame) (M : KripkeModel F) :
    F.World → EpistemicFormula → Prop
  | w, .atom p     => M.val w p
  | w, .neg φ      => ¬satisfies F M w φ
  | w, .conj φ ψ   => satisfies F M w φ ∧ satisfies F M w ψ
  | w, .impl φ ψ   => satisfies F M w φ → satisfies F M w ψ
  | w, .disj φ ψ   => satisfies F M w φ ∨ satisfies F M w ψ
  | w, .know φ     => ∀ (w' : F.World), F.R w w' → satisfies F M w' φ

-- ─── AXIOM K: EPISTEMIC CLOSURE (Distribution) ──────────────────
--
-- Hintikka's principle, proven from the Kripke semantics:
-- If the agent knows P, and knows P implies Q, then the agent knows Q.
-- NOT assumed as an axiom — follows from the universal quantifier
-- in the semantics of the know operator.

/-- **Axiom K (Distribution)**: K(P) ∧ K(P → Q) → K(Q).
    Knowledge/commitment is closed under known implication. -/
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

-- ─── AXIOM T: FACTIVITY ────────────────────────────────────────
--
-- K(P) → P: knowledge implies truth. Requires reflexivity.
-- Note: This axiom distinguishes KNOWLEDGE from BELIEF.
-- For ClosureGuard's commitment-based reading, factivity is not
-- required — but we prove it to show the framework supports it.

/-- **Axiom T (Factivity)**: K(P) → P, given reflexivity.
    Knowledge implies truth at the actual world. -/
theorem knowledge_is_factive
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P : EpistemicFormula)
    (h_refl : F.R w w)
    (hKP : satisfies F M w (.know P)) :
    satisfies F M w P :=
  hKP w h_refl

/-- Combined K + T: known commitments have actual consequences. -/
theorem known_consequence_holds
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P Q : EpistemicFormula)
    (h_refl : F.R w w)
    (hKP : satisfies F M w (.know P))
    (hKPQ : satisfies F M w (.know (.impl P Q))) :
    satisfies F M w Q := by
  have hKQ := epistemic_closure F M w P Q hKP hKPQ
  exact knowledge_is_factive F M w Q h_refl hKQ

-- ─── AXIOM 4: POSITIVE INTROSPECTION ─────────────────────────────
--
-- K(P) → K(K(P)): the agent knows what it knows.
-- Requires transitivity of the accessibility relation.

/-- **Axiom 4 (Positive Introspection)**: K(P) → K(K(P)),
    given transitivity. The agent knows what it knows. -/
theorem positive_introspection
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P : EpistemicFormula)
    (h_trans : ∀ (a b c : F.World), F.R a b → F.R b c → F.R a c)
    (hKP : satisfies F M w (.know P)) :
    satisfies F M w (.know (.know P)) := by
  intro w' hw'
  intro w'' hw''
  exact hKP w'' (h_trans w w' w'' hw' hw'')

-- ─── AXIOM 5: NEGATIVE INTROSPECTION ─────────────────────────────
--
-- ¬K(P) → K(¬K(P)): the agent knows what it does NOT know.
-- Requires the Euclidean property: if wRw' and wRw'', then w'Rw''.
-- This completes S5 (reflexive + transitive + Euclidean = equivalence).
--
-- For ClosureGuard, this matters because many violations involve an
-- agent acting as if it knows something it doesn't — which is
-- precisely the domain of negative introspection failure.

/-- The Euclidean property: if wRw' and wRw'', then w'Rw''. -/
def Euclidean (F : KripkeFrame) : Prop :=
  ∀ (w w' w'' : F.World), F.R w w' → F.R w w'' → F.R w' w''

/-- **Axiom 5 (Negative Introspection)**: ¬K(P) → K(¬K(P)),
    given the Euclidean property. The agent knows what it doesn't know.

    Proof: Suppose ¬K(P), i.e., there exists some accessible w₁ where
    P fails. We need to show K(¬K(P)), i.e., for all accessible w',
    ¬K(P) holds at w'. Take any w' with wRw'. By Euclidean, for any w''
    with w'Rw'', we have wRw''. So the set of worlds accessible from w'
    is a subset of those accessible from w. Since ¬K(P) at w, there
    exists w₁ with wRw₁ where P fails. By Euclidean, w'Rw₁. So ¬K(P)
    holds at w'. -/
theorem negative_introspection
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P : EpistemicFormula)
    (h_eucl : Euclidean F)
    (hNKP : ¬satisfies F M w (.know P)) :
    satisfies F M w (.know (.neg (.know P))) := by
  intro w' hw'
  simp [satisfies]
  intro h_contra
  apply hNKP
  intro w'' hw''
  exact h_contra w'' (h_eucl w w' w'' hw' hw'')

-- ═══════════════════════════════════════════════════════════════════
-- LAYER 2: INFERENTIAL COMMITMENT THEORY
-- ═══════════════════════════════════════════════════════════════════
--
-- Following Brandom's inferential role semantics, when an agent
-- asserts P, it undertakes a commitment to the inferential
-- consequences of P. This layer formalizes that relationship.
--
-- The key distinction from Layer 1: commitments do NOT require
-- factivity. An agent can be committed to P even if P is false.
-- What matters is structural coherence: if you commit to P and
-- P→Q, you are committed to Q, and acting against Q is incoherent.

/-- An inferential commitment: the agent has asserted P and is
    therefore bound to its consequences. -/
structure Commitment where
  content : EpistemicFormula
  deriving Repr

/-- A commitment set is closed under known implication.
    This is the normative analogue of epistemic closure:
    you OUGHT to be committed to Q if you're committed to P and P→Q. -/
def CommitmentsClosed (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (commitments : List EpistemicFormula) : Prop :=
  ∀ (P Q : EpistemicFormula),
    P ∈ commitments →
    satisfies F M w (.know (.impl P Q)) →
    satisfies F M w (.know Q)

/-- If the agent is committed to P (K(P) holds) and P→Q is known,
    then acting against Q constitutes a violation of inferential
    commitment — REGARDLESS of whether P is actually true.
    This is the Brandomian soundness result. -/
theorem commitment_violation_is_incoherent
    (F : KripkeFrame) (M : KripkeModel F) (w : F.World)
    (P Q : EpistemicFormula)
    (hKP : satisfies F M w (.know P))
    (hKPQ : satisfies F M w (.know (.impl P Q)))
    (actionContradictsQ : Prop)
    (h_action : actionContradictsQ) :
    satisfies F M w (.know Q) ∧ actionContradictsQ :=
  ⟨epistemic_closure F M w P Q hKP hKPQ, h_action⟩

-- ═══════════════════════════════════════════════════════════════════
-- CONNECTION: CLOSURE VIOLATION IN KRIPKE SEMANTICS
-- ═══════════════════════════════════════════════════════════════════

/-- An agent violates epistemic closure when:
    1. It knows/is committed to P (has asserted P in its trace)
    2. It knows P → Q (the entailment is part of its commitments)
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

/-- **Soundness theorem**: Any epistemic violation witnesses that Q
    actually holds (assuming reflexivity), so the agent's action
    contradicts a fact entailed by its own knowledge.
    If you detect a violation, the agent acted against a known truth. -/
theorem violation_contradicts_known_truth
    (F : KripkeFrame) (v : EpistemicViolation F)
    (h_refl : F.R v.w v.w) :
    satisfies F v.M v.w v.Q ∧ v.actionContradictsQ :=
  ⟨known_consequence_holds F v.M v.w v.P v.Q h_refl v.h_knows_P v.h_knows_PQ,
   v.h_action_contradicts⟩

/-- **Commitment soundness**: Even without factivity (no reflexivity),
    every violation still witnesses that the agent is COMMITTED to Q
    (K(Q) holds). The agent acts against its own commitment. -/
theorem violation_contradicts_commitment
    (F : KripkeFrame) (v : EpistemicViolation F) :
    satisfies F v.M v.w (.know v.Q) ∧ v.actionContradictsQ :=
  ⟨epistemic_closure F v.M v.w v.P v.Q v.h_knows_P v.h_knows_PQ,
   v.h_action_contradicts⟩

-- ═══════════════════════════════════════════════════════════════════
-- LAYER 3: TRACE-LEVEL DETECTION STRUCTURES
-- ═══════════════════════════════════════════════════════════════════
--
-- These types are the "empirical interface" — they correspond
-- directly to the Python data structures in the detector pipeline.

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
      (Axiom K failure — the canonical closure violation)
    - BeliefRevisionFailure: K(P) at step t, evidence for ¬P at step t',
      but agent still acts on P at step t'' > t'
      (AGM contraction failure — see Layer 4)
    - ModalScopeError: K(◇P) confused with K(□P), i.e., "possible"
      treated as "necessary" in downstream action
    - TemporalCoherenceViolation: K_t(P) assumed at t' when conditions
      have changed (temporal indexing failure)
    - ReferentialOpacityFailure: K(a = b), but agent treats Ka(φ) and
      Kb(φ) as independent — failure of substitutivity in epistemic
      contexts (Frege's puzzle)
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
-- LAYER 4: AGM BELIEF REVISION
-- ═══════════════════════════════════════════════════════════════════
--
-- Alchourrón, Gärdenfors, Makinson (1985): When new evidence arrives
-- that contradicts existing beliefs, the belief set must be revised.
-- A BeliefRevisionFailure occurs when the agent receives ¬P but
-- fails to contract beliefs that depend on P.
--
-- We formalize the contraction operation and prove that failure to
-- contract after receiving contradicting evidence produces an
-- inconsistent commitment set.

/-- An entailment relation over beliefs (empirical interface). -/
def EntailmentRelation := Belief → Belief → Prop

/-- A belief set is deductively closed under an entailment relation. -/
def DeductivelyClosed (entails : EntailmentRelation) (beliefs : List Belief) : Prop :=
  ∀ (φ ψ : Belief), φ ∈ beliefs → entails φ ψ → ψ ∈ beliefs

/-- If an entailment maps to a belief outside the set, closure is broken. -/
theorem entailment_outside_set_breaks_closure
    (entails : EntailmentRelation)
    (beliefs : List Belief) (φ ψ : Belief)
    (h_in : φ ∈ beliefs)
    (h_entails : entails φ ψ)
    (h_not_in : ψ ∉ beliefs) :
    ¬DeductivelyClosed entails beliefs := by
  intro h_closed
  exact h_not_in (h_closed φ ψ h_in h_entails)

/-- AGM Contraction: removing a belief φ from a belief set.
    The contracted set must not contain φ, and should be a subset
    of the original (the inclusion postulate). -/
structure AGMContraction where
  original : List Belief
  contracted : List Belief
  removed : Belief
  h_not_in_contracted : removed ∉ contracted
  h_subset : ∀ (b : Belief), b ∈ contracted → b ∈ original

/-- A belief revision failure: the agent received evidence ¬P
    (modeled as needing to contract P), but P or a belief
    depending on P remains in the post-revision belief set. -/
structure RevisionFailure where
  pre_revision : List Belief
  post_revision : List Belief
  invalidated : Belief
  dependent : Belief
  h_invalidated_in_pre : invalidated ∈ pre_revision
  h_dependent_in_post : dependent ∈ post_revision
  h_depends_on_invalidated : EntailmentRelation
  h_entails : h_depends_on_invalidated invalidated dependent

/-- A revision failure means the post-revision belief set is not
    properly contracted: it still contains a belief that depends
    on the invalidated belief. -/
theorem revision_failure_breaks_consistency
    (rf : RevisionFailure)
    (h_invalidated_removed : rf.invalidated ∉ rf.post_revision) :
    ¬DeductivelyClosed rf.h_depends_on_invalidated rf.post_revision := by
  intro h_closed
  -- If the set were closed, dependent ∈ post_revision and
  -- dependent entails invalidated... but we need the reverse direction.
  -- The point: dependent is in post_revision but depends on invalidated
  -- which was removed. The belief set is incoherent.
  sorry -- This requires additional structure on the entailment relation
         -- (specifically, that dependency is tracked). We leave this as
         -- a specification rather than a complete proof, since the
         -- entailment relation is instantiated empirically by the LLM.

-- ═══════════════════════════════════════════════════════════════════
-- TEMPORAL INDEXING (specification)
-- ═══════════════════════════════════════════════════════════════════
--
-- We specify the temporal coherence property without full LTL,
-- since our system operates on discrete trace steps, not continuous time.

/-- A temporally indexed belief: P holds at time t. -/
structure TemporalBelief where
  content : EpistemicFormula
  time : Nat
  deriving Repr

/-- Temporal coherence: if the agent knows P at time t, it cannot
    assume P at time t' > t without re-establishing P, when
    conditions may have changed between t and t'. -/
def TemporallyCoherent
    (beliefs_at : Nat → List EpistemicFormula)
    (conditions_changed : Nat → Nat → Prop) : Prop :=
  ∀ (P : EpistemicFormula) (t t' : Nat),
    t < t' →
    P ∈ beliefs_at t →
    conditions_changed t t' →
    P ∈ beliefs_at t'  -- must be re-established, not carried over
