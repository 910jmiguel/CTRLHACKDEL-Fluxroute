# FluxRoute — Setup & Run Guide

> AI-Powered Multimodal Routing for the Greater Toronto Area

---

## Prerequisites

| Tool       | Version  | Install                          |
|------------|----------|----------------------------------|
| Python     | ≥ 3.11   | [python.org](https://python.org) |
| Node.js    | ≥ 18     | [nodejs.org](https://nodejs.org) |
| npm        | ≥ 9      | Bundled with Node.js             |
| Git LFS    | any      | `brew install git-lfs`           |

---

## 1. Clone the Repository

```bash
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute
git lfs pull   # download large data files
```

---

## 2. Environment Variables

### Backend — `backend/.env`

Create `backend/.env` with:

```env
GEMINI_API_KEY=<your-google-gemini-api-key>
MAPBOX_TOKEN=<your-mapbox-access-token>
NEXT_PUBLIC_API_URL=http://localhost:8000/
OTP_BASE_URL=http://localhost:8080
```

> [!TIP]
> Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).
> Get a free Mapbox token at [mapbox.com](https://account.mapbox.com/access-tokens/).

### Frontend — `frontend/.env.local`

Create `frontend/.env.local` with:

```env
NEXT_PUBLIC_MAPBOX_TOKEN=<your-mapbox-access-token>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 3. Backend Setup

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Upgrade Gemini SDK (required for AI chatbot)
pip install --upgrade google-generativeai
```

### Key Python Packages

| Package              | Purpose                         |
|----------------------|---------------------------------|
| `fastapi`            | API framework                   |
| `uvicorn`            | ASGI server                     |
| `google-generativeai`| Gemini AI chatbot               |
| `scikit-learn`       | ML delay prediction             |
| `xgboost`            | ML model engine                 |
| `pandas`             | Data processing                 |
| `httpx`              | Async HTTP client               |

---

## 4. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### Key Frontend Packages

| Package       | Purpose                    |
|---------------|----------------------------|
| `next`        | React framework (v14)      |
| `react`       | UI library                 |
| `mapbox-gl`   | Interactive map rendering  |
| `lucide-react`| Icon library               |

---

## 5. Run the Application

Open **two terminal windows**:

### Terminal 1 — Backend (port 8000)

```bash
source .venv/bin/activate
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     GTFS loaded: 9388 stops
INFO:     ML model loaded successfully
INFO:     Application startup complete.
```

### Terminal 2 — Frontend (port 3000)

```bash
cd frontend
npm run dev
```

You should see:

```
▲ Next.js 14.x
- Local: http://localhost:3000
```

### Open the App

Navigate to **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 6. Verify Everything Works

### Quick Health Checks

```bash
# Backend API
curl http://localhost:8000/api/alerts

# AI Chatbot
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "history": []}'

# Frontend
curl -s http://localhost:3000 | head -5
```

### What to Expect in the UI

| Feature              | Location                                   |
|----------------------|--------------------------------------------|
| Route Planner        | Left sidebar — enter origin & destination  |
| Map                  | Main area — Mapbox interactive map         |
| AI Chat              | Blue chat bubble (bottom-right corner)     |
| Transit Alerts       | Sidebar alerts section                     |
| Live Vehicles        | Map markers (auto-updating)                |
| Delay Predictions    | Route cards after searching                |
| Decision Matrix      | Below route cards — compares all options   |

---

## 7. Optional: OpenTripPlanner (Advanced Routing)

OTP provides multi-agency transit routing. It's **optional** — the app falls back to heuristic routing without it.

```bash
docker compose up -d
```

This starts OTP on port 8080 using GTFS data in `backend/data/otp/`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **"AI backend" error in chat** | Check `GEMINI_API_KEY` is valid. Free tier has daily limits — quota resets daily. |
| **Map not loading** | Verify `NEXT_PUBLIC_MAPBOX_TOKEN` in `frontend/.env.local`. |
| **Backend won't start** | Ensure virtual environment is activated: `source .venv/bin/activate` |
| **Port already in use** | Kill the process: `lsof -ti:8000 \| xargs kill -9` |
| **`git-lfs` errors on pull** | Install git-lfs: `brew install git-lfs && git lfs install` |
| **Module not found errors** | Reinstall deps: `pip install -r backend/requirements.txt` |

---

## Project Structure

```
CTRLHACKDEL-Fluxroute/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── routes.py          # API endpoints
│   │   ├── gemini_agent.py    # AI chatbot (Gemini)
│   │   ├── route_engine.py    # Route generation logic
│   │   ├── ml_predictor.py    # ML delay prediction
│   │   ├── gtfs_parser.py     # GTFS data loader
│   │   └── gtfs_realtime.py   # Real-time transit polling
│   ├── ml/                    # Trained ML model files
│   ├── data/                  # GTFS & OTP data
│   ├── .env                   # Backend environment variables
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── app/                   # Next.js pages
│   ├── components/            # React components
│   │   ├── FluxMap.tsx        # Map with routes & vehicles
│   │   ├── RouteCards.tsx     # Route comparison cards
│   │   ├── DecisionMatrix.tsx # Side-by-side route matrix
│   │   └── DelayIndicator.tsx # ML delay risk display
│   ├── .env.local             # Frontend environment variables
│   └── package.json           # Node dependencies
├── docs/                      # Documentation
└── docker-compose.yml         # OTP container setup
```

---

## API Endpoints

| Method | Endpoint          | Description                     |
|--------|-------------------|---------------------------------|
| POST   | `/api/routes`     | Generate multimodal routes      |
| POST   | `/api/chat`       | AI chatbot conversation         |
| GET    | `/api/alerts`     | TTC service alerts              |
| GET    | `/api/vehicles`   | Live vehicle positions          |
| GET    | `/api/predict`    | ML delay predictions            |

---

*Built for CTRL+HACK+DEL Hackathon 2026*
