# FluxRoute — AI-Powered Multimodal GTA Transit Routing

FluxRoute is a smart transit routing application for the Greater Toronto Area that compares transit, driving, walking, and hybrid routes in real-time. It uses machine learning to predict TTC subway delays, provides cost and stress scoring, and includes an AI-powered chat assistant for personalized transit advice.

Built for **CTRL+HACK+DEL Hackathon 2025**.

---

## Features

- **Multimodal Route Comparison** — Get side-by-side transit, driving, walking, and hybrid (park & ride) routes with real TTC GTFS data
- **ML Delay Predictions** — XGBoost model trained on TTC subway delay data predicts delay probability and expected wait times by line, time of day, and season
- **Decision Matrix** — Instantly compare routes by speed (Fastest), cost (Thrifty), and comfort (Zen)
- **Live Vehicle Tracking** — Real-time TTC vehicle positions displayed on the map
- **Service Alerts** — Live TTC service alerts with rotating banner
- **Cost Breakdown** — Detailed fare, gas, and parking cost calculations for every route
- **Stress Scoring** — Each route gets a stress score based on transfers, delays, traffic, and weather
- **AI Chat Assistant** — Claude-powered assistant with tool use for route planning, delay checks, and transit tips
- **Weather Integration** — Real-time weather from Open-Meteo API, factored into delay predictions and route scoring
- **Dark Theme UI** — Glassmorphism design with Mapbox dark-v11 map style

---

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.12)
- **ML:** XGBoost (classifier + regressor), scikit-learn
- **Data:** Real TTC GTFS static feed (9,388 stops, 230 routes, 437K shape points)
- **APIs:** Mapbox Directions, Open-Meteo Weather, Anthropic Claude, TTC GTFS-RT
- **Libraries:** pandas, httpx, joblib, protobuf

### Frontend
- **Framework:** Next.js 14 (App Router, TypeScript)
- **Map:** Mapbox GL JS with dark-v11 style
- **Styling:** Tailwind CSS with custom glassmorphism theme
- **Icons:** Lucide React
- **State:** Custom React hooks (useRoutes, useChat)

---

## Project Structure

```
fluxroute/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, lifespan startup
│   │   ├── models.py            # Pydantic v2 models (API contract)
│   │   ├── routes.py            # API endpoints
│   │   ├── route_engine.py      # Core routing logic (transit/drive/walk/hybrid)
│   │   ├── gtfs_parser.py       # TTC GTFS data loading and querying
│   │   ├── ml_predictor.py      # ML delay prediction (XGBoost + heuristic fallback)
│   │   ├── cost_calculator.py   # Fare, gas, parking cost calculations
│   │   ├── weather.py           # Open-Meteo weather API integration
│   │   ├── gtfs_realtime.py     # Real-time vehicle positions and alerts
│   │   └── claude_agent.py      # AI chat assistant with tool use
│   ├── ml/
│   │   ├── feature_engineering.py  # Feature extraction from delay CSV
│   │   ├── train_model.py          # XGBoost model training pipeline
│   │   └── delay_model.joblib      # Trained model (generated)
│   ├── data/
│   │   ├── gtfs/                   # TTC GTFS static feed (auto-downloaded)
│   │   └── ttc-subway-delay-data.csv
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout with fonts and metadata
│   │   ├── globals.css          # Tailwind + glassmorphism + Mapbox overrides
│   │   └── page.tsx             # Main page composing all components
│   ├── components/
│   │   ├── FluxMap.tsx          # Full-screen Mapbox map with route visualization
│   │   ├── Sidebar.tsx          # Collapsible left panel
│   │   ├── RouteInput.tsx       # Origin/destination with geocoder autocomplete
│   │   ├── RouteCards.tsx       # Scrollable route option cards
│   │   ├── DecisionMatrix.tsx   # Fastest / Thrifty / Zen comparison
│   │   ├── ChatAssistant.tsx    # Floating AI chat panel
│   │   ├── LiveAlerts.tsx       # Rotating alert banner
│   │   ├── DelayIndicator.tsx   # Green/yellow/red delay badge
│   │   ├── CostBreakdown.tsx    # Expandable cost details
│   │   └── LoadingOverlay.tsx   # Route calculation spinner
│   ├── lib/
│   │   ├── types.ts             # TypeScript interfaces (mirrors Pydantic models)
│   │   ├── constants.ts         # Config: tokens, colors, Toronto bounds
│   │   ├── api.ts               # Typed API client
│   │   └── mapUtils.ts          # Map drawing utilities
│   ├── hooks/
│   │   ├── useRoutes.ts         # Route fetching and selection state
│   │   └── useChat.ts           # Chat message state management
│   └── package.json
├── .gitignore
└── README.md
```

---

## Prerequisites

- **Python 3.10+** (tested with 3.12)
- **Node.js 18+** (tested with 22.9.0)
- **npm** or **yarn**
- **Homebrew** (macOS only, for XGBoost dependency)

### API Keys (optional but recommended)

| Key | Purpose | Required? |
|-----|---------|-----------|
| `MAPBOX_TOKEN` | Map display and route directions | Yes for map |
| `ANTHROPIC_API_KEY` | AI chat assistant | No (chat shows fallback message) |
| `METROLINX_API_KEY` | GO Transit real-time data | No (mock data used) |

Get a free Mapbox token at [mapbox.com](https://account.mapbox.com/access-tokens/).

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute
```

### 2. Backend setup

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# macOS only: XGBoost requires OpenMP
brew install libomp

# Download TTC GTFS data (if not already present)
cd backend/data/gtfs
curl -L -o gtfs.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"
unzip gtfs.zip && rm gtfs.zip
cd ../../..
```

### 3. Configure environment variables

Create `backend/.env`:
```env
ANTHROPIC_API_KEY=your-anthropic-api-key-here
MAPBOX_TOKEN=your-mapbox-token-here
METROLINX_API_KEY=your-metrolinx-api-key-here
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_MAPBOX_TOKEN=your-mapbox-token-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Train the ML model (optional)

```bash
cd backend
python3 -m ml.train_model
```

This trains an XGBoost delay prediction model on TTC subway delay data. If you skip this step, the app automatically uses a heuristic fallback based on real TTC delay patterns.

### 5. Frontend setup

```bash
cd frontend
npm install
```

### 6. Start the application

Open two terminals:

**Terminal 1 — Backend:**
```bash
cd backend
python3 -m uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
The app will be available at `http://localhost:3000`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/routes` | Generate multimodal route options |
| GET | `/api/predict-delay` | ML delay prediction for a TTC line |
| POST | `/api/chat` | AI chat assistant |
| GET | `/api/alerts` | Current service alerts |
| GET | `/api/vehicles` | Live vehicle positions |
| GET | `/api/transit-shape/{id}` | GeoJSON shape for a transit route |
| GET | `/api/nearby-stops` | Find stops near coordinates |
| GET | `/api/weather` | Current weather conditions |
| GET | `/api/health` | Health check |

### Example: Get routes

```bash
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "origin": {"lat": 43.7804, "lng": -79.4153},
    "destination": {"lat": 43.6453, "lng": -79.3806}
  }'
```

### Example: Predict delay

```bash
curl "http://localhost:8000/api/predict-delay?line=Line+1&hour=8&day_of_week=0"
```

---

## Resilience

FluxRoute is designed to work even when external services are unavailable:

| Failure | Fallback |
|---------|----------|
| GTFS files missing | Hardcoded TTC subway station data (75 stations with real coordinates) |
| Delay CSV unavailable | Heuristic predictor based on real TTC delay patterns |
| GTFS-RT feeds down | Mock vehicle positions along subway lines + sample alerts |
| Mapbox API unavailable | Straight-line geometry with haversine distance estimates |
| Claude API unavailable | Chat shows friendly error; all other features work |
| Weather API down | Default Toronto winter conditions |

---

## Team

Built by **Team FluxRoute** at CTRL+HACK+DEL 2025.
