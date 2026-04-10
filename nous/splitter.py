"""Text splitter: parse raw reasoning text into structured [{text, action}] steps.

Handles ChatGPT-style output, Claude-style output, plain prose, numbered proofs.
"""
from __future__ import annotations

import re


def split_reasoning(text: str) -> list[dict]:
    """Parse raw reasoning text into [{text, action}] steps.

    Tries, in order:
    1. Numbered steps (1., 2., Step 1:, etc.)
    2. --- delimiters
    3. Paragraph breaks (double newline)
    4. Single chunk fallback

    The concluding sentence of each chunk becomes the action;
    everything prior is the reasoning text.
    """
    text = text.strip()
    if not text:
        return []

    chunks = _split_numbered(text)
    if len(chunks) < 2:
        chunks = _split_delimited(text)
    if len(chunks) < 2:
        chunks = _split_paragraphs(text)
    if len(chunks) < 2:
        chunks = _split_sentences(text)
    if len(chunks) < 2:
        chunks = [text]

    steps = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        reasoning, action = _extract_action(chunk)
        if reasoning or action:
            steps.append({"text": reasoning, "action": action})

    return steps


# ── Splitters ────────────────────────────────────────────────────────────

def _split_numbered(text: str) -> list[str]:
    """Split on '1.', '1)', 'Step 1:', 'Step 1.', heading patterns."""
    pattern = r'(?:^|\n)(?:Step\s+)?\d+[.):][ \t]+'
    parts = re.split(pattern, text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _split_delimited(text: str) -> list[str]:
    """Split on '---' or '===' horizontal rules."""
    parts = re.split(r'\n(?:-{3,}|={3,})\n', text)
    return [p.strip() for p in parts if p.strip()]


def _split_paragraphs(text: str) -> list[str]:
    """Split on double (or more) newlines."""
    parts = re.split(r'\n\n+', text)
    return [p.strip() for p in parts if p.strip()]


def _split_sentences(text: str) -> list[str]:
    """Last resort: split on sentence boundaries, grouping into ~2-sentence chunks."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if len(sentences) < 2:
        return [text]
    # Group into pairs so each "step" has substance
    chunks = []
    for i in range(0, len(sentences), 2):
        chunk = ' '.join(sentences[i:i + 2])
        if chunk:
            chunks.append(chunk)
    return chunks


# ── Action extractor ─────────────────────────────────────────────────────

def _extract_action(chunk: str) -> tuple[str, str]:
    """Extract (reasoning_text, action) from a chunk.

    Heuristic: the last sentence is the action/conclusion.
    If only one sentence, it is used as both.
    """
    # Split by sentence-ending punctuation followed by whitespace
    sentences = re.split(r'(?<=[.!?])\s+', chunk.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return chunk.strip(), "Continue reasoning"

    if len(sentences) == 1:
        return chunk.strip(), sentences[0]

    action = sentences[-1]
    reasoning = " ".join(sentences[:-1])
    return reasoning, action
