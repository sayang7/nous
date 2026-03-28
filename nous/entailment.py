"""Entailment backends for Nous.

The entailment checker is the pluggable component that determines whether
proposition P entails proposition Q, and whether action A contradicts
proposition P. This is the ONLY component that needs semantic understanding.

Three backends, from heaviest to lightest:
  1. LLMBackend — uses Claude/GPT for entailment (most accurate, costs money)
  2. NLIBackend — uses a local cross-encoder NLI model (free, fast, no API)
  3. EmbeddingBackend — uses sentence embeddings + cosine (fastest, least accurate)

The core algorithm (commitment graph, closure, violation detection) is
the SAME regardless of backend. The backend is a tool, not the system.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EntailmentResult:
    """Result of checking entailment or contradiction."""
    relation: str  # "entailment", "contradiction", "neutral"
    confidence: float  # 0.0 to 1.0
    explanation: str = ""


class EntailmentBackend(ABC):
    """Abstract backend for semantic entailment checking."""

    @abstractmethod
    def check_entailment(self, premise: str, hypothesis: str) -> EntailmentResult:
        """Does premise entail hypothesis?"""
        ...

    @abstractmethod
    def check_contradiction(self, commitment: str, action: str) -> EntailmentResult:
        """Does action contradict commitment?"""
        ...

    def batch_check_contradiction(
        self, commitments: list[str], action: str,
    ) -> list[EntailmentResult]:
        """Check action against multiple commitments. Override for efficiency."""
        return [self.check_contradiction(c, action) for c in commitments]


class NLIBackend(EntailmentBackend):
    """Local NLI model backend using sentence-transformers cross-encoder.

    Requires: pip install sentence-transformers
    Model: cross-encoder/nli-deberta-v3-base (or configurable)

    This is the recommended backend for production use:
    - Free (no API costs)
    - Fast (~10ms per check on GPU, ~50ms on CPU)
    - Deterministic
    - Good accuracy on standard NLI benchmarks (~90% on MNLI)
    """

    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-base"):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            raise ImportError(
                "NLIBackend requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            )
        self._model = CrossEncoder(model_name)
        # DeBERTa NLI labels: 0=contradiction, 1=entailment, 2=neutral
        self._label_map = {0: "contradiction", 1: "entailment", 2: "neutral"}

    def check_entailment(self, premise: str, hypothesis: str) -> EntailmentResult:
        scores = self._model.predict([(premise, hypothesis)])[0]
        label_idx = scores.argmax()
        return EntailmentResult(
            relation=self._label_map[label_idx],
            confidence=float(scores[label_idx]),
        )

    def check_contradiction(self, commitment: str, action: str) -> EntailmentResult:
        # Frame: "Given [commitment], the action [action] is coherent"
        # If this is contradicted, the action violates the commitment
        hypothesis = f"The action '{action}' is consistent with: {commitment}"
        anti_hypothesis = f"The action '{action}' contradicts: {commitment}"

        scores_pos = self._model.predict([(commitment, hypothesis)])[0]
        scores_neg = self._model.predict([(commitment, anti_hypothesis)])[0]

        # Contradiction score = P(entailment of anti_hypothesis)
        contradiction_score = float(scores_neg[1])  # entailment of negation
        entailment_score = float(scores_pos[1])  # entailment of positive

        if contradiction_score > entailment_score and contradiction_score > 0.5:
            return EntailmentResult(
                relation="contradiction",
                confidence=contradiction_score,
            )
        return EntailmentResult(
            relation="neutral",
            confidence=1.0 - contradiction_score,
        )

    def batch_check_contradiction(
        self, commitments: list[str], action: str,
    ) -> list[EntailmentResult]:
        if not commitments:
            return []

        pairs = [(c, f"The action '{action}' contradicts: {c}") for c in commitments]
        all_scores = self._model.predict(pairs)

        results = []
        for scores in all_scores:
            contradiction_score = float(scores[1])
            if contradiction_score > 0.5:
                results.append(EntailmentResult(
                    relation="contradiction",
                    confidence=contradiction_score,
                ))
            else:
                results.append(EntailmentResult(
                    relation="neutral",
                    confidence=1.0 - contradiction_score,
                ))
        return results


class EmbeddingBackend(EntailmentBackend):
    """Embedding-based backend using sentence-transformers.

    Requires: pip install sentence-transformers
    Model: all-MiniLM-L6-v2 (or configurable)

    Fastest backend. Uses cosine similarity to approximate entailment
    and contradiction. Less accurate than NLI but requires no
    cross-encoder inference.

    Entailment: high similarity between premise and hypothesis
    Contradiction: high similarity between premise and negation of hypothesis
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "EmbeddingBackend requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            )
        self._model = SentenceTransformer(model_name)

    def _cosine_sim(self, a, b) -> float:
        import numpy as np
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def check_entailment(self, premise: str, hypothesis: str) -> EntailmentResult:
        embeddings = self._model.encode([premise, hypothesis])
        sim = self._cosine_sim(embeddings[0], embeddings[1])

        if sim > 0.8:
            return EntailmentResult(relation="entailment", confidence=sim)
        elif sim < 0.3:
            return EntailmentResult(relation="contradiction", confidence=1.0 - sim)
        return EntailmentResult(relation="neutral", confidence=0.5)

    def check_contradiction(self, commitment: str, action: str) -> EntailmentResult:
        neg_commitment = f"NOT: {commitment}"
        embeddings = self._model.encode([action, commitment, neg_commitment])

        sim_pos = self._cosine_sim(embeddings[0], embeddings[1])
        sim_neg = self._cosine_sim(embeddings[0], embeddings[2])

        if sim_neg > sim_pos and sim_neg > 0.5:
            return EntailmentResult(
                relation="contradiction",
                confidence=sim_neg,
            )
        return EntailmentResult(relation="neutral", confidence=sim_pos)


class LLMBackend(EntailmentBackend):
    """LLM-based backend using Claude API.

    Most accurate but costs money per call. Use when:
    - You need maximum accuracy on subtle cases
    - You're running eval/benchmarks
    - The trace is short and cost doesn't matter

    The LLM is asked ONLY about entailment/contradiction — it does
    NOT do the reasoning. The reasoning (closure, violation detection,
    classification) is done by the graph algorithm.
    """

    def __init__(self, api_key: Optional[str] = None):
        import anthropic

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("LLMBackend requires ANTHROPIC_API_KEY")
        self._client = anthropic.Anthropic(api_key=self.api_key)
        self._model = os.environ.get("NOUS_MODEL", "claude-sonnet-4-6")

    def check_entailment(self, premise: str, hypothesis: str) -> EntailmentResult:
        import json
        prompt = (
            f'Does the premise entail the hypothesis?\n\n'
            f'Premise: "{premise}"\n'
            f'Hypothesis: "{hypothesis}"\n\n'
            f'Respond with ONLY JSON: '
            f'{{"relation": "entailment"|"contradiction"|"neutral", '
            f'"confidence": 0.0-1.0}}'
        )

        try:
            text_parts = []
            with self._client.messages.stream(
                model=self._model,
                max_tokens=128,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(text)
            return EntailmentResult(
                relation=parsed.get("relation", "neutral"),
                confidence=float(parsed.get("confidence", 0.5)),
            )
        except Exception as e:
            logger.warning("LLM entailment check failed: %s", e)
            return EntailmentResult(relation="neutral", confidence=0.5)

    def check_contradiction(self, commitment: str, action: str) -> EntailmentResult:
        import json
        prompt = (
            f'Does this action contradict this commitment?\n\n'
            f'Commitment: "{commitment}"\n'
            f'Action: "{action}"\n\n'
            f'A contradiction means the action LOGICALLY REQUIRES that the '
            f'commitment is false — not merely that the action is suboptimal.\n\n'
            f'Respond with ONLY JSON: '
            f'{{"relation": "contradiction"|"neutral", '
            f'"confidence": 0.0-1.0}}'
        )

        try:
            text_parts = []
            with self._client.messages.stream(
                model=self._model,
                max_tokens=128,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(text)
            return EntailmentResult(
                relation=parsed.get("relation", "neutral"),
                confidence=float(parsed.get("confidence", 0.5)),
            )
        except Exception as e:
            logger.warning("LLM contradiction check failed: %s", e)
            return EntailmentResult(relation="neutral", confidence=0.5)


class TestBackend(EntailmentBackend):
    """Fixture-based backend for testing. No API calls.

    Uses the same coherence fixtures that the legacy test path used,
    but routed through the standard EntailmentBackend interface so
    the graph code path is unified.
    """

    def check_entailment(self, premise: str, hypothesis: str) -> EntailmentResult:
        # Test mode edges are handled by _compute_edges_test (fixture-based
        # node materialization). This backend returns neutral so the standard
        # _compute_edges path doesn't add spurious edges.
        return EntailmentResult(relation="neutral", confidence=0.3)

    def check_contradiction(self, commitment: str, action: str) -> EntailmentResult:
        """Check contradiction using coherence fixtures."""
        from nous.coherence import _TEST_COHERENCE

        key = (action, commitment)
        if key in _TEST_COHERENCE:
            result = _TEST_COHERENCE[key]
            if not result.coherent:
                return EntailmentResult(
                    relation="contradiction",
                    confidence=result.confidence,
                    explanation=result.explanation or "",
                )
            return EntailmentResult(
                relation="neutral",
                confidence=result.confidence,
            )
        return EntailmentResult(relation="neutral", confidence=0.5)


def get_backend(
    backend: str = "auto",
    api_key: Optional[str] = None,
) -> EntailmentBackend:
    """Get the best available entailment backend.

    Args:
        backend: "nli", "embedding", "llm", or "auto" (tries nli → llm → embedding).
        api_key: For LLM backend.

    Returns:
        An EntailmentBackend instance.
    """
    if backend == "nli":
        return NLIBackend()
    elif backend == "embedding":
        return EmbeddingBackend()
    elif backend == "llm":
        return LLMBackend(api_key=api_key)
    elif backend == "auto":
        # Try NLI first (free, fast, accurate)
        try:
            return NLIBackend()
        except ImportError:
            pass

        # Try LLM (accurate, costs money)
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return LLMBackend(api_key=key)

        # Fall back to embedding (free, fast, less accurate)
        try:
            return EmbeddingBackend()
        except ImportError:
            raise RuntimeError(
                "No entailment backend available. Either:\n"
                "  1. pip install sentence-transformers  (recommended, free)\n"
                "  2. Set ANTHROPIC_API_KEY  (accurate, costs money)\n"
            )
    else:
        raise ValueError(f"Unknown backend: {backend}")
