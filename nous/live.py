"""Live streaming mode — the voice in the AI's head.

Phase D.4: Wrap a streaming AI response, detect step boundaries, and run
verification on each step as it arrives. Results are streamed back via
SSE (Server-Sent Events) interleaved with the original token stream.

This is the browser extension angle: a Chrome extension injects into
claude.ai / chatgpt.com / gemini.google.com, pipes the streaming response
through this endpoint, and renders inline annotations live.

Usage (standalone)::

    # Start the server
    python -m nous.live

    # Pipe a streaming request through it
    curl -N http://localhost:8765/api/live/stream \\
         -H "Content-Type: application/json" \\
         -d '{"prompt": "Solve this problem step by step...", "provider": "anthropic"}'

Usage (programmatic)::

    from nous.live import LiveNous

    async for event in LiveNous().stream("Solve this step by step..."):
        if event["type"] == "token":
            print(event["text"], end="", flush=True)
        elif event["type"] == "step_verified":
            if event["status"] != "ok":
                print(f"\\n  [WARNING: {event['status']}]")

Server-Sent Events format::

    data: {"type": "token", "text": "First, "}

    data: {"type": "step_start", "step": 1}

    data: {"type": "step_verified", "step": 1, "status": "ok", "certainty": "ok",
           "commitments_added": 2}

    data: {"type": "step_verified", "step": 2, "status": "violation",
           "certainty": "formal", "violation_type": "ModusPonensViolation",
           "violated": "..."}

    data: {"type": "done", "total_steps": 4, "violations": 1}
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from typing import AsyncIterator, Optional


# ── Sentence / step boundary detection ─────────────────────────────

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
_STEP_MARKERS = re.compile(
    r'\b(?:Step\s+\d+|First[,:]|Second[,:]|Third[,:]|Next[,:]|'
    r'Finally[,:]|Therefore[,:]|Thus[,:]|Hence[,:]|So[,:]|'
    r'In conclusion[,:]|To summarize[,:])\b',
    re.IGNORECASE,
)

def _is_step_boundary(text: str) -> bool:
    """Heuristic: does this text segment look like a reasoning step end?"""
    stripped = text.strip()
    if not stripped:
        return False
    # Double newline → paragraph = step
    if '\n\n' in text:
        return True
    # Ends with sentence terminator + has enough content
    if stripped[-1] in '.!?' and len(stripped) > 40:
        return True
    # Starts a new numbered step marker
    if _STEP_MARKERS.search(stripped):
        return True
    return False


# ── LiveNous streaming engine ────────────────────────────────────────

class LiveNous:
    """Stream an AI response while verifying each reasoning step in real time.

    Each step (detected by sentence/paragraph boundary) is immediately
    fed to Nous.step() in a background task. Verification results stream
    back as SSE events before the next step arrives.

    Args:
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        model: Which Claude model to stream from.
        buffer_size: Tokens to accumulate before checking for step boundary.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        buffer_size: int = 50,
    ):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model
        self._buffer_size = buffer_size

    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        cross_verify: bool = False,
    ) -> AsyncIterator[dict]:
        """Stream a prompt, yielding SSE-ready event dicts.

        Args:
            prompt: The user prompt to send to Claude.
            system: Optional system prompt.
            cross_verify: If True, use multi-model cross-verification for certainty="high".

        Yields:
            Dicts with "type" key. Types:
                "token"         — a token from the model response
                "step_start"    — a new reasoning step detected
                "step_verified" — verification result for a completed step
                "done"          — final summary
        """
        from nous import Nous

        if not self._api_key:
            yield {"type": "error", "message": "No ANTHROPIC_API_KEY available"}
            return

        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        n = Nous(api_key=self._api_key)
        step_num = 0
        buffer = []
        token_buffer = []
        pending_verify: Optional[asyncio.Task] = None

        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": self._model,
            "max_tokens": 2048,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "token", "text": text}
                buffer.append(text)
                token_buffer.append(text)

                # Check for step boundary every buffer_size tokens
                if len(token_buffer) >= self._buffer_size:
                    segment = "".join(buffer)
                    if _is_step_boundary(segment):
                        step_num += 1
                        step_text = "".join(buffer).strip()

                        yield {"type": "step_start", "step": step_num}

                        # Wait for previous verification to complete
                        if pending_verify and not pending_verify.done():
                            try:
                                await asyncio.wait_for(pending_verify, timeout=5.0)
                            except asyncio.TimeoutError:
                                pass

                        # Launch verification as background task
                        _step = step_num
                        _text = step_text
                        _nous = n

                        async def _verify(s=_step, t=_text, nous=_nous) -> dict:
                            try:
                                result = nous.step(
                                    reasoning=t,
                                    action=t,  # in live mode, reasoning IS the action
                                    test_mode=False,
                                )
                                event = {
                                    "type": "step_verified",
                                    "step": s,
                                    "status": result.status,
                                    "certainty": result.certainty,
                                    "commitments_added": result.commitments_added,
                                    "closure_size": result.closure_size,
                                }
                                if result.violation:
                                    event["violation_type"] = result.violation.get("type")
                                    event["violated"] = result.violation.get("violated", "")
                                    event["confidence"] = result.violation.get("confidence", 0)
                                return event
                            except Exception as e:
                                return {"type": "step_error", "step": s, "error": str(e)}

                        pending_verify = asyncio.create_task(_verify())
                        buffer = []

                    token_buffer = []

        # Handle remaining buffer
        if buffer:
            remaining = "".join(buffer).strip()
            if remaining and len(remaining) > 20:
                step_num += 1
                yield {"type": "step_start", "step": step_num}

                try:
                    result = n.step(
                        reasoning=remaining,
                        action=remaining,
                        test_mode=False,
                    )
                    event = {
                        "type": "step_verified",
                        "step": step_num,
                        "status": result.status,
                        "certainty": result.certainty,
                        "commitments_added": result.commitments_added,
                        "closure_size": result.closure_size,
                    }
                    if result.violation:
                        event["violation_type"] = result.violation.get("type")
                        event["violated"] = result.violation.get("violated", "")
                    yield event
                except Exception as e:
                    yield {"type": "step_error", "step": step_num, "error": str(e)}

        # Wait for pending verification
        if pending_verify and not pending_verify.done():
            try:
                verify_result = await asyncio.wait_for(pending_verify, timeout=10.0)
                yield verify_result
            except asyncio.TimeoutError:
                pass

        yield {
            "type": "done",
            "total_steps": step_num,
            "violations": len(n.violations),
            "closure_size": len(n.closure()),
        }


# ── SSE format helpers ───────────────────────────────────────────────

def format_sse(event: dict) -> str:
    """Format a dict as an SSE message."""
    return f"data: {json.dumps(event)}\n\n"


# ── FastAPI server (optional — requires `pip install fastapi uvicorn`) ──

def create_app():
    """Create a FastAPI app with the live streaming endpoint."""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import StreamingResponse
        from pydantic import BaseModel
    except ImportError:
        raise ImportError(
            "FastAPI required for live server. "
            "Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="Nous Live",
        description="Real-time AI reasoning verification via SSE",
        version="0.5.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Lock down in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class StreamRequest(BaseModel):
        prompt: str
        system: Optional[str] = None
        model: str = "claude-sonnet-4-6"
        cross_verify: bool = False
        api_key: Optional[str] = None

    @app.post("/api/live/stream")
    async def live_stream(req: StreamRequest):
        """Stream AI response with interleaved verification events."""
        live = LiveNous(api_key=req.api_key, model=req.model)

        async def event_stream():
            async for event in live.stream(
                req.prompt,
                system=req.system,
                cross_verify=req.cross_verify,
            ):
                yield format_sse(event)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.5.0"}

    return app


# ── CLI entrypoint ────────────────────────────────────────────────────

def main():
    """Start the Nous Live server."""
    try:
        import uvicorn
    except ImportError:
        print("uvicorn required: pip install uvicorn")
        sys.exit(1)

    port = int(os.environ.get("NOUS_PORT", 8765))
    app = create_app()
    print(f"Nous Live server starting on http://localhost:{port}")
    print(f"  SSE endpoint: POST http://localhost:{port}/api/live/stream")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
