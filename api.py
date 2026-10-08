"""One HTTP API over the whole project.

    uvicorn api:app --reload --port 8000
    open http://127.0.0.1:8000/docs

    /rag/ask        weeks 1-5   retrieval + guarded answer over the recipe corpus
    /agent/ask      weeks 7-8   three-tool agent, optional week-8 guards / injection test
    /mcp/ask        week 9      MCP host agent (recipes + ingredient_db, or via the gateway)
    /squad/ask      week 10     planner + substitution worker + allergen worker + synthesis
    /eval/week8     week 8      saved baseline / after / injection results (no model call)
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Literal, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from agent.mcp_agent import McpHost, discover, run_mcp_agent  # noqa: E402

# Named configs only: the caller picks a key, never a file path.
MCP_CONFIGS = {
    "direct": ROOT / "config" / "mcp_servers.json",
    "gateway": ROOT / "config" / "mcp_servers.gateway.json",
}
# The gateway reads GATEWAY_TOKEN from the process env, so gateway runs are serialised.
_gateway_lock = threading.Lock()

app = FastAPI(title="Recipe RAG + agents")


def _need_groq() -> None:
    if not os.environ.get("GROQ_API_KEY"):
        raise HTTPException(503, "GROQ_API_KEY is not set in .env")


def _strip(out: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in out.items() if k != "messages"}


@app.get("/health")
def health() -> Dict[str, Any]:
    chroma = ROOT / ".chroma"
    return {
        "ok": True,
        "groq_key_set": bool(os.environ.get("GROQ_API_KEY")),
        "langfuse_keys_set": bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")),
        "chroma_index_present": chroma.exists() and any(chroma.iterdir()),
    }


# --------------------------------------------------------------------- weeks 1-5

class RagRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["How do I make a vegan paneer butter masala?"])
    strategy: Literal["basic", "structured"] = "structured"
    mode: Literal["semantic", "bm25", "hybrid"] = "semantic"
    k: int = Field(4, ge=1, le=20)
    rerank: bool = False
    dietary_tag: Optional[str] = Field(None, description="e.g. vegan, gluten-free")


@app.post("/rag/ask")
def rag_ask(req: RagRequest) -> Dict[str, Any]:
    _need_groq()
    from guardrails import answer_question
    from retrieve import dietary_filter, search

    where = dietary_filter(req.dietary_tag) if req.dietary_tag else None
    try:
        hits = search(req.question, strategy=req.strategy, k=req.k, where=where, mode=req.mode, rerank=req.rerank)
    except Exception as exc:  # most likely: index not built yet
        raise HTTPException(
            500,
            f"retrieval failed ({type(exc).__name__}: {exc}). Build the index first: python scripts/ingest.py",
        ) from exc
    result = answer_question(req.question, hits)
    result["hits"] = [
        {"id": h.get("id"), "score": h.get("score"), "metadata": h.get("metadata")} for h in hits
    ]
    return result


# --------------------------------------------------------------------- weeks 7-8

class AgentRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["Scale the paneer butter masala to 8 servings. No swaps."])
    strict_path: bool = Field(False, description="week 8 guard: least-privilege tool order")
    cascade_guard: bool = Field(False, description="week 8 guard: block 'done' until introduced allergens are checked")
    enable_document_tool: bool = Field(False, description="expose read_source_document (injection surface)")
    poison_notes: bool = Field(False, description="week 8 attack: poisoned source-card notes (needs document tool)")
    defended: bool = Field(False, description="week 8 injection defenses: strip, wrap, validate")


@app.post("/agent/ask")
def agent_ask(req: AgentRequest) -> Dict[str, Any]:
    _need_groq()
    from agent.loop import run_agent
    from config import WEEK8_MODEL

    out = run_agent(
        req.question, model=WEEK8_MODEL, enable_document_tool=req.enable_document_tool,
        poison_notes=req.poison_notes, defended=req.defended,
        strict_path=req.strict_path, cascade_guard=req.cascade_guard,
    )
    return _strip(out)


@app.get("/eval/week8")
def eval_week8() -> Dict[str, Any]:
    """Saved results: baseline, after, injection, verdict. No model call."""
    w8 = ROOT / "eval" / "week8"
    out: Dict[str, Any] = {}
    for name in ("baseline", "after"):
        p = w8 / f"{name}.json"
        if p.exists():
            out[name] = json.loads(p.read_text(encoding="utf-8")).get("summary")
    p = w8 / "injection.json"
    if p.exists():
        rows = json.loads(p.read_text(encoding="utf-8"))
        out["injection"] = [
            {"id": r["id"], "phase": r.get("phase"), "tricked": r.get("tricked"), "outcome_pass": r.get("outcome_pass")}
            for r in rows
        ]
    p = w8 / "verdict.md"
    if p.exists():
        out["verdict"] = p.read_text(encoding="utf-8")
    return out


# ----------------------------------------------------------------------- week 9

class McpRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["How many kcal in 100 g of paneer?"])
    config: Literal["direct", "gateway"] = "direct"
    gateway_token: Optional[str] = Field(
        None, description="Only for config=gateway, e.g. tok-recipe-agent-allergen-only"
    )


@app.get("/mcp/tools")
def mcp_tools(config: Literal["direct", "gateway"] = "direct") -> Dict[str, Any]:
    """tools/list across the configured servers. No model call."""
    if config == "gateway":
        with _gateway_lock:
            os.environ.setdefault("GATEWAY_TOKEN", "tok-recipe-agent-full")
            found = discover(MCP_CONFIGS[config])
    else:
        found = discover(MCP_CONFIGS[config])
    return {"config": config, "count": len(found), "tools": found}


@app.post("/mcp/ask")
def mcp_ask(req: McpRequest) -> Dict[str, Any]:
    _need_groq()
    if req.config == "gateway":
        with _gateway_lock:
            os.environ["GATEWAY_TOKEN"] = req.gateway_token or "tok-recipe-agent-full"
            return _strip(run_mcp_agent(req.question, config_path=MCP_CONFIGS["gateway"]))
    return _strip(run_mcp_agent(req.question, config_path=MCP_CONFIGS["direct"]))


# ---------------------------------------------------------------------- week 10

def _race_module():
    """scripts/run_week10_race.py is not a package; load it for its FORMAT_SPEC."""
    spec = importlib.util.spec_from_file_location("run_week10_race", ROOT / "scripts" / "run_week10_race.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SquadRequest(BaseModel):
    request: str = Field(..., min_length=1, examples=["Make the Thai green curry vegan."])
    constraint: str = Field(..., examples=["vegan"])
    servings: int = Field(4, ge=1, le=50)
    inject_500_on_allergen: bool = Field(False, description="fault injection: allergen worker fails with HTTP 500")


@app.post("/squad/ask")
def squad_ask(req: SquadRequest) -> Dict[str, Any]:
    _need_groq()
    from multi.orchestrator import run_orchestrator

    race = _race_module()
    task = f"{req.request}\nConstraint: {req.constraint}\nServings: {req.servings}"
    host = McpHost(race.CFG).connect()
    try:
        return run_orchestrator(task, race.FORMAT_SPEC, host, inject_500_on_allergen=req.inject_500_on_allergen)
    finally:
        host.close()
