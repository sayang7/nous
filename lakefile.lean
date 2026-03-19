import Lake
open Lake DSL

package ClosureGuard where
  leanOptions := #[
    ⟨`autoImplicit, false⟩
  ]

@[default_target]
lean_lib Theory where
  srcDir := "theory"
  roots := #[`ClosureViolation, `Examples]
