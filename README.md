# FluxRoute — AI-Powered Multimodal GTA Transit Routing

FluxRoute is a smart transit routing application for the Greater Toronto Area that compares transit, driving, walking, and hybrid routes in real-time. It uses machine learning to predict TTC subway delays, provides cost and stress scoring, and includes an AI-powered chat assistant for personalized transit advice.

Built for **CTRL+HACK+DEL Hackathon 2025**.

---

## Features

- **Multi-Agency Transit Routing** — Routes across 5 GTA transit agencies (TTC, GO Transit, YRT, MiWay, UP Express) powered by OpenTripPlanner
- **Multimodal Route Comparison** — Side-by-side transit, driving, walking, and hybrid (park & ride) routes
- **ML Delay Predictions** — XGBoost model trained on TTC subway delay data predicts delay probability and expected wait times by line, time of day, and season
- **Decision Matrix** — Instantly compare routes by speed (Fastest), cost (Thrifty), and comfort (Zen)
- **Real-Time Traffic** — Mapbox congestion annotations color-code driving routes (green/yellow/orange/red) and factor into stress scoring
- **Live Vehicle Tracking** — Real-time TTC vehicle positions displayed on the map
- **Service Alerts** — Live TTC service alerts with rotating banner
- **Road Closure Awareness** — Active City of Toronto road closures factored into route stress scoring
- **Cost Breakdown** — Detailed fare, gas, and parking cost calculations with PRESTO co-fare discounts for multi-agency trips
- **Stress Scoring** — Each route gets a stress score based on transfers, delays, traffic, weather, and road closures
- **AI Chat Assistant** — Google Gemini-powered assistant with tool use for route planning, delay checks, and transit tips
- **Weather Integration** — Real-time weather from Open-Meteo API, factored into delay predictions and route scoring
- **Turn-by-Turn Directions** — Step-by-step navigation instructions for driving and walking segments
- **Time-Based Map Theme** — Map style automatically adapts to time of day (dawn, day, dusk, night)
- **Dark Theme UI** — Glassmorphism design with Mapbox dark-v11 map style

---

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.12)
- **Transit Routing:** OpenTripPlanner 2.5 (multi-agency graph routing)
- **ML:** XGBoost (classifier + regressor), scikit-learn
- **Data:** Multi-agency GTFS (TTC, GO Transit, YRT, MiWay, UP Express) + Ontario OSM street network
- **APIs:** Mapbox Directions (driving/walking + congestion), Open-Meteo Weather, Google Gemini, TTC GTFS-RT
- **Libraries:** pandas, httpx, joblib, protobuf, google-generativeai, polyline

### Frontend
- **Framework:** Next.js 14 (App Router, TypeScript)
- **Map:** Mapbox GL JS with dark-v11 style + congestion-colored route lines
- **Styling:** Tailwind CSS with custom glassmorphism theme
- **Icons:** Lucide React
- **State:** Custom React hooks (useRoutes, useChat, useTimeBasedTheme)

### Infrastructure
- **OTP Server:** OpenTripPlanner 2.5 (Docker or native JAR)
- **Data:** Git LFS for large GTFS/OSM files
- **Containerization:** Docker Compose for OTP service

---

## Project Structure

```
fluxroute/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, CORS, lifespan startup
│   │   ├── models.py                  # Pydantic v2 models (API contract)
│   │   ├── routes.py                  # API endpoints
│   │   ├── route_engine.py            # Core routing: OTP-first with GTFS fallback
│   │   ├── otp_client.py              # Async OTP API client (plan_trip, health check)
│   │   ├── gtfs_parser.py             # TTC GTFS data loading and querying
│   │   ├── gtfs_realtime.py           # Real-time vehicle positions and alerts
│   │   ├── transit_lines.py           # Transit line GeoJSON overlay data
│   │   ├── ml_predictor.py            # ML delay prediction (XGBoost + heuristic fallback)
│   │   ├── cost_calculator.py         # Multi-agency fares, gas, parking, PRESTO discounts
│   │   ├── weather.py                 # Open-Meteo weather API integration
│   │   ├── road_closures.py           # City of Toronto road closure data
│   │   ├── parking_data.py            # Parking location and cost data
│   │   ├── mapbox_navigation.py       # Mapbox Navigation API (turn-by-turn directions)
│   │   ├── navigation_service.py      # Navigation session management (WebSocket)
│   │   ├── route_builder_suggestions.py # Transit route suggestions for custom builder
│   │   └── gemini_agent.py            # Gemini AI chat assistant with tool use
│   ├── ml/
│   │   ├── train_model.py             # XGBoost model training pipeline
│   │   ├── feature_engineering.py     # Feature extraction from delay CSV
│   │   ├── evaluate_model.py          # Model evaluation metrics
│   │   ├── combine_all_data.py        # Multi-source data combiner
│   │   ├── enrich_weather_data.py     # Weather data enrichment for ML
│   │   └── delay_model.joblib         # Trained model (generated, gitignored)
│   ├── data/
│   │   ├── gtfs/                      # TTC GTFS static feed (see setup step 3)
│   │   ├── otp/                       # OTP multi-agency data (see docs/OTP_SETUP.md)
│   │   │   ├── build-config.json      # OTP build configuration
│   │   │   ├── otp-config.json        # OTP routing parameters
│   │   │   ├── ttc.zip                # TTC GTFS (79 MB, Git LFS)
│   │   │   ├── gotransit.zip          # GO Transit GTFS (21 MB, Git LFS)
│   │   │   ├── yrt.zip               # York Region Transit GTFS (5 MB, Git LFS)
│   │   │   ├── miway.zip             # MiWay GTFS (7.6 MB, Git LFS)
│   │   │   ├── upexpress.zip         # UP Express GTFS (888 KB, Git LFS)
│   │   │   └── ontario.osm.pbf       # Ontario street network (890 MB, Git LFS)
│   │   └── ttc-subway-delay-data.csv
│   ├── scripts/
│   │   └── download_gtfs.sh           # GTFS download helper script
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout with fonts and metadata
│   │   ├── page.tsx                   # Landing page
│   │   ├── map/page.tsx               # Map application (main app)
│   │   └── globals.css                # Tailwind + glassmorphism + Mapbox overrides
│   ├── components/
│   │   ├── FluxMap.tsx                # Mapbox map with congestion-colored routes
│   │   ├── TopBar.tsx                 # Top navigation bar with search inputs
│   │   ├── RoutePanel.tsx             # Route results panel
│   │   ├── RoutePills.tsx             # Mode filter pills (transit/driving/walking)
│   │   ├── RouteInput.tsx             # Origin/destination with geocoder autocomplete
│   │   ├── RouteCards.tsx             # Scrollable route option cards
│   │   ├── RouteComparisonTable.tsx   # Side-by-side route comparison
│   │   ├── DecisionMatrix.tsx         # Fastest / Thrifty / Zen comparison
│   │   ├── JourneyTimeline.tsx        # Visual timeline with depart/arrive times
│   │   ├── LineStripDiagram.tsx       # Transit line strip map visualization
│   │   ├── DirectionSteps.tsx         # Turn-by-turn navigation instructions
│   │   ├── NavigationView.tsx         # Active navigation UI
│   │   ├── ChatAssistant.tsx          # Floating AI chat panel
│   │   ├── AlertsPanel.tsx            # Service alerts detail panel
│   │   ├── AlertsBell.tsx             # Alert notification bell icon
│   │   ├── DashboardView.tsx          # Dashboard overview
│   │   ├── BottomSheet.tsx            # Mobile-friendly bottom sheet
│   │   ├── RouteBuilderModal.tsx      # Custom route builder modal
│   │   ├── SegmentEditor.tsx          # Route segment editor
│   │   ├── IsochronePanel.tsx         # Isochrone analysis panel
│   │   ├── MapLayersControl.tsx       # Map layer toggle controls
│   │   ├── ThemeToggle.tsx            # Light/dark theme toggle
│   │   ├── DelayIndicator.tsx         # Green/yellow/red delay badge
│   │   ├── CostBreakdown.tsx          # Expandable cost details
│   │   ├── LoadingOverlay.tsx         # Route calculation spinner
│   │   ├── Sidebar.tsx                # Legacy collapsible left panel
│   │   └── LiveAlerts.tsx             # Legacy rotating alert banner
│   ├── lib/
│   │   ├── types.ts                   # TypeScript interfaces (mirrors Pydantic models)
│   │   ├── constants.ts               # Config: tokens, colors, Toronto bounds
│   │   ├── api.ts                     # Typed API client
│   │   └── mapUtils.ts               # Map drawing utilities (congestion coloring)
│   ├── hooks/
│   │   ├── useRoutes.ts               # Route fetching and selection state
│   │   ├── useChat.ts                 # Chat message state management
│   │   ├── useNavigation.ts           # Turn-by-turn navigation state
│   │   ├── useCustomRoute.ts          # Custom route builder state
│   │   ├── useMediaQuery.ts           # Responsive breakpoint detection
│   │   └── useTimeBasedTheme.ts       # Automatic map theme switching
│   └── package.json
├── docs/
│   ├── FULL_SETUP.md              # Complete setup guide (start here)
│   ├── API_KEYS_SETUP.md          # API key setup instructions
│   ├── OTP_SETUP.md               # OTP setup guide (native + Docker)
│   ├── OTP_INTEGRATION.md         # OTP integration technical details
│   └── ROADMAP.md                 # Project roadmap & status
├── docker-compose.yml             # OTP Docker service
├── .gitattributes                 # Git LFS tracking for large files
├── .gitignore
├── README.md
└── CLAUDE.md                      # Project guide for Claude Code
```

---

## Quick Start

> For step-by-step instructions with explanations, see **[docs/FULL_SETUP.md](docs/FULL_SETUP.md)**.

### Prerequisites

- Python 3.10+, Node.js 18+, Git LFS
- [Mapbox token](https://account.mapbox.com/access-tokens/) (free)
- [Gemini API key](https://aistudio.google.com/apikey) (free, optional — for AI chat)
- Java 17+ or Docker (optional — for multi-agency OTP routing)

### Setup

```bash
# 1. Clone & pull data
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute
git lfs install && git lfs pull

# 2. Backend
pip install -r backend/requirements.txt
brew install libomp   # macOS only

# 3. Download TTC GTFS data (CRITICAL — without this, transit lines render as straight lines)
cd backend/data/gtfs
curl -L -o gtfs.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"
unzip gtfs.zip && rm gtfs.zip
cd ../../..

# 4. Configure environment variables
#    backend/.env     → MAPBOX_TOKEN, GEMINI_API_KEY
#    frontend/.env.local → NEXT_PUBLIC_MAPBOX_TOKEN, NEXT_PUBLIC_API_URL
#    See docs/API_KEYS_SETUP.md for details

# 5. Frontend
cd frontend && npm install && cd ..
```

### Run

```bash
# Terminal 1 — Backend
cd backend && python3 -m uvicorn app.main:app --reload
# API at http://localhost:8000

# Terminal 2 — Frontend
cd frontend && npm run dev
# Landing page at http://localhost:3000
# Map app at http://localhost:3000/map
```

### Optional: OTP multi-agency routing

OTP enables routing across TTC, GO Transit, YRT, MiWay, and UP Express. Without it, only TTC routing is available. See **[docs/OTP_SETUP.md](docs/OTP_SETUP.md)** for setup instructions.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/routes` | Generate multimodal route options (OTP-first, GTFS fallback) |
| GET | `/api/predict-delay` | ML delay prediction for a TTC line |
| POST | `/api/chat` | Gemini AI chat assistant |
| GET | `/api/alerts` | Current service alerts |
| GET | `/api/vehicles` | Live vehicle positions |
| GET | `/api/transit-lines` | Transit line overlay GeoJSON |
| GET | `/api/transit-shape/{id}` | GeoJSON shape for a transit route |
| GET | `/api/nearby-stops` | Find stops near coordinates |
| GET | `/api/stops/search` | Search stops by name |
| GET | `/api/line-stops/{line_id}` | Ordered stops for a specific line |
| GET | `/api/weather` | Current weather conditions |
| GET | `/api/road-closures` | Active road closures from Toronto Open Data |
| POST | `/api/custom-route` | Calculate a user-defined custom route |
| POST | `/api/custom-route-v2` | Custom route (v2, suggestion-based segments) |
| POST | `/api/suggest-transit-routes` | AI-suggested transit routes for origin/destination |
| POST | `/api/navigation-route` | Turn-by-turn navigation with voice/banner instructions |
| POST | `/api/navigation-session` | Create navigation session (returns WebSocket URL) |
| WS | `/api/ws/navigation/{id}` | Real-time navigation updates via WebSocket |
| POST | `/api/optimize-route` | Optimize multi-stop route ordering |
| POST | `/api/isochrone` | Isochrone reachability analysis |
| GET | `/api/otp/status` | OTP server availability check |
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

### Example: Check OTP status

```bash
curl http://localhost:8000/api/otp/status
# {"available": true, "message": "Multi-agency routing active"}
```

---

## Architecture

```
Browser (localhost:3000)
    |
    v
Next.js 14 Frontend (TypeScript, Mapbox GL JS)
    |  HTTP requests
    v
FastAPI Backend (localhost:8000)
    |
    |-- Mapbox Directions API (driving/walking + congestion annotations)
    |-- Open-Meteo Weather API (real-time weather)
    |-- Google Gemini API (AI chat with tool use)
    |-- TTC GTFS-RT (live vehicle positions + alerts)
    |-- XGBoost ML Model (delay prediction)
    |-- City of Toronto (road closures)
    |
    v
OpenTripPlanner (localhost:8080)
    |  Reads GTFS + OSM data, builds routing graph
    v
5 Transit Agencies: TTC, GO Transit, YRT, MiWay, UP Express
```

The backend's route engine queries OTP first for transit routes. If OTP is unavailable, it falls back to the local GTFS-based nearest-stop heuristic. Driving and walking routes always use Mapbox Directions. The frontend requires **zero changes** — the API contract is identical regardless of routing backend.

---

## Resilience

FluxRoute is designed to work even when external services are unavailable:

| Failure | Fallback |
|---------|----------|
| OTP server down | Local GTFS nearest-stop routing (TTC only) |
| GTFS files missing | Hardcoded TTC subway station data (75 stations) |
| Delay CSV unavailable | Heuristic predictor based on real TTC delay patterns |
| GTFS-RT feeds down | Mock vehicle positions along subway lines + sample alerts |
| Mapbox API unavailable | Straight-line geometry with haversine distance estimates |
| Mapbox congestion unavailable | Rush-hour heuristic (7-9am, 4-7pm) for stress scoring |
| Gemini API unavailable | Chat shows friendly error; all other features work |
| Weather API down | Default Toronto winter conditions |
| Road closure API down | Routes generated without closure data |
| GTFS `shapes.txt` missing | Transit lines render as straight lines (see [setup step 3](docs/FULL_SETUP.md#step-3-download-ttc-gtfs-data)) |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Transit lines look straight, not curved | Missing GTFS data (`shapes.txt`) | Download GTFS data — see [setup step 3](docs/FULL_SETUP.md#step-3-download-ttc-gtfs-data) |
| Map is blank / doesn't load | Missing Mapbox token in frontend | Set `NEXT_PUBLIC_MAPBOX_TOKEN` in `frontend/.env.local` |
| Driving routes are straight lines | Missing Mapbox token in backend | Set `MAPBOX_TOKEN` in `backend/.env` |
| AI chat doesn't respond | Missing Gemini API key | Set `GEMINI_API_KEY` in `backend/.env` |
| `xgboost` install fails on macOS | Missing OpenMP library | Run `brew install libomp` |
| OTP not detected by backend | OTP not running when backend started | Start OTP first, then restart backend |

For a full troubleshooting guide, see **[docs/FULL_SETUP.md](docs/FULL_SETUP.md#troubleshooting)**.

---

## Team

Built by **Team FluxRoute** at CTRL+HACK+DEL 2025.
