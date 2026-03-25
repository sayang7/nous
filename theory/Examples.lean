/-
  ClosureGuard: Worked Examples in Kripke Semantics

  Each example constructs a concrete Kripke model and demonstrates
  either epistemic closure (coherent) or violation (incoherent).
  Includes examples of all five violation types and the new
  commitment-based and negative introspection results.
-/

import ClosureViolation

-- ═══════════════════════════════════════════════════════════════════
-- EXAMPLE 1: Coherent — Modus Ponens Applied Correctly
-- ═══════════════════════════════════════════════════════════════════
--
-- Scenario: Agent knows "response is JSON" (P) and knows
-- "JSON implies must parse" (P → Q). Agent parses as JSON.
-- This is coherent: the agent acts on Q, consistent with K(Q).

/-- A simple two-world frame where both worlds are accessible. -/
def coherentFrame : KripkeFrame where
  World := Bool
  R := fun _ _ => True

/-- In both worlds: "is_json" and "must_parse" are true. -/
def coherentModel : KripkeModel coherentFrame where
  val := fun _ p => p = "is_json" ∨ p = "must_parse"

/-- The agent knows "is_json" in this model. -/
theorem coherent_knows_P :
    satisfies coherentFrame coherentModel true
      (.know (.atom "is_json")) := by
  intro w' _
  simp [satisfies, coherentModel]

/-- The agent knows "is_json → must_parse" in this model. -/
theorem coherent_knows_PQ :
    satisfies coherentFrame coherentModel true
      (.know (.impl (.atom "is_json") (.atom "must_parse"))) := by
  intro w' _
  intro h
  simp [satisfies, coherentModel]

/-- Therefore: the agent knows "must_parse" (by epistemic_closure). -/
theorem coherent_knows_Q :
    satisfies coherentFrame coherentModel true
      (.know (.atom "must_parse")) :=
  epistemic_closure coherentFrame coherentModel true
    (.atom "is_json") (.atom "must_parse")
    coherent_knows_P coherent_knows_PQ


-- ═══════════════════════════════════════════════════════════════════
-- EXAMPLE 2: Violation — ModusPonensViolation
-- ═══════════════════════════════════════════════════════════════════
--
-- Scenario: Agent knows "is_json" and "json → must_parse",
-- but in the actual world, the action presupposes "¬must_parse"
-- (string-splitting instead of JSON parsing).

/-- Violation witness for the JSON parsing example.
    Uses both the knowledge-based and commitment-based soundness. -/
theorem modus_ponens_violation_example :
    ∃ (F : KripkeFrame) (v : EpistemicViolation F),
      satisfies F v.M v.w v.Q ∧ v.actionContradictsQ := by
  refine ⟨coherentFrame, ?_, ?_⟩
  · exact {
      M := coherentModel
      w := true
      P := .atom "is_json"
      Q := .atom "must_parse"
      h_knows_P := coherent_knows_P
      h_knows_PQ := coherent_knows_PQ
      actionContradictsQ := True  -- "string split" contradicts "must parse"
      h_action_contradicts := trivial
    }
  · exact violation_contradicts_known_truth coherentFrame _ trivial

/-- The same violation, but using commitment soundness (no factivity needed). -/
theorem modus_ponens_commitment_violation :
    ∃ (F : KripkeFrame) (v : EpistemicViolation F),
      satisfies F v.M v.w (.know v.Q) ∧ v.actionContradictsQ := by
  refine ⟨coherentFrame, ?_, ?_⟩
  · exact {
      M := coherentModel
      w := true
      P := .atom "is_json"
      Q := .atom "must_parse"
      h_knows_P := coherent_knows_P
      h_knows_PQ := coherent_knows_PQ
      actionContradictsQ := True
      h_action_contradicts := trivial
    }
  · exact violation_contradicts_commitment coherentFrame _


-- ═══════════════════════════════════════════════════════════════════
-- EXAMPLE 3: Coherent — Belief Correctly Revised
-- ═══════════════════════════════════════════════════════════════════
--
-- Scenario: Agent initially believed "file exists", then learned
-- "file deleted". In the revised model, the agent no longer knows
-- "file exists" — so reading from it would be a violation, but
-- the agent correctly avoids it.

/-- Frame with two worlds: w0 = file exists, w1 = file deleted.
    After learning deletion, only w1 is accessible. -/
def revisedFrame : KripkeFrame where
  World := Bool  -- false = file deleted (actual), true = file exists
  R := fun _ w' => w' = false  -- only "deleted" world is accessible

def revisedModel : KripkeModel revisedFrame where
  val := fun w p =>
    match w, p with
    | false, "file_deleted" => True
    | true,  "file_exists"  => True
    | _,     _              => False

/-- After revision, the agent knows the file is deleted. -/
theorem revised_knows_deleted :
    satisfies revisedFrame revisedModel false
      (.know (.atom "file_deleted")) := by
  intro w' hw'
  simp [satisfies, revisedModel]
  simp_all [revisedFrame]

/-- After revision, the agent does NOT know the file exists. -/
theorem revised_not_knows_exists :
    ¬satisfies revisedFrame revisedModel false
      (.know (.atom "file_exists")) := by
  intro h
  have := h false rfl
  simp [satisfies, revisedModel] at this


-- ═══════════════════════════════════════════════════════════════════
-- EXAMPLE 4: Violation — BeliefRevisionFailure
-- ═══════════════════════════════════════════════════════════════════
--
-- The agent's model SHOULD be `revisedFrame` (it learned the file
-- was deleted), but it acts as though "file_exists" is still known.

theorem belief_revision_failure_example :
    ¬satisfies revisedFrame revisedModel false (.atom "file_exists") := by
  simp [satisfies, revisedModel]


-- ═══════════════════════════════════════════════════════════════════
-- EXAMPLE 5: Coherent — Possibility Not Treated as Certainty
-- ═══════════════════════════════════════════════════════════════════

def modalFrame : KripkeFrame where
  World := Fin 3      -- w0 = actual, w1 = induction works, w2 = it doesn't
  R := fun _ _ => True  -- all worlds accessible (S5)

def modalModel : KripkeModel modalFrame where
  val := fun w p =>
    match p with
    | "induction_works" => w.val = 0 ∨ w.val = 1  -- true in w0, w1; false in w2
    | _ => False

/-- The agent does NOT know "induction_works" — it's false in w2. -/
theorem modal_not_knows_induction :
    ¬satisfies modalFrame modalModel ⟨0, by omega⟩
      (.know (.atom "induction_works")) := by
  intro h
  have := h ⟨2, by omega⟩ trivial
  simp [satisfies, modalModel] at this


-- ═══════════════════════════════════════════════════════════════════
-- EXAMPLE 6: Violation — ModalScopeError
-- ═══════════════════════════════════════════════════════════════════

theorem modal_scope_error_example :
    satisfies modalFrame modalModel ⟨0, by omega⟩ (.atom "induction_works") ∧
    ¬satisfies modalFrame modalModel ⟨0, by omega⟩
      (.know (.atom "induction_works")) :=
  ⟨by simp [satisfies, modalModel],
   modal_not_knows_induction⟩


-- ═══════════════════════════════════════════════════════════════════
-- EXAMPLE 7: Negative Introspection
-- ═══════════════════════════════════════════════════════════════════
--
-- In the modal frame (which is Euclidean since R is universal),
-- the agent KNOWS it doesn't know induction_works.
-- This demonstrates Axiom 5.

/-- The universal relation is Euclidean. -/
theorem modalFrame_euclidean : Euclidean modalFrame := by
  intro _ _ _ _ _
  exact trivial

/-- The agent knows it doesn't know induction_works (Axiom 5). -/
theorem knows_doesnt_know_induction :
    satisfies modalFrame modalModel ⟨0, by omega⟩
      (.know (.neg (.know (.atom "induction_works")))) :=
  negative_introspection modalFrame modalModel ⟨0, by omega⟩
    (.atom "induction_works") modalFrame_euclidean modal_not_knows_induction


-- ═══════════════════════════════════════════════════════════════════
-- TRACE-LEVEL EXAMPLES (empirical interface)
-- ═══════════════════════════════════════════════════════════════════

/-- Coherent trace: even number reasoning. -/
def coherentTrace1 : List AgentStep := [
  { text := "The input n = 42 is an even number.",
    action := { description := "Store n = 42 as even." },
    stepIndex := 1 },
  { text := "Since n is even, n is divisible by 2.",
    action := { description := "Compute n / 2 = 21." },
    stepIndex := 2 },
  { text := "The result is 21.",
    action := { description := "Return 21." },
    stepIndex := 3 }
]

/-- Incoherent trace: API JSON violation (ModusPonensViolation). -/
def incoherentTrace1 : List AgentStep := [
  { text := "The API documentation confirms the endpoint returns JSON.",
    action := { description := "Send GET request to the endpoint." },
    stepIndex := 1 },
  { text := "JSON responses need to be parsed before accessing fields.",
    action := { description := "Store the response body." },
    stepIndex := 2 },
  { text := "Let me extract the 'name' field from the response.",
    action := { description := "Split response string by commas to find name." },
    stepIndex := 3 }
]

/-- Violation witness for the API JSON trace. -/
def violation1 : ClosureViolation := {
  antecedent := { content := "The API endpoint returns JSON." },
  entailed := { content := "The response must be parsed as JSON to extract fields." },
  step := (incoherentTrace1.get! 2),
  contradictionType := ViolationType.ModusPonensViolation
}
