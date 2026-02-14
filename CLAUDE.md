<<<<<<< HEAD
# FluxRoute — Project Guide for Claude

## Project Overview

FluxRoute is an **AI-powered multimodal transit routing application** for the Greater Toronto Area (GTA) built for the CTRL+HACK+DEL 2025 Hackathon. It compares transit, driving, walking, and hybrid routes in real-time using machine learning to predict TTC subway delays and provides an AI chat assistant for personalized transit advice.

**Core Value Proposition:**
- Multimodal route comparison (transit/driving/walking/hybrid)
- ML-based TTC subway delay predictions using XGBoost
- Real-time GTFS data integration (TTC schedules + live vehicle positions)
- Decision matrix for optimizing by speed (Fastest), cost (Thrifty), or comfort (Zen)
- AI chat assistant powered by Google Gemini (formerly Claude/Anthropic)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────┐         ┌──────────────────────────────────┐
│   Next.js 14    │  HTTP   │        FastAPI Backend          │
│   Frontend      │◄────────┤   Python 3.12 + Uvicorn         │
│  (TypeScript)   │         │                                  │
└─────────────────┘         │  ┌────────────────────────────┐  │
                            │  │   GTFS Data (TTC)          │  │
┌─────────────────┐         │  │   - 9,388 stops            │  │
│   Mapbox API    │◄────────┤  │   - 230 routes             │  │
│  - Directions   │         │  │   - 437K shape points      │  │
│  - Geocoding    │         │  └────────────────────────────┘  │
│  - Map Display  │         │                                  │
└─────────────────┘         │  ┌────────────────────────────┐  │
                            │  │   XGBoost ML Model         │  │
┌─────────────────┐         │  │   Delay Prediction         │  │
│  Google Gemini  │◄────────┤  └────────────────────────────┘  │
│   AI Chat API   │         │                                  │
└─────────────────┘         │  ┌────────────────────────────┐  │
                            │  │   GTFS-RT Realtime Feeds   │  │
┌─────────────────┐         │  │   - Vehicle positions      │  │
│  Open-Meteo     │◄────────┤  │   - Service alerts         │  │
│  Weather API    │         │  └────────────────────────────┘  │
└─────────────────┘         └──────────────────────────────────┘
```

### Data Flow

1. **User Input** → Frontend geocodes origin/destination via Mapbox
2. **Route Request** → Backend `/api/routes` endpoint
3. **Route Generation**:
   - Transit routes: Query GTFS data for stops/schedules + Mapbox directions
   - Driving routes: Mapbox Directions API
   - Walking routes: Mapbox Directions API
   - Hybrid routes: Park-and-ride combinations
4. **Delay Prediction** → XGBoost model predicts delays for transit segments
5. **Cost Calculation** → Fares (TTC/GO), gas, parking costs computed
6. **Stress Scoring** → Weighted scoring based on transfers, delays, weather, traffic
7. **Response** → Ranked routes returned to frontend
8. **Map Rendering** → Mapbox GL JS renders routes with live vehicle overlays

---

## Tech Stack

### Backend (Python 3.12)
- **Framework:** FastAPI with Pydantic v2 models
- **Server:** Uvicorn (ASGI)
- **ML:** XGBoost, scikit-learn, pandas, joblib
- **APIs:**
  - Mapbox Directions API (routing)
  - Google Gemini API (AI chat)
  - Open-Meteo API (weather)
  - TTC GTFS-RT (real-time transit)
- **Data Processing:** pandas, httpx, protobuf (GTFS-RT), gtfs-realtime-bindings
- **Environment:** python-dotenv for config

### Frontend (Next.js 14 + TypeScript)
- **Framework:** Next.js 14 (App Router, React 18)
- **Map:** Mapbox GL JS 3.18.1
- **Geocoding:** @mapbox/mapbox-gl-geocoder
- **Styling:** Tailwind CSS 3.4+ with glassmorphism theme
- **Icons:** Lucide React
- **State Management:** Custom React hooks (`useRoutes`, `useChat`)
- **Type Safety:** TypeScript 5+ with strict type checking

### Data Sources
- **TTC GTFS Static Feed** (9,388 stops, 230 routes, 437K shape points)
- **TTC Subway Delay CSV** (historical delay data for ML training)
- **TTC GTFS-RT Feeds** (vehicle positions + service alerts)
- **Mapbox Directions API** (driving/walking routes)
- **Open-Meteo Weather API** (real-time weather conditions)

---

## Project Structure

```
fluxroute/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS + lifespan startup
│   │   ├── routes.py            # API route handlers
│   │   ├── models.py            # Pydantic v2 data models (API contract)
│   │   ├── route_engine.py      # Core multimodal routing logic
│   │   ├── gtfs_parser.py       # GTFS data loading + querying
│   │   ├── ml_predictor.py      # XGBoost delay prediction + heuristic fallback
│   │   ├── cost_calculator.py   # TTC/GO fares, gas, parking calculations
│   │   ├── weather.py           # Open-Meteo weather integration
│   │   ├── gtfs_realtime.py     # GTFS-RT vehicle positions + alerts poller
│   │   └── claude_agent.py      # Gemini AI chat assistant with tools
│   ├── ml/
│   │   ├── feature_engineering.py  # Delay CSV → ML features
│   │   ├── train_model.py          # XGBoost training pipeline
│   │   └── delay_model.joblib      # Trained model (gitignored, auto-generated)
│   ├── data/
│   │   ├── gtfs/                   # TTC GTFS static feed (gitignored, auto-downloaded)
│   │   └── ttc-subway-delay-data.csv  # Historical delay data
│   ├── requirements.txt
│   └── .env                        # API keys (gitignored)
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout with fonts + metadata
│   │   ├── globals.css          # Tailwind + glassmorphism + Mapbox overrides
│   │   └── page.tsx             # Main page (client component)
│   ├── components/
│   │   ├── FluxMap.tsx          # Mapbox map with route visualization
│   │   ├── Sidebar.tsx          # Collapsible left panel
│   │   ├── RouteInput.tsx       # Geocoder-powered origin/destination input
│   │   ├── RouteCards.tsx       # Scrollable route option cards
│   │   ├── DecisionMatrix.tsx   # Fastest/Thrifty/Zen comparison
│   │   ├── ChatAssistant.tsx    # AI chat floating panel
│   │   ├── LiveAlerts.tsx       # Rotating service alert banner
│   │   ├── DelayIndicator.tsx   # Green/yellow/red delay badge
│   │   ├── CostBreakdown.tsx    # Expandable cost details
│   │   └── LoadingOverlay.tsx   # Route calculation spinner
│   ├── lib/
│   │   ├── types.ts             # TypeScript interfaces (mirrors Pydantic models)
│   │   ├── constants.ts         # Config (tokens, colors, Toronto bounds)
│   │   ├── api.ts               # Typed API client
│   │   └── mapUtils.ts          # Map drawing utilities
│   ├── hooks/
│   │   ├── useRoutes.ts         # Route fetching + selection state
│   │   └── useChat.ts           # Chat message state management
│   ├── package.json
│   └── .env.local               # Frontend config (gitignored)
│
├── .gitignore
├── README.md
├── API_KEYS_SETUP.md
└── CLAUDE.md                    # This file
```

---

## Key Modules and Responsibilities

### Backend Modules

#### `app/main.py`
- FastAPI application initialization
- CORS middleware for localhost:3000
- Lifespan management:
  - Loads GTFS data on startup
  - Initializes ML predictor (XGBoost or heuristic fallback)
  - Starts GTFS-RT realtime poller background task
  - Cleans up on shutdown
- **Global State:** `app_state` dict stores GTFS data, ML predictor, vehicles, alerts, poller task

#### `app/routes.py`
- API route handlers
- **Endpoints:**
  - `POST /api/routes` — Generate multimodal routes
  - `GET /api/predict-delay` — ML delay prediction
  - `POST /api/chat` — AI chat assistant
  - `GET /api/alerts` — Service alerts
  - `GET /api/vehicles` — Live vehicle positions
  - `GET /api/transit-shape/{id}` — GeoJSON shape for transit route
  - `GET /api/nearby-stops` — Find stops near coordinates
  - `GET /api/weather` — Current weather
  - `GET /api/health` — Health check

#### `app/models.py`
- **Pydantic v2 models** (API contract):
  - `RouteMode` enum: transit, driving, walking, cycling, hybrid
  - `Coordinate`, `RouteSegment`, `RouteOption`, `RouteRequest`, `RouteResponse`
  - `CostBreakdown`, `DelayInfo`, `DelayPredictionRequest/Response`
  - `ChatMessage`, `ChatRequest`, `ChatResponse`
  - `ServiceAlert`, `VehiclePosition`
- **Type safety:** All API requests/responses are validated via Pydantic

#### `app/route_engine.py`
- **Core routing logic:**
  - Generates transit, driving, walking, and hybrid route options
  - Queries GTFS for nearest stops, schedules, shapes
  - Calls Mapbox Directions API for driving/walking routes
  - Computes stress scores, delay predictions, cost breakdowns
  - Returns ranked `RouteOption` list
- **Fallback behavior:** If GTFS unavailable, uses hardcoded TTC subway stations

#### `app/gtfs_parser.py`
- Loads TTC GTFS static feed (stops.txt, routes.txt, trips.txt, shapes.txt, stop_times.txt)
- Provides query functions:
  - `find_nearest_stops()` — Haversine distance search
  - `get_route_shape()` — GeoJSON LineString for route visualization
  - `load_gtfs_data()` — Loads all GTFS files into memory (pandas DataFrames)
- **Fallback:** If GTFS files missing, returns hardcoded TTC subway stations (75 stations)

#### `app/ml_predictor.py`
- **DelayPredictor class** with two modes:
  1. **ML mode:** Loads XGBoost model from `ml/delay_model.joblib`
  2. **Heuristic mode:** Rule-based delay estimates (if model file missing)
- **Prediction inputs:** line, station, hour, day_of_week, month
- **Returns:** `{delay_probability, expected_delay_minutes, confidence, contributing_factors}`
- **Heuristic logic:**
  - Line 1 (Yonge-University): Higher delays during rush hour
  - Line 2 (Bloor-Danforth): Moderate delays
  - Line 3 (Scarborough): Low delays
  - Line 4 (Sheppard): Minimal delays
  - Rush hour penalty (7-9am, 4-7pm)
  - Weekend reduction

#### `app/cost_calculator.py`
- Calculates fare, gas, and parking costs
- **TTC Fares:** $3.35 single, $3.00 PRESTO
- **GO Transit Fares:** Distance-based ($4-$12)
- **Gas Cost:** Distance × fuel consumption × gas price
- **Parking:** Downtown ($15-$30), suburbs ($5-$10)
- Returns `CostBreakdown` model

#### `app/weather.py`
- Fetches current weather from Open-Meteo API
- **Returns:** temperature, precipitation, wind speed, conditions
- **Fallback:** Default Toronto winter conditions if API fails
- **Usage:** Factored into delay predictions and stress scoring

#### `app/gtfs_realtime.py`
- Background poller for TTC GTFS-RT feeds:
  - Vehicle positions feed
  - Service alerts feed
- **Polling interval:** 15 seconds
- **Mock fallback:** If GTFS-RT unavailable, generates mock subway vehicle positions and sample alerts
- Updates `app_state["vehicles"]` and `app_state["alerts"]`

#### `app/claude_agent.py`
- **AI chat assistant** powered by **Google Gemini** (note: originally designed for Claude/Anthropic, migrated to Gemini)
- **Tool use:** Can call route prediction, delay checking, and transit info tools
- **Context-aware:** Receives user location, current routes, weather
- **Returns:** `ChatResponse` with message + suggested actions

#### `ml/train_model.py`
- XGBoost model training pipeline
- **Input:** `data/ttc-subway-delay-data.csv`
- **Features:** line, station, hour, day_of_week, month, season
- **Target:** delay occurrence (classifier) + delay duration (regressor)
- **Output:** `ml/delay_model.joblib` (gitignored)
- **Run manually:** `cd backend && python3 -m ml.train_model`

#### `ml/feature_engineering.py`
- Extracts features from TTC delay CSV
- Creates time-based features (hour, day_of_week, season)
- Encodes categorical variables (line, station)

---

### Frontend Modules

#### `app/page.tsx`
- **Main page component** (client-side)
- Manages origin/destination state
- Polls vehicle positions every 15 seconds
- Composes all UI components:
  - `LiveAlerts` (top banner)
  - `Sidebar` (left panel)
  - `FluxMap` (main map)
  - `ChatAssistant` (floating chat)
  - `LoadingOverlay` (during route fetch)

#### `components/FluxMap.tsx`
- Mapbox GL JS map component
- **Map style:** `mapbox://styles/mapbox/dark-v11`
- **Rendering:**
  - Route polylines with mode-specific colors
  - Origin/destination markers
  - Live vehicle markers (pulsing circles)
  - Transit stop markers
- **Interactions:** Click routes to select, zoom to fit bounds

#### `components/Sidebar.tsx`
- Collapsible left panel (toggleable)
- Contains:
  - `RouteInput` (geocoder)
  - `DecisionMatrix` (Fastest/Thrifty/Zen)
  - `RouteCards` (scrollable route options)

#### `components/RouteInput.tsx`
- Mapbox Geocoder integration
- Origin/destination input fields
- **Geocoding scope:** Toronto bounding box (43.58-43.85°N, -79.65--79.12°W)
- Triggers route search on submission

#### `components/RouteCards.tsx`
- Displays route options as cards
- Shows: mode icon, duration, cost, delay badge, summary
- Click to select route (highlights on map)
- Expandable `CostBreakdown` component

#### `components/DecisionMatrix.tsx`
- Compares routes by 3 criteria:
  - **Fastest:** Minimum `total_duration_min`
  - **Thrifty:** Minimum `cost.total`
  - **Zen:** Minimum `stress_score`
- Displays winner for each category with metric

#### `components/ChatAssistant.tsx`
- Floating AI chat panel (bottom-right)
- Uses `useChat` hook for message state
- Sends messages to `POST /api/chat`
- Displays suggested actions as clickable chips

#### `components/LiveAlerts.tsx`
- Rotating service alert banner (top of page)
- Fetches alerts from `GET /api/alerts`
- **Colors:** info (blue), warning (yellow), error (red)
- Auto-rotates every 5 seconds if multiple alerts

#### `components/DelayIndicator.tsx`
- Badge showing delay probability
- **Colors:**
  - Green (< 30%): Low delay
  - Yellow (30-60%): Moderate delay
  - Red (> 60%): High delay

#### `lib/types.ts`
- **TypeScript interfaces** mirroring Pydantic models
- Ensures type safety between frontend/backend
- **Key types:** `RouteOption`, `RouteSegment`, `Coordinate`, `ChatMessage`, `VehiclePosition`, etc.

#### `lib/api.ts`
- Typed API client with fetch wrappers
- **Functions:**
  - `fetchRoutes(origin, destination)` → `RouteResponse`
  - `sendChatMessage(message, history, context)` → `ChatResponse`
  - `getAlerts()` → `{alerts: ServiceAlert[]}`
  - `getVehicles()` → `{vehicles: VehiclePosition[]}`
  - `predictDelay(params)` → `DelayPredictionResponse`

#### `lib/constants.ts`
- Configuration constants:
  - Mapbox token
  - API base URL
  - Route mode colors
  - Toronto bounding box
  - Default map center (43.6532, -79.3832)

#### `lib/mapUtils.ts`
- Map drawing utilities:
  - `drawRoute(map, route)` — Add route polyline layers
  - `addMarker(map, coord, type)` — Add origin/destination markers
  - `fitBounds(map, coords)` — Zoom to fit route

#### `hooks/useRoutes.ts`
- React hook for route state management
- **State:** routes, selectedRoute, loading, error
- **Actions:** fetchRoutes(), selectRoute()
- Calls `lib/api.fetchRoutes()`

#### `hooks/useChat.ts`
- React hook for chat state management
- **State:** messages, loading
- **Actions:** sendMessage(), clearMessages()
- Calls `lib/api.sendChatMessage()`

---

## Development Patterns and Conventions

### Backend Conventions
- **Pydantic v2 models** for all API contracts (strict type validation)
- **FastAPI dependency injection** via lifespan events (loads data once on startup)
- **Graceful degradation:** All external services have fallback behavior
- **Logging:** Use `logging.getLogger("fluxroute.*")` for all modules
- **Error handling:** Return user-friendly messages, never expose internal errors
- **Async/await:** All route handlers are async for I/O operations (HTTP requests)
- **Global state:** Access via `from app.main import app_state` (dict shared across requests)

### Frontend Conventions
- **Client components:** All interactive components use `"use client"` directive
- **TypeScript strict mode:** Enabled in `tsconfig.json`
- **Tailwind utility classes:** Prefer utility classes over custom CSS
- **Glassmorphism theme:** `backdrop-blur-md bg-white/10` for panels
- **Responsive design:** Mobile-first approach (though primarily desktop-focused)
- **Error boundaries:** Graceful error handling with fallback UI
- **API client abstraction:** All backend calls go through `lib/api.ts` (never raw fetch in components)

### Naming Conventions
- **Backend:** snake_case for variables/functions, PascalCase for classes
- **Frontend:** camelCase for variables/functions, PascalCase for components
- **Files:** kebab-case for multi-word files (e.g., `route-engine.py`)
- **API endpoints:** `/api/kebab-case` pattern

### Code Quality Standards
- **Type safety:** Strict typing in both Python (Pydantic) and TypeScript
- **No magic numbers:** Use named constants (e.g., `TTC_FARE = 3.35`)
- **DRY principle:** Extract reusable logic into utility functions
- **Single Responsibility:** Each module has one clear purpose
- **Documentation:** Docstrings for all public functions

---

## API Contract (Pydantic Models)

### Core Models

```python
# RouteMode enum
RouteMode = "transit" | "driving" | "walking" | "cycling" | "hybrid"

# Request
RouteRequest {
    origin: Coordinate
    destination: Coordinate
    modes?: RouteMode[]  # defaults to all modes
    departure_time?: str
}

# Response
RouteResponse {
    routes: RouteOption[]
    origin: Coordinate
    destination: Coordinate
}

# Route option
RouteOption {
    id: str
    label: str  # "Fastest", "Thrifty", "Zen", etc.
    mode: RouteMode
    segments: RouteSegment[]
    total_distance_km: float
    total_duration_min: float
    cost: CostBreakdown
    delay_info: DelayInfo
    stress_score: float  # 0.0 (zen) to 1.0 (max stress)
    departure_time?: str
    arrival_time?: str
    summary: str
}

# Route segment
RouteSegment {
    mode: RouteMode
    geometry: dict  # GeoJSON LineString
    distance_km: float
    duration_min: float
    instructions?: str
    transit_line?: str
    transit_route_id?: str
    color?: str
}

# Cost breakdown
CostBreakdown {
    fare: float
    gas: float
    parking: float
    total: float
}

# Delay info
DelayInfo {
    probability: float  # 0.0 to 1.0
    expected_minutes: float
    confidence: float  # 0.0 to 1.0
    factors: str[]
}
```

### Chat Models

```python
ChatRequest {
    message: str
    history: ChatMessage[]
    context?: dict  # current routes, location, etc.
}

ChatResponse {
    message: str
    suggested_actions: str[]
}

ChatMessage {
    role: "user" | "assistant"
    content: str
}
```

---

## Environment Variables

### Backend `.env`
```bash
GEMINI_API_KEY=your-gemini-api-key-here
MAPBOX_TOKEN=pk.your-mapbox-token-here
METROLINX_API_KEY=optional-metrolinx-key
```

### Frontend `.env.local`
```bash
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your-mapbox-token-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Security:**
- `.env` and `.env.local` are gitignored
- Mapbox token (`pk.*`) is public-safe (can be exposed in frontend)
- Gemini API key must stay server-side only

---

## Common Development Tasks

### Setup
```bash
# Clone repo
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute

# Backend setup
pip install -r backend/requirements.txt
brew install libomp  # macOS only (XGBoost dependency)

# Download TTC GTFS data
cd backend/data/gtfs
curl -L -o gtfs.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"
unzip gtfs.zip && rm gtfs.zip
cd ../../..

# Train ML model (optional)
cd backend
python3 -m ml.train_model

# Frontend setup
cd frontend
npm install

# Configure .env files (see API_KEYS_SETUP.md)
```

### Run Development Servers
```bash
# Terminal 1 — Backend
cd backend
python3 -m uvicorn app.main:app --reload
# API available at http://localhost:8000

# Terminal 2 — Frontend
cd frontend
npm run dev
# App available at http://localhost:3000
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/api/health

# Get routes
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin": {"lat": 43.7804, "lng": -79.4153}, "destination": {"lat": 43.6453, "lng": -79.3806}}'

# Predict delay
curl "http://localhost:8000/api/predict-delay?line=Line+1&hour=8&day_of_week=0"

# Get alerts
curl http://localhost:8000/api/alerts

# Get vehicles
curl http://localhost:8000/api/vehicles
```

### Build for Production
```bash
# Frontend
cd frontend
npm run build
npm start

# Backend (use gunicorn or deploy to cloud)
cd backend
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## Important Notes and Gotchas

### Resilience and Fallback Behavior
FluxRoute is designed to work even when external services fail:

| Failure Scenario | Fallback Behavior |
|------------------|-------------------|
| GTFS files missing | Hardcoded TTC subway stations (75 stations) |
| Delay CSV unavailable | Heuristic delay predictor (rule-based) |
| GTFS-RT feeds down | Mock vehicle positions + sample alerts |
| Mapbox API fails | Straight-line geometry with haversine distance |
| Gemini API unavailable | Chat returns friendly error message |
| Weather API down | Default Toronto winter conditions |

### Data Dependencies
- **GTFS data** is gitignored (large files) — must be downloaded on setup
- **ML model** (`delay_model.joblib`) is gitignored — auto-generated or falls back to heuristic
- **Delay CSV** (`ttc-subway-delay-data.csv`) is committed (historical data)

### API Rate Limits
- **Mapbox Free Tier:** 50k map loads/month, 100k directions requests/month
- **Gemini API:** Free tier is rate-limited (check Google AI Studio for limits)
- **Open-Meteo:** No API key required, generous free tier
- **TTC GTFS-RT:** Public feeds, no authentication required

### Performance Considerations
- **GTFS data loading:** Happens once on startup (in-memory pandas DataFrames)
- **Route calculation:** Typically 1-3 seconds (depends on Mapbox API latency)
- **ML prediction:** < 10ms (in-memory model)
- **GTFS-RT polling:** 15-second interval (background task)
- **Frontend vehicle polling:** 15-second interval (client-side)

### Known Limitations
- **Transit routing:** Uses nearest-stop heuristic (not full graph search)
- **Schedule accuracy:** GTFS static data (no real-time schedule adjustments)
- **GO Transit:** Mock data only (requires Metrolinx API key for real data)
- **Hybrid routes:** Simplified park-and-ride logic (doesn't consider parking availability)
- **Stress scoring:** Heuristic-based (not ML-derived)

### Debugging Tips
- **GTFS not loading:** Check `backend/data/gtfs/` directory exists with `.txt` files
- **ML model not loading:** Run `python3 -m ml.train_model` or check `delay_model.joblib` exists
- **Map not rendering:** Verify `NEXT_PUBLIC_MAPBOX_TOKEN` in `frontend/.env.local`
- **CORS errors:** Ensure frontend runs on `localhost:3000` (hardcoded in backend CORS)
- **Chat not working:** Check `GEMINI_API_KEY` in `backend/.env` and backend logs

### AI Integration Notes
- **Originally designed for Anthropic Claude API** but migrated to **Google Gemini**
- File `claude_agent.py` name is legacy (now uses Gemini)
- API key env var changed from `ANTHROPIC_API_KEY` to `GEMINI_API_KEY`
- See `API_KEYS_SETUP.md` for updated Gemini setup instructions

---

## Key Dependencies

### Backend Critical Dependencies
- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `pydantic` — Data validation
- `pandas` — GTFS data processing
- `xgboost` — ML delay prediction
- `scikit-learn` — Feature engineering
- `httpx` — Async HTTP client (Mapbox, weather, GTFS-RT)
- `google-generativeai` — Gemini AI chat
- `gtfs-realtime-bindings` — GTFS-RT protobuf parsing
- `joblib` — ML model serialization

### Frontend Critical Dependencies
- `next` — React framework
- `react` — UI library
- `mapbox-gl` — Map rendering
- `@mapbox/mapbox-gl-geocoder` — Location search
- `lucide-react` — Icons
- `tailwindcss` — Styling

---

## Decision Matrix Logic

The decision matrix compares routes by three criteria:

1. **Fastest:** Minimum `total_duration_min`
2. **Thrifty:** Minimum `cost.total`
3. **Zen:** Minimum `stress_score`

### Stress Score Calculation
Weighted factors:
- **Transfers:** 0.1 per transfer
- **Delay probability:** 0.3 × `delay_info.probability`
- **Weather penalty:** 0.2 if precipitation > 5mm
- **Traffic penalty:** 0.1 if rush hour (7-9am, 4-7pm)
- **Walking distance:** 0.05 per km
- **Driving stress:** 0.15 (base for driving routes)

**Range:** 0.0 (perfectly zen) to 1.0 (maximum stress)

---

## Future Enhancement Ideas
- Real-time schedule updates (integrate TTC GTFS-RT trip updates)
- Full graph-based transit routing (Dijkstra/A* on GTFS graph)
- GO Transit real-time data (requires Metrolinx API key)
- User preferences (avoid transfers, prefer subway, etc.)
- Historical route performance tracking
- Multi-stop trip planning
- Bike-share integration (Bike Share Toronto)
- Accessibility routing (wheelchair-accessible routes)
- Carbon footprint comparison

---

## Team and Hackathon Context
Built for **CTRL+HACK+DEL 2025 Hackathon** by **Team FluxRoute**.

This is a hackathon project — code prioritizes functionality and demo-ability over production-readiness. Expect some technical debt, hardcoded values, and incomplete error handling.

---

## Summary for Claude

When working on this project:
1. **Always validate types** — Use Pydantic models in backend, TypeScript interfaces in frontend
2. **Respect fallback behavior** — Don't break graceful degradation
3. **Test API integration** — Use curl or Postman to test backend endpoints
4. **Check environment variables** — Many features require API keys
5. **Understand data flow** — GTFS data → route engine → ML prediction → cost calculation → response
6. **Follow conventions** — snake_case (Python), camelCase (TypeScript), PascalCase (classes/components)
7. **Read `API_KEYS_SETUP.md`** for detailed API key setup instructions
8. **Check `README.md`** for user-facing setup documentation

This project demonstrates:
- Multimodal transit routing
- Real-world ML integration (XGBoost delay prediction)
- Real-time data feeds (GTFS-RT)
- AI-powered chat assistant (Gemini with tool use)
- Production-quality API design (FastAPI + Pydantic)
- Modern React patterns (hooks, TypeScript, Next.js App Router)
- Glassmorphism UI design

The codebase is well-structured, type-safe, and resilient. Have fun building on it!
=======
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FluxRoute — AI-powered multimodal transit routing app for the Greater Toronto Area. FastAPI backend + Next.js 14 frontend with Mapbox GL maps and XGBoost ML delay predictions for TTC subway lines.

## Commands

### Backend
```bash
# Install deps (macOS needs: brew install libomp for XGBoost)
pip install -r backend/requirements.txt

# Run dev server
cd backend && python3 -m uvicorn app.main:app --reload

# Train ML model (optional — heuristic fallback works without it)
cd backend && python3 -m ml.train_model
```

### Frontend
```bash
cd frontend && npm install
cd frontend && npm run dev      # dev server on :3000
cd frontend && npm run build    # production build
cd frontend && npm run lint     # ESLint
```

### Environment
Both `backend/.env` and `frontend/.env.local` are gitignored. Required keys:
- `MAPBOX_TOKEN` / `NEXT_PUBLIC_MAPBOX_TOKEN` — same `pk.` token in both files
- `ANTHROPIC_API_KEY` — `sk-ant-` key in backend only
- `METROLINX_API_KEY` — optional, mock data fallback exists

## Architecture

### Backend (`/backend/app/`)
- **main.py** — FastAPI app with lifespan context manager that loads GTFS data, ML model, and starts real-time polling on startup
- **routes.py** — All API endpoints under `/api` prefix
- **route_engine.py** — Core routing logic generating transit/driving/walking/hybrid options with segment-level detail
- **models.py** — Pydantic v2 models defining the full API contract (RouteRequest → RouteResponse with RouteOption[], etc.)
- **gtfs_parser.py** — Loads TTC GTFS static feed; falls back to 75 hardcoded subway stations if files missing
- **ml_predictor.py** — XGBoost delay prediction with heuristic fallback using real TTC line patterns (rush hour, seasonal, weather modifiers)
- **claude_agent.py** — Anthropic Claude chat with tool use (route planning, delay checks)
- **gtfs_realtime.py** — Polls TTC/Metrolinx GTFS-RT feeds for vehicle positions and service alerts
- **cost_calculator.py** — TTC fare ($3.35), gas ($0.15/km), parking cost estimation
- **weather.py** — Open-Meteo API integration

### ML Pipeline (`/backend/ml/`)
- **feature_engineering.py** — Extracts temporal features (hour, day, rush hour, weekend) from TTC delay CSV with dynamic column detection
- **train_model.py** — Trains XGBoost classifier (delay probability) + regressor (expected minutes), saves as `delay_model.joblib`

### Frontend (`/frontend/`)
Next.js 14 App Router, TypeScript strict mode, Tailwind CSS, dark glassmorphism theme.

- **app/page.tsx** — Main page composing all components
- **components/** — FluxMap (Mapbox), Sidebar, RouteInput (geocoder), RouteCards, DecisionMatrix (fastest/thrifty/zen), ChatAssistant, LiveAlerts, DelayIndicator, CostBreakdown
- **lib/types.ts** — TypeScript interfaces mirroring backend Pydantic models
- **lib/api.ts** — Typed fetch wrapper for all backend endpoints
- **lib/constants.ts** — Config: API URL, Mapbox token, Toronto bounds, TTC line colors
- **lib/mapUtils.ts** — Route polyline drawing, markers, vehicle position updates
- **hooks/** — useRoutes (route fetching/selection state), useChat (message state)

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/routes` | Generate multimodal routes |
| GET | `/api/predict-delay` | ML delay prediction for TTC line |
| POST | `/api/chat` | Claude AI assistant |
| GET | `/api/alerts` | Cached TTC service alerts |
| GET | `/api/vehicles` | Cached vehicle positions |
| GET | `/api/transit-shape/{route_id}` | GeoJSON shape for route |
| GET | `/api/nearby-stops` | Stops near coordinates |
| GET | `/api/weather` | Current conditions |
| GET | `/api/health` | Health check |

### Data Flow
1. Frontend sends origin/destination coords → `/api/routes`
2. Backend route_engine generates up to 3 options using GTFS data + Mapbox Directions API
3. Each option gets ML delay prediction, cost calculation, stress score
4. Frontend renders routes on Mapbox map with polylines, shows cards with decision matrix
5. Real-time: vehicle positions polled every 15s, alerts rotate in banner

### Resilience
Every external dependency has a fallback: GTFS → hardcoded stations, ML model → heuristic predictor, Mapbox → haversine straight lines, weather → Toronto winter defaults, GTFS-RT → mock vehicles/alerts.

## Notes
- Use `python3` not `python` (macOS)
- GTFS data (`backend/data/gtfs/`) is gitignored — downloaded from Toronto Open Data CKAN on first setup
- `*.joblib` models are gitignored — regenerated via `python3 -m ml.train_model`
- Frontend path alias: `@/*` maps to project root
- TTC line normalization in ml_predictor handles many formats ("Line 1", "YU", "Yonge-University" → "1")
>>>>>>> a4ea520bb53c56a1d8ed5d90c3730003f209b3b5
