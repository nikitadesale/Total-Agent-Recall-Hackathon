"""
Sentinel Twin (S-Twin) — Full Stack API
Privacy-First Digital Twin | Hackathon Build

Covers: Finance · Health · Transport · Subscriptions · Habits · Calendar
LLM   : GMI Cloud / Kimi K2.5 (direct, no Dify)
Memory: HydraDB
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from logic import FinanceProfile, HealthProfile, ValidationResult, reconcile_action

# ── Config ────────────────────────────────────────────────────────────────────

logging.basicConfig(format="%(message)s", level=logging.INFO)
logger = logging.getLogger("sentinel-twin")

DATA_DIR      = Path(__file__).parent / "data"
HYDRA_KEY     = os.getenv("HYDRA_API_KEY", "")
HYDRA_BASE    = "https://api.hydradb.com"
HYDRA_TENANT  = "sentinel-twin-user77a"
GMI_KEY       = os.getenv("GMI_API_KEY", "")
GMI_BASE      = "https://api.gmi-serving.com/v1"
GMI_MODEL     = "moonshotai/Kimi-K2.5"

# ── Data loading ──────────────────────────────────────────────────────────────

def _load(filename: str) -> dict[str, Any]:
    p = DATA_DIR / filename
    return json.loads(p.read_text()) if p.exists() else {}

def _all_profiles() -> dict[str, Any]:
    return {
        "finance":       _load("finance_profile.json"),
        "health":        _load("health_profile.json"),
        "identity":      _load("user_identity.json"),
        "transport":     _load("transport_profile.json"),
        "subscriptions": _load("subscriptions.json"),
        "habits":        _load("habits_profile.json"),
        "calendar":      _load("calendar_profile.json"),
    }

# ── Audit ─────────────────────────────────────────────────────────────────────

def _audit(domain: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    logger.info("[AUDIT] Accessing %s for User-77a | Timestamp: %s", domain, ts)

# ── HydraDB ───────────────────────────────────────────────────────────────────

def _hydra(path: str, payload: dict) -> dict:
    if not HYDRA_KEY:
        return {}
    try:
        req = urllib.request.Request(
            f"{HYDRA_BASE}{path}",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {HYDRA_KEY}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning("[HYDRA] %s failed: %s", path, e)
        return {}

def hydra_remember(title: str, text: str) -> None:
    _hydra("/memories/add_memory", {
        "tenant_id": HYDRA_TENANT,
        "memories": [{"text": text, "infer": True, "title": title}],
    })
    logger.info("[HYDRA] Remembered: %s", title)

def hydra_recall(query: str, max_results: int = 5) -> str:
    result = _hydra("/recall/full_recall", {
        "tenant_id": HYDRA_TENANT,
        "query": query,
        "max_results": max_results,
    })
    chunks = result.get("chunks", [])
    return "\n---\n".join(c.get("chunk_content", "") for c in chunks) if chunks else ""

# ── GMI Cloud / Kimi K2.5 ────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Sentinel Twin — a privacy-first personal AI guardian with full consent-based access to the user's life data.

Rules:
- Be concise, specific, and warm. Max 5–6 lines.
- Use actual numbers from the context. Never make up data.
- Connect dots across domains when relevant (sleep + food + money patterns).
- Protect their future self, not just their present impulse.
- Format with **bold** for key points and short bullet lines.
- Never expose internal IDs. Never be preachy — be smart."""

def gmi_chat(messages: list[dict], context: str = "") -> str:
    if not GMI_KEY:
        return "GMI_API_KEY not set. Add it to your environment."
    system = SYSTEM_PROMPT
    if context:
        system += f"\n\n## Recalled memory from HydraDB:\n{context}"

    payload = {
        "model": GMI_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": 600,
        "temperature": 0.7,
        "stream": False,
    }
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                f"{GMI_BASE}/chat/completions",
                "-H", f"Authorization: Bearer {GMI_KEY}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
            ],
            capture_output=True, text=True, timeout=35
        )
        data = json.loads(result.stdout)
        if "choices" not in data:
            logger.error("[GMI] Unexpected response: %s", result.stdout[:300])
            return f"Model error: {data.get('error', {}).get('message', result.stdout[:200])}"
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("[GMI] Error: %s", e)
        return f"Error calling GMI Cloud: {e}"

# ── Smart context builder ─────────────────────────────────────────────────────

def _smart_context(query: str) -> str:
    """Return only the vault domains relevant to the query — saves ~60% tokens."""
    q = query.lower()
    f  = _load("finance_profile.json")
    h  = _load("health_profile.json")
    t  = _load("transport_profile.json")
    s  = _load("subscriptions.json")
    hab= _load("habits_profile.json")
    cal= _load("calendar_profile.json")

    fin_rem  = round(f.get("daily_disposable_limit", 0) - f.get("spent_today", 0), 2)
    cal_rem  = h.get("nutritional_targets",{}).get("calories_max",0) - h.get("nutritional_targets",{}).get("calories_consumed",0)
    ride_rem = round(t.get("weekly_ride_budget",0) - t.get("spent_this_week",0), 2)
    dd_rem   = round(hab.get("doordash_weekly_budget",0) - hab.get("doordash_spent_this_week",0), 2)

    # Always include a compact baseline
    base = f"Finance: ${fin_rem} left today | DoorDash: {hab.get('doordash_orders_this_week',0)} orders, ${dd_rem} left"

    parts = [base]

    if any(w in q for w in ["uber","ride","car","taxi","surge","commute","travel"]):
        parts.append(f"Transport: surge {t.get('current_surge_multiplier','?')}x | drop in ~{t.get('estimated_surge_drop_minutes','?')}min | ${ride_rem} ride budget left")

    if any(w in q for w in ["food","eat","order","calorie","health","allerg","diet","meal","lunch","dinner"]):
        parts.append(f"Health: {cal_rem} kcal left | Allergens: {h.get('restrictions',{}).get('allergies',[])} | Diet: {h.get('restrictions',{}).get('dietary','')}")

    if any(w in q for w in ["gym","workout","steps","fitness","exercise","walk","run"]):
        fit = hab.get("fitness",{})
        parts.append(f"Fitness: {fit.get('steps_today',0)} steps today (goal {fit.get('steps_goal',0)}) | Last workout {fit.get('last_workout_days_ago',0)} days ago")

    if any(w in q for w in ["sleep","tired","rest","bed","morning","wake"]):
        slp = hab.get("sleep",{})
        parts.append(f"Sleep: {slp.get('sleep_debt_hours',0)}h debt | avg {slp.get('avg_hours',0)}h/night | next alarm {slp.get('next_alarm','?')}")

    if any(w in q for w in ["subscription","app","cancel","netflix","spotify","duolingo","waste","money"]):
        unused = [s["name"] for s in s.get("subscriptions",[]) if s.get("last_used_days_ago",0) > 14]
        parts.append(f"Subscriptions: wasting ${s.get('potential_monthly_savings',0)}/mo | Unused: {', '.join(unused)}")

    if any(w in q for w in ["calendar","schedule","meeting","event","week","today","tomorrow"]):
        parts.append(f"Calendar: {cal.get('today')} | Next: {[e['title'] for e in cal.get('upcoming_events',[])[:2]]} | {cal.get('social_events_this_week',0)} social events this week")

    # Fallback: send all if query is broad
    if len(parts) == 1:
        parts += [
            f"Health: {cal_rem} kcal left | Allergens: {h.get('restrictions',{}).get('allergies',[])}",
            f"Transport: surge {t.get('current_surge_multiplier','?')}x | ${ride_rem} ride budget",
            f"Sleep debt: {hab.get('sleep',{}).get('sleep_debt_hours',0)}h | Screen over limit: {hab.get('screen_time',{}).get('over_limit',False)}",
        ]

    return "## Your live data:\n" + "\n".join(f"- {p}" for p in parts)


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Sentinel Twin API",
    description="Privacy-First Digital Twin — Finance · Health · Transport · Habits · Calendar",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def _custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version,
                         description=app.description, routes=app.routes)
    schema["openapi"] = "3.0.3"
    app.openapi_schema = schema
    return schema

app.openapi = _custom_openapi

@app.exception_handler(Exception)
async def _err(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})

# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    include_vault: bool = True

class ActionRequest(BaseModel):
    action_type: str = Field(..., examples=["food_order"])
    item: str        = Field(..., examples=["Spicy Tuna Roll"])
    cost: float      = Field(..., gt=0)
    calories: int    = Field(..., ge=0)
    ingredients: list[str] = Field(default_factory=list)

    @field_validator("action_type", "item")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/vault/status", tags=["Vault"])
async def vault_status() -> dict[str, Any]:
    """Full digital twin state across all life domains."""
    _audit("Full_Vault")
    p = _all_profiles()
    f = FinanceProfile.from_dict(p["finance"])
    h = HealthProfile.from_dict(p["health"])
    return {
        "subject_ref": "User-77a",
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "finance": {
            "remaining_budget": f.remaining_budget,
            "daily_limit":      f.daily_disposable_limit,
            "spent_today":      f.spent_today,
            "currency":         f.currency,
            "liquidity_status": f.liquidity_status,
        },
        "health": {
            "remaining_calories": h.remaining_calories,
            "calories_max":       h.calories_max,
            "dietary_profile":    h.dietary,
            "known_allergens":    h.allergies,
        },
        "transport": {
            "remaining_ride_budget": round(
                p["transport"].get("weekly_ride_budget", 0) -
                p["transport"].get("spent_this_week", 0), 2),
            "current_surge":         p["transport"].get("current_surge_multiplier"),
            "surge_drop_in_mins":    p["transport"].get("estimated_surge_drop_minutes"),
        },
        "subscriptions": {
            "monthly_waste":  p["subscriptions"].get("potential_monthly_savings"),
            "waste_score":    p["subscriptions"].get("waste_score"),
            "unused_apps":    [s["name"] for s in p["subscriptions"].get("subscriptions", [])
                               if s.get("last_used_days_ago", 0) > 14],
        },
        "habits": {
            "steps_today":         p["habits"].get("fitness", {}).get("steps_today"),
            "steps_goal":          p["habits"].get("fitness", {}).get("steps_goal"),
            "sleep_debt_hours":    p["habits"].get("sleep", {}).get("sleep_debt_hours"),
            "screen_over_limit":   p["habits"].get("screen_time", {}).get("over_limit"),
            "doordash_this_week":  p["habits"].get("doordash_orders_this_week"),
        },
        "calendar": {
            "today":                    p["calendar"].get("today"),
            "work_meetings_tomorrow":   p["calendar"].get("work_meetings_tomorrow"),
            "social_events_this_week":  p["calendar"].get("social_events_this_week"),
            "pattern_insight":          p["calendar"].get("pattern_insight"),
        },
    }


@app.post("/validate/action", tags=["Reconciliation"])
async def validate_action(body: ActionRequest) -> dict[str, Any]:
    """Validate any action against health + finance constraints."""
    _audit("Health_Vault + Finance_Vault")
    f, h = FinanceProfile.from_dict(_load("finance_profile.json")), \
           HealthProfile.from_dict(_load("health_profile.json"))
    result: ValidationResult = reconcile_action(body.model_dump(), f, h)

    logger.info("[DECISION] %s | %s | %s", body.item, result.status, result.reason)
    hydra_remember(
        title=f"Decision — {body.item} — {result.status}",
        text=f"{result.status}: {body.item} | ${body.cost} | {body.calories}kcal | {result.reason}"
    )
    return {"status": result.status, "reason": result.reason, "alternative": result.alternative}


@app.get("/insights", tags=["Intelligence"])
async def get_insights() -> dict[str, Any]:
    """Proactive smart insights across all life domains."""
    _audit("All_Vaults_Insights")
    p = _all_profiles()
    insights = []

    # Uber surge alert
    t = p.get("transport", {})
    if t.get("current_surge_multiplier", 1) > t.get("surge_threshold_to_wait", 1.4):
        insights.append({
            "domain": "transport",
            "priority": "high",
            "icon": "🚗",
            "title": "Uber surge is 2.3x right now",
            "body": f"Wait {t.get('estimated_surge_drop_minutes', 8)} mins — surge drops to ~1.1x. Save ~$8.",
            "action": "wait",
        })

    # Subscription waste
    s = p.get("subscriptions", {})
    unused = [x["name"] for x in s.get("subscriptions", []) if x.get("last_used_days_ago", 0) > 20]
    if unused:
        insights.append({
            "domain": "subscriptions",
            "priority": "medium",
            "icon": "📱",
            "title": f"You're wasting ${s.get('potential_monthly_savings', 0)}/month",
            "body": f"{', '.join(unused)} unused for 20+ days. Cancel to save ${s.get('potential_monthly_savings', 0)}/mo.",
            "action": "cancel",
        })

    # DoorDash budget warning
    hab = p.get("habits", {})
    if hab.get("doordash_orders_this_week", 0) >= 3:
        spent = hab.get("doordash_spent_this_week", 0)
        budget = hab.get("doordash_weekly_budget", 50)
        insights.append({
            "domain": "habits",
            "priority": "high",
            "icon": "🍔",
            "title": f"4th DoorDash order this week?",
            "body": f"You've spent ${spent} of your ${budget} weekly food delivery budget. ${round(budget-spent, 2)} left.",
            "action": "block",
        })

    # Sleep debt
    sleep = hab.get("sleep", {})
    if sleep.get("sleep_debt_hours", 0) > 3:
        insights.append({
            "domain": "habits",
            "priority": "medium",
            "icon": "😴",
            "title": f"{sleep.get('sleep_debt_hours')}h sleep debt accumulated",
            "body": "You've averaged 6.5h this week vs 8h recommended. Tonight: lights out by 10:30 PM?",
            "action": "suggest",
        })

    # Gym guilt
    fit = hab.get("fitness", {})
    if fit.get("last_workout_days_ago", 0) >= 5:
        insights.append({
            "domain": "habits",
            "priority": "low",
            "icon": "🏃",
            "title": f"No workout in {fit.get('last_workout_days_ago')} days",
            "body": f"You've hit your gym goal {hab.get('fitness', {}).get('workouts_this_week', 0)}/3 times this week. You have a free block today 2-5 PM.",
            "action": "nudge",
        })

    # Pattern: calendar + social
    cal = p.get("calendar", {})
    if cal.get("pattern_insight"):
        insights.append({
            "domain": "calendar",
            "priority": "low",
            "icon": "📅",
            "title": "Pattern detected in your schedule",
            "body": cal["pattern_insight"],
            "action": "inform",
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "insights": insights,
        "total": len(insights),
    }


@app.post("/chat", tags=["Intelligence"])
async def chat(body: ChatRequest) -> dict[str, Any]:
    """
    Direct chat with Sentinel Twin (Kimi K2.5 via GMI Cloud).
    Injects full vault context + HydraDB memory automatically.
    """
    _audit("Chat_All_Vaults")

    last_msg = body.messages[-1].content if body.messages else ""

    # Build smart, query-aware vault context (fewer tokens)
    vault_ctx = ""
    if body.include_vault:
        vault_ctx = _smart_context(last_msg)

    # Recall relevant HydraDB memory
    memory   = hydra_recall(last_msg)

    messages = [m.model_dump() for m in body.messages]
    reply    = gmi_chat(messages, context=vault_ctx + ("\n## Past decisions:\n" + memory if memory else ""))

    # Store the conversation turn in HydraDB
    if body.messages:
        hydra_remember(
            title=f"Chat — {last_msg[:50]}",
            text=f"User: {last_msg}\nSentinel Twin: {reply}"
        )

    return {
        "reply":      reply,
        "model":      GMI_MODEL,
        "vault_used": body.include_vault,
        "memory_hit": bool(memory),
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }


@app.get("/memory/recall", tags=["Memory"])
async def memory_recall(query: str = "recent decisions") -> dict[str, Any]:
    """Recall relevant past decisions and patterns from HydraDB."""
    _audit("HydraDB_Memory")
    return {"query": query, "context": hydra_recall(query), "source": "HydraDB"}


@app.get("/health", include_in_schema=False)
async def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-twin", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
