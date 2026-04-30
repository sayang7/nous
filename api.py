"""Nous API — FastAPI wrapper for the Nous reasoning engine."""
from __future__ import annotations

import asyncio
import html
import json
import os
import re
import urllib.request
from typing import Optional

# Load .env so ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY are available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nous import Nous
from nous.providers import get_provider
from nous.splitter import split_reasoning

app = FastAPI(title="Nous", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static examples ──────────────────────────────────────────────────────
EXAMPLES = {
    "catalyst": {
        "id": "catalyst", "icon": "⚗", "title": "Air-Sensitive Catalyst",
        "domain": "Chemistry",
        "desc": "A lab agent records that a palladium catalyst is oxygen-sensitive, transfers it under nitrogen, then opens the flask to air.",
        "watch": "Builds the chain: air-sensitive → must avoid oxygen. When the flask opens, commitment violated.",
        "steps": [
            {"text": "The palladium catalyst is air-sensitive and must be handled under inert atmosphere (N2 or Ar). Exposure to oxygen will deactivate it.", "action": "Note catalyst handling requirements."},
            {"text": "Weigh 50mg of catalyst in the glovebox and transfer to the Schlenk flask under nitrogen.", "action": "Transfer catalyst to reaction vessel."},
            {"text": "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.", "action": "Open flask to air to add reagent."},
        ],
    },
    "math": {
        "id": "math", "icon": "∫", "title": "Assumption Drift",
        "domain": "Mathematics",
        "desc": "A proof establishes continuity, then silently assumes differentiability — a strictly stronger property never proved.",
        "watch": "Steps 1–2 establish continuity. Step 3 assumes differentiability — a stronger property never proved.",
        "steps": [
            {"text": "Function f is continuous on the closed interval [a,b]. This follows from the composition of continuous functions.", "action": "Establish continuity of f on [a,b]."},
            {"text": "By the Intermediate Value Theorem, since f is continuous on [a,b] and f(a) < 0 < f(b), there exists c in (a,b) with f(c) = 0.", "action": "Apply IVT to locate root."},
            {"text": "To find extrema, I need to find critical points. Since f is differentiable everywhere on (a,b), I can compute f'(x) and set it to zero.", "action": "Differentiate f on (a,b) to find critical points."},
        ],
    },
    "drug": {
        "id": "drug", "icon": "⬡", "title": "Contradictory Recommendation",
        "domain": "Drug Discovery",
        "desc": "An agent derives that compound X impairs pathway Z, then recommends X to enhance Z.",
        "watch": "Steps 1–3 derive that X impairs Z. Step 4 directly contradicts the derived conclusion.",
        "steps": [
            {"text": "Paper A (Chen et al. 2024) reports that compound X is a potent inhibitor of kinase Y, with IC50 = 12nM.", "action": "Review literature on compound X."},
            {"text": "Paper B (Zhang et al. 2025) shows that kinase Y is essential for activating pathway Z. Knockout of kinase Y abolishes pathway Z activity entirely.", "action": "Record kinase Y role in pathway Z."},
            {"text": "Synthesizing these findings: since X inhibits Y, and Y is required for Z, compound X would impair pathway Z signaling.", "action": "Derive effect of X on pathway Z."},
            {"text": "Based on the literature, we recommend compound X as a potential enhancer of pathway Z for therapeutic applications.", "action": "Recommend X to enhance pathway Z."},
        ],
    },
    "code": {
        "id": "code", "icon": "⟨⟩", "title": "API Type Mismatch",
        "domain": "Code Agent",
        "desc": "An agent reads that an API returns JSON, acknowledges it needs parsing, then splits the response by commas.",
        "watch": "The agent commits to 'response is JSON' and 'JSON needs parsing', then treats the response as plain text.",
        "steps": [
            {"text": "The API documentation confirms the endpoint returns JSON.", "action": "Send GET request to the endpoint."},
            {"text": "JSON responses need to be parsed before accessing fields.", "action": "Store the response body."},
            {"text": "Let me extract the 'name' field from the response.", "action": "Split response string by commas to find name."},
        ],
    },
}

VIOLATION_LABELS = {
    "ModusPonensViolation": "Logical Contradiction",
    "BeliefRevisionFailure": "Ignored Update",
    "ModalScopeError": "Certainty Mismatch",
    "TemporalCoherenceViolation": "Temporal Inconsistency",
    "ReferentialOpacityFailure": "Referential Confusion",
}


# ── Request models ───────────────────────────────────────────────────────

class StepIn(BaseModel):
    text: str
    action: str
    step: Optional[int] = None

class AnalyzeRequest(BaseModel):
    steps: list[StepIn]
    test_mode: bool = True

class ReasonRequest(BaseModel):
    problem: str
    provider: str = "anthropic"
    api_key: Optional[str] = None
    test_mode: bool = False

class URLRequest(BaseModel):
    url: str
    test_mode: bool = False

class TextRequest(BaseModel):
    text: str
    test_mode: bool = False


# ── Shared helpers ───────────────────────────────────────────────────────

def _label_violations(items: list[dict]) -> list[dict]:
    for v in items:
        raw = v.get("type", "")
        v["label"] = VIOLATION_LABELS.get(raw, raw)
    return items


def _run_pipeline(steps_raw: list[dict], test_mode: bool) -> dict:
    n = Nous()
    results = []
    for i, step in enumerate(steps_raw):
        r = n.step(step["text"], step["action"], step_index=i + 1, test_mode=test_mode)
        results.append({
            "step_index": r.step_index,
            "coherent": r.coherent,
            "violation": r.violation,
            "commitments_added": r.commitments_added,
            "total_commitments": r.total_commitments,
        })

    graph_dict = n.graph.to_dict()
    _label_violations(graph_dict.get("violations", []))

    for r in results:
        if r.get("violation"):
            _label_violations([r["violation"]])

    violations = n.violations
    _label_violations(violations)

    return {
        "steps": steps_raw,
        "results": results,
        "graph": graph_dict,
        "violations": violations,
        "summary": {
            "total_steps": len(steps_raw),
            "violation_count": len(violations),
            "coherent_count": sum(1 for r in results if r["coherent"]),
        },
    }


def _fetch_url_text(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; Nous/0.5)"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode("utf-8", errors="replace")
    raw = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<style[^>]*>.*?</style>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Standard endpoints ───────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"ok": True, "version": "0.5.0"}


@app.get("/api/examples")
def get_examples():
    return list(EXAMPLES.values())


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if not req.steps:
        raise HTTPException(status_code=400, detail="steps required")
    steps_raw = [{"text": s.text, "action": s.action} for s in req.steps]
    return _run_pipeline(steps_raw, req.test_mode)


@app.post("/api/reason")
def reason(req: ReasonRequest):
    """Non-streaming: AI reasons, Nous analyzes, returns full result."""
    if not req.problem.strip():
        raise HTTPException(status_code=400, detail="problem required")
    try:
        provider = get_provider(req.provider, api_key=req.api_key)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        steps_raw = provider.reason(req.problem)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Provider error: {e}")
    if not steps_raw:
        raise HTTPException(status_code=502, detail="Provider returned no reasoning steps")
    result = _run_pipeline(steps_raw, req.test_mode)
    result["problem"] = req.problem
    result["provider"] = req.provider
    return result


@app.post("/api/stream/reason")
async def stream_reason(req: ReasonRequest):
    """SSE stream: AI reasons live, Nous analyzes each step as it arrives."""
    if not req.problem.strip():
        raise HTTPException(status_code=400, detail="problem required")

    def sse(type_: str, data: dict) -> str:
        data["type"] = type_
        return f"data: {json.dumps(data)}\n\n"

    async def generate():
        yield sse("status", {"msg": f"Thinking with {req.provider}…"})
        await asyncio.sleep(0)

        try:
            provider = get_provider(req.provider, api_key=req.api_key)
        except Exception as e:
            yield sse("error", {"msg": str(e)})
            return

        try:
            steps_raw = await asyncio.to_thread(provider.reason, req.problem)
        except Exception as e:
            yield sse("error", {"msg": f"Provider error: {e}"})
            return

        if not steps_raw:
            yield sse("error", {"msg": "No reasoning steps returned."})
            return

        yield sse("ready", {"count": len(steps_raw)})
        await asyncio.sleep(0)

        n = Nous()
        all_results = []

        for i, step in enumerate(steps_raw):
            # Surface the step first (before analysis) — gives live feel
            yield sse("step", {"i": i, "step": step})
            await asyncio.sleep(0)

            # Analyze — run blocking LLM entailment calls in thread pool
            # so the event loop (and SSE flush) stays responsive
            r = await asyncio.to_thread(
                n.step, step["text"], step["action"],
                step_index=i + 1, test_mode=False,
            )
            result = {
                "step_index": r.step_index,
                "coherent": r.coherent,
                "violation": r.violation,
                "commitments_added": r.commitments_added,
                "total_commitments": r.total_commitments,
            }
            if result.get("violation"):
                _label_violations([result["violation"]])
            all_results.append(result)

            yield sse("result", {"i": i, "result": result})
            # Small pause so browser has time to render each step visually
            await asyncio.sleep(0.25)

        graph_dict = n.graph.to_dict()
        _label_violations(graph_dict.get("violations", []))
        violations = n.violations
        _label_violations(violations)

        yield sse("done", {
            "steps": steps_raw,
            "results": all_results,
            "graph": graph_dict,
            "violations": violations,
            "summary": {
                "total_steps": len(steps_raw),
                "violation_count": len(violations),
                "coherent_count": sum(1 for r in all_results if r["coherent"]),
            },
            "problem": req.problem,
            "provider": req.provider,
        })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


@app.post("/api/import/url")
def import_url(req: URLRequest):
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url required")
    try:
        text = _fetch_url_text(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")
    if len(text) < 50:
        raise HTTPException(status_code=422, detail="Not enough text content found at URL")
    steps_raw = split_reasoning(text[:8000])
    if len(steps_raw) < 2:
        raise HTTPException(status_code=422, detail="Could not split content into reasoning steps")
    result = _run_pipeline(steps_raw, req.test_mode)
    result["source_url"] = req.url
    return result


@app.post("/api/analyze/text")
def analyze_text(req: TextRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text required")
    steps_raw = split_reasoning(req.text)
    if not steps_raw:
        raise HTTPException(
            status_code=422,
            detail="Could not extract any reasoning steps from the text.",
        )
    return _run_pipeline(steps_raw, req.test_mode)


# ── Serve React SPA ──────────────────────────────────────────────────────
_frontend = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        return FileResponse(os.path.join(_frontend, "index.html"))
