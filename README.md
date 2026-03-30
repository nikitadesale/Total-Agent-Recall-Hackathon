# 👁️ Sentinel Twin - Privacy-First Digital Twin

> *"What if one AI had full context of your life — and used it to protect you?"*

Sentinel Twin is a privacy-first personal AI guardian that mirrors your entire digital life with your consent. It connects your finance, health, transport, subscriptions, habits, and calendar data to make smarter, proactive decisions on your behalf, powered by **Kimi K2.5 via GMI Cloud** and **HydraDB** for pattern memory.

---

## 🎯 The Idea

Most apps give you data. Sentinel Twin gives you **decisions**.

It knows:
- 💰 Your bank balance and spending patterns
- 🥗 Your calorie targets and allergens
- 🚗 Uber surge pricing and your commute habits
- 📱 Which subscriptions you're wasting money on
- 🏃 Your sleep debt, steps, and gym streak
- 📅 Your upcoming calendar and social load

And it acts as a guardian, blocking bad decisions, surfacing smart alternatives, and connecting dots across domains before you even notice the pattern.

---

## 🏗 Architecture

```
You (React UI)
      │
      ▼
React + Vite  (localhost:5173)
  Chat Panel · Smart Alerts · Live Vault · Memory · TTS
      │  Axios REST
      ▼
FastAPI  (localhost:8000)
  /vault/status  → live state of all 6 domains
  /chat          → AI reasoning with smart context routing
  /insights      → proactive alerts engine
  /validate/action → reconciliation (budget · calories · allergens)
  /memory/recall → HydraDB pattern search
      │                          │
      ▼                          ▼
GMI Cloud                    HydraDB
Kimi K2.5                    Pattern Memory
(LLM Reasoning)              (Stores every decision)
```

**Smart Context Routing** — the `/chat` endpoint reads query intent and only loads relevant data domains, saving ~60% tokens per call.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI (Python 3.9+) |
| LLM | moonshotai/Kimi-K2.5 via GMI Cloud |
| Memory | HydraDB |
| Health data | FHIR-Lite schema |
| Finance data | ISO-20022 style |
| Identity | JSON-LD |

---

## 🚀 Quick Start

### 1. Clone & install backend
```bash
git clone https://github.com/your-username/Hackathon-Sentinel-Ai-Twin
cd Hackathon-Sentinel-Ai-Twin

pip install -r requirements.txt
```

### 2. Set up API keys
```bash
cp .env.example .env
# Edit .env and add your GMI_API_KEY and HYDRA_API_KEY
```

Get keys from:
- **GMI Cloud**: https://console.gmi.ai — free tier available
- **HydraDB**: https://www.hydradb.com — free tier available

### 3. Install frontend
```bash
cd frontend
npm install
cd ..
```

### 4. Run everything
```bash
chmod +x start.sh
./start.sh
```

Or manually in two terminals:
```bash
# Terminal 1 — API
export GMI_API_KEY="your_key"
export HYDRA_API_KEY="your_key"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — UI
cd frontend && npm run dev
```

Open **http://localhost:5173**

---

## 📡 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/vault/status` | Full digital twin state (all 6 domains) |
| `POST` | `/chat` | Chat with Kimi K2.5 (vault-aware) |
| `GET` | `/insights` | Proactive smart alerts |
| `POST` | `/validate/action` | Check food/transport/spend against constraints |
| `GET` | `/memory/recall` | Query past decisions from HydraDB |
| `GET` | `/docs` | Interactive Swagger UI |

### Example — Validate an action
```bash
curl -X POST http://localhost:8000/validate/action \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "food_order",
    "item": "Spicy Tuna Roll",
    "cost": 22.00,
    "calories": 500,
    "ingredients": ["tuna", "rice", "seaweed"]
  }'
```

Response:
```json
{
  "status": "APPROVED",
  "reason": "All constraints satisfied: budget, calories, and allergens.",
  "alternative": "No alternative needed — action is fully compliant."
}
```

---

## 🧠 Smart Use Cases

| Scenario | What Sentinel Twin Does |
|---|---|
| You open DoorDash | Checks remaining food budget, calorie target, and allergens |
| You request an Uber | Detects 2.3x surge, suggests waiting 8 min to save $8 |
| You haven't used Duolingo in 23 days | Flags $6.99/mo waste, suggests cancellation |
| 4.5h sleep debt accumulated | Suggests lights-out time based on next alarm |
| 3 DoorDash orders this week | Warns $2.50 left of weekly delivery budget |
| Friday invite arrives | Detects calendar pattern — you usually decline with 2+ midweek events |

---

## 🔒 Privacy Design

- **Stateless** — no transaction data is ever persisted by the middleware
- **Consent-first** — all data access is explicitly granted
- **De-identified output** — raw account IDs never exposed via API
- **Audit trail** — every request logs `[AUDIT] Accessing X_Vault for User-77a | Timestamp: ...`
- **Local data** — all profiles are synthetic JSON files, no real app connections needed for the demo

---

## 📁 Project Structure

```
Hackathon-Sentinel-Ai-Twin/
├── main.py                 # FastAPI app — all endpoints
├── logic.py                # Reconciliation engine (stateless)
├── requirements.txt
├── start.sh                # One-command launcher
├── .env.example            # API key template
├── architecture.html       # Interactive architecture diagram
├── data/
│   ├── finance_profile.json    # ISO-20022 style
│   ├── health_profile.json     # FHIR-Lite
│   ├── user_identity.json      # JSON-LD
│   ├── transport_profile.json  # Uber patterns
│   ├── subscriptions.json      # App usage
│   ├── habits_profile.json     # Sleep, fitness, screen
│   └── calendar_profile.json   # Schedule & events
└── frontend/
    ├── index.html
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx         # Full React UI
        └── App.css         # Dark theme styles
```

---

## 👁️ Built at Hackathon

Sentinel Twin — because your future self deserves a guardian.
