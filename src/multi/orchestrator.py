"""Kitchen squad: planner -> substitution worker -> allergen worker -> synthesis.

Narrow on purpose (the only plausible source of a win over one agent):
  substitution worker : search_recipes, scale_recipe, get_allergen_profile   (the card)
  allergen worker     : get_ingredient_allergens, get_ingredient_nutrition   (the ingredient DB)
The allergen worker only sees the substitution worker's draft, never the corpus.

Hand-offs (metered by name):
  H1 user->orchestrator (plan)
  H2 orchestrator->substitution_worker
  H3 orchestrator->allergen_worker      (re-sends the draft)
  H4 workers->orchestrator (synthesis)  (re-sends both reports)
"""
from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional

from agent.mcp_agent import McpHost
from multi.runtime import Meter, llm, tool_loop

SUB_TOOLS = ["search_recipes", "scale_recipe", "get_allergen_profile"]
ALLERGEN_TOOLS = ["get_ingredient_allergens", "get_ingredient_nutrition"]

PLAN_SYS = ("You are a kitchen orchestrator. Read the request and reply with ONLY a JSON object: "
            '{"recipe_query": "<dish name to search>", "constraint": "<dietary constraint>", '
            '"servings": <int or null>}. No prose.')
SUB_SYS = ("You are the substitution worker. Find the recipe card, scale it, and rewrite it so it honours the constraint, "
           "using only swaps the card itself writes (get_allergen_profile returns them). Return the draft in the requested format. "
           "You do not verify ingredient allergens beyond the card.")
ALLERGEN_SYS = ("You are the allergen worker. For the ingredients in the draft you are given, look up allergen flags with your tools "
                "(one ingredient per call) and report which ingredients carry an allergen relevant to the constraint, and any "
                "allergen present in the final list. Never state a flag a tool did not return. Reply with a short report.")
SYNTH_SYS = ("You are the orchestrator. Combine the worker reports into the final answer in the requested format. "
             "Keep any caveat a worker raised.")


class WorkerFailed(Exception):
    pass


def _allergen_worker(host: McpHost, constraint: str, draft: str, meter: Meter, inject_500: bool) -> str:
    if inject_500:  # fault injection: the worker's HTTP endpoint answers 500
        raise WorkerFailed("HTTP 500 Internal Server Error from allergen_worker")
    out = tool_loop(ALLERGEN_SYS, f"CONSTRAINT: {constraint}\n\nDRAFT:\n{draft}", host, ALLERGEN_TOOLS, meter, "H3 orchestrator->allergen_worker")
    return out["text"]


def run_orchestrator(task: str, format_spec: str, host: McpHost, *, inject_500_on_allergen: bool = False,
                     retries: int = 1) -> Dict:
    meter = Meter()
    events: List[str] = []
    t0 = time.perf_counter()

    plan_resp = llm([{"role": "system", "content": PLAN_SYS}, {"role": "user", "content": task}], meter, "H1 user->orchestrator")
    m = re.search(r"\{.*\}", plan_resp.get("content") or "", re.S)
    try:
        plan = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        plan = {}
    events.append(f"plan={json.dumps(plan)}")

    sub = tool_loop(SUB_SYS, f"{task}\n\nPLAN: {json.dumps(plan)}\n\n{format_spec}", host, SUB_TOOLS, meter,
                    "H2 orchestrator->substitution_worker")
    draft = sub["text"]
    events.append(f"substitution_worker calls={[c['tool'] for c in sub['calls']]}")

    allergen_report, failure = "", None
    for attempt in range(retries + 1):
        try:
            allergen_report = _allergen_worker(host, plan.get("constraint", ""), draft, meter, inject_500_on_allergen)
            failure = None
            break
        except WorkerFailed as exc:
            failure = str(exc)
            events.append(f"allergen_worker attempt {attempt + 1} FAILED: {failure}")
    if failure:
        allergen_report = f"[allergen_worker error: {failure}]"

    synth = llm([{"role": "system", "content": SYNTH_SYS},
                 {"role": "user", "content": f"{task}\n\nSUBSTITUTION WORKER REPORT:\n{draft}\n\nALLERGEN WORKER REPORT:\n{allergen_report}\n\n{format_spec}"}],
                meter, "H4 workers->orchestrator (synthesis)")
    return {
        "answer": synth.get("content") or "", "tokens": meter.tokens, "cost_usd": meter.cost(),
        "latency_ms": int((time.perf_counter() - t0) * 1000), "handoffs": meter.rows,
        "by_handoff": meter.by_handoff(), "events": events, "allergen_failure": failure,
        "draft": draft, "allergen_report": allergen_report,
        "worker_calls": {"substitution": sub["calls"]},
    }
