/-
  ClosureGuard: Example Traces
  3 epistemically coherent + 3 epistemically incoherent traces
-/

import ClosureViolation

open ClosureViolation

/-! ## Coherent Traces (no violations) -/

/-- Coherent example 1: Math reasoning.
    Agent states "n is even", concludes "n is divisible by 2",
    then correctly divides n by 2. Beliefs and actions align. -/
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

/-- Coherent example 2: Web agent navigation.
    Agent identifies a login page, enters credentials,
    and proceeds to the authenticated dashboard. -/
def coherentTrace2 : List AgentStep := [
  { text := "I see a login page with username and password fields.",
    action := { description := "Type username into the username field." },
    stepIndex := 1 },
  { text := "Username entered. Now I need to enter the password.",
    action := { description := "Type password into the password field." },
    stepIndex := 2 },
  { text := "Credentials entered. I'll submit the form to authenticate.",
    action := { description := "Click the login button." },
    stepIndex := 3 }
]

/-- Coherent example 3: Scientific reasoning.
    Agent identifies a substance as an acid, correctly predicts
    it will lower pH, and tests accordingly. -/
def coherentTrace3 : List AgentStep := [
  { text := "The substance has a pH of 3.2, which means it is acidic.",
    action := { description := "Record substance as acidic." },
    stepIndex := 1 },
  { text := "Acidic substances turn litmus paper red.",
    action := { description := "Apply litmus paper test." },
    stepIndex := 2 },
  { text := "As expected, the litmus paper turned red, confirming acidity.",
    action := { description := "Confirm acidic classification." },
    stepIndex := 3 }
]

/-! ## Incoherent Traces (at least one violation each) -/

/-- Incoherent example 1: ModusPonensViolation.
    Agent states the API returns JSON, states JSON must be parsed,
    but then treats the response as plain text.
    Violation: K(response is JSON) ∧ K(JSON → must parse) → acts as ¬(must parse). -/
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

def violation1 : ClosureViolation := {
  antecedent := { content := "The API endpoint returns JSON." },
  entailed := { content := "The response must be parsed as JSON to extract fields." },
  step := (incoherentTrace1.get! 2),
  contradictionType := ViolationType.ModusPonensViolation
}

/-- Incoherent example 2: BeliefRevisionFailure.
    Agent learns the file was deleted, but continues to
    read from it without acknowledging the deletion. -/
def incoherentTrace2 : List AgentStep := [
  { text := "I'll read the configuration from config.yaml.",
    action := { description := "Open config.yaml for reading." },
    stepIndex := 1 },
  { text := "The system reports config.yaml was deleted in the last deployment.",
    action := { description := "Acknowledge file deletion." },
    stepIndex := 2 },
  { text := "Now let me parse the database URL from config.yaml.",
    action := { description := "Read database_url field from config.yaml." },
    stepIndex := 3 }
]

def violation2 : ClosureViolation := {
  antecedent := { content := "config.yaml was deleted in the last deployment." },
  entailed := { content := "config.yaml cannot be read because it no longer exists." },
  step := (incoherentTrace2.get! 2),
  contradictionType := ViolationType.BeliefRevisionFailure
}

/-- Incoherent example 3: TemporalCoherenceViolation.
    Agent notes the server is down at time T, then at the same
    logical time tries to query it without acknowledging any recovery. -/
def incoherentTrace3 : List AgentStep := [
  { text := "Health check at 14:00 shows the database server is unreachable.",
    action := { description := "Log server as unreachable." },
    stepIndex := 1 },
  { text := "I need to fetch user records to complete this task.",
    action := { description := "Query the database server for user records." },
    stepIndex := 2 },
  { text := "Let me process the query results.",
    action := { description := "Iterate over returned user records." },
    stepIndex := 3 }
]

def violation3 : ClosureViolation := {
  antecedent := { content := "The database server is unreachable at 14:00." },
  entailed := { content := "Queries to the database server will fail." },
  step := (incoherentTrace3.get! 1),
  contradictionType := ViolationType.TemporalCoherenceViolation
}
