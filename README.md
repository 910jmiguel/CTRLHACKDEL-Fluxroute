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
│   │   ├── main.py              # FastAPI app, CORS, lifespan startup (OTP init)
│   │   ├── models.py            # Pydantic v2 models (API contract)
│   │   ├── routes.py            # API endpoints (+ /api/otp/status)
│   │   ├── route_engine.py      # Core routing: OTP-first with GTFS fallback
│   │   ├── otp_client.py        # Async OTP API client (plan_trip, health check)
│   │   ├── gtfs_parser.py       # TTC GTFS data loading and querying
│   │   ├── ml_predictor.py      # ML delay prediction (XGBoost + heuristic fallback)
│   │   ├── cost_calculator.py   # Multi-agency fares, gas, parking, PRESTO discounts
│   │   ├── weather.py           # Open-Meteo weather API integration
│   │   ├── road_closures.py     # City of Toronto road closure data
│   │   ├── gtfs_realtime.py     # Real-time vehicle positions and alerts
│   │   └── gemini_agent.py      # Gemini AI chat assistant with tool use
│   ├── ml/
│   │   ├── feature_engineering.py  # Feature extraction from delay CSV
│   │   ├── train_model.py          # XGBoost model training pipeline
│   │   └── delay_model.joblib      # Trained model (generated, gitignored)
│   ├── data/
│   │   ├── gtfs/                   # TTC GTFS static feed (auto-downloaded)
│   │   ├── otp/                    # OTP multi-agency data (see OTP Setup below)
│   │   │   ├── build-config.json   # OTP build configuration (CRITICAL)
│   │   │   ├── otp-config.json     # OTP routing parameters
│   │   │   ├── ttc.zip             # TTC GTFS (79 MB, Git LFS)
│   │   │   ├── gotransit.zip       # GO Transit GTFS (21 MB, Git LFS)
│   │   │   ├── yrt.zip             # York Region Transit GTFS (5 MB, Git LFS)
│   │   │   ├── miway.zip           # MiWay GTFS (7.6 MB, Git LFS)
│   │   │   ├── upexpress.zip       # UP Express GTFS (888 KB, Git LFS)
│   │   │   └── ontario.osm.pbf     # Ontario street network (890 MB, Git LFS)
│   │   └── ttc-subway-delay-data.csv
│   ├── scripts/
│   │   └── download_gtfs.sh        # GTFS download helper script
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout with fonts and metadata
│   │   ├── globals.css          # Tailwind + glassmorphism + Mapbox overrides
│   │   └── page.tsx             # Main page composing all components
│   ├── components/
│   │   ├── FluxMap.tsx          # Mapbox map with congestion-colored routes
│   │   ├── Sidebar.tsx          # Collapsible left panel
│   │   ├── RouteInput.tsx       # Origin/destination with geocoder autocomplete
│   │   ├── RouteCards.tsx       # Scrollable route option cards
│   │   ├── DecisionMatrix.tsx   # Fastest / Thrifty / Zen comparison
│   │   ├── DirectionSteps.tsx   # Turn-by-turn navigation instructions
│   │   ├── ChatAssistant.tsx    # Floating AI chat panel
│   │   ├── LiveAlerts.tsx       # Rotating alert banner
│   │   ├── DelayIndicator.tsx   # Green/yellow/red delay badge
│   │   ├── CostBreakdown.tsx    # Expandable cost details
│   │   └── LoadingOverlay.tsx   # Route calculation spinner
│   ├── lib/
│   │   ├── types.ts             # TypeScript interfaces (mirrors Pydantic models)
│   │   ├── constants.ts         # Config: tokens, colors, Toronto bounds
│   │   ├── api.ts               # Typed API client
│   │   └── mapUtils.ts          # Map drawing utilities (congestion coloring)
│   ├── hooks/
│   │   ├── useRoutes.ts         # Route fetching and selection state
│   │   ├── useChat.ts           # Chat message state management
│   │   └── useTimeBasedTheme.ts # Automatic map theme switching
│   └── package.json
├── docs/
│   ├── ROADMAP.md               # Project roadmap & status
│   ├── API_KEYS_SETUP.md        # API key setup instructions
│   ├── OTP_INTEGRATION.md       # OTP integration technical details
│   └── OTP_SETUP.md             # OTP setup guide (native + Docker)
├── docker-compose.yml           # OTP Docker service
├── .gitattributes               # Git LFS tracking for large files
├── .gitignore
├── README.md
└── CLAUDE.md                    # Project guide for Claude Code
```

---

## Prerequisites

- **Python 3.10+** (tested with 3.12)
- **Node.js 18+** (tested with 22.9.0)
- **npm** or **yarn**
- **Homebrew** (macOS only, for XGBoost dependency)
- **Java 17+** (for running OTP natively — not needed if using Docker)
- **Docker** (for running OTP via Docker — not needed if using Java)
- **Git LFS** (for pulling large data files)

### API Keys

| Key | Purpose | Required? |
|-----|---------|-----------|
| `MAPBOX_TOKEN` | Map display, route directions, geocoding | Yes |
| `GEMINI_API_KEY` | AI chat assistant (Google Gemini) | No (chat shows fallback) |
| `METROLINX_API_KEY` | GO Transit real-time data | No (mock data used) |

Get a free Mapbox token at [mapbox.com](https://account.mapbox.com/access-tokens/).
Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/apikey).

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute

# Pull large data files tracked by Git LFS
git lfs install
git lfs pull
```

### 2. Backend setup

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# macOS only: XGBoost requires OpenMP
brew install libomp

# Download TTC GTFS data for the local parser (if not already present)
cd backend/data/gtfs
curl -L -o gtfs.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"
unzip gtfs.zip && rm gtfs.zip
cd ../../..
```

### 3. Configure environment variables

Create `backend/.env`:
```env
GEMINI_API_KEY=your-gemini-api-key-here
MAPBOX_TOKEN=your-mapbox-token-here
METROLINX_API_KEY=your-metrolinx-api-key-here

# OTP Configuration
OTP_BASE_URL=http://localhost:8080/otp/routers/default
OTP_TIMEOUT=15.0
OTP_ENABLED=true
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_MAPBOX_TOKEN=your-mapbox-token-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

See `docs/API_KEYS_SETUP.md` for detailed instructions.

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

### 6. OpenTripPlanner setup (multi-agency routing)

OTP provides real multi-agency transit routing across TTC, GO Transit, YRT, MiWay, and UP Express. The GTFS data files and OSM street network are already included in the repo (pulled via Git LFS in step 1). You just need to download the OTP JAR and run it.

#### Option A: Native (recommended for development)

```bash
# Download OTP JAR from Maven Central (~174 MB, one-time download)
curl -L -o backend/data/otp/otp-2.5.0-shaded.jar \
  "https://repo1.maven.org/maven2/org/opentripplanner/otp/2.5.0/otp-2.5.0-shaded.jar"

# Verify the download
ls -lh backend/data/otp/otp-2.5.0-shaded.jar
# Should be ~174 MB

# Build the graph and start the server (takes ~15-20 minutes on first run)
cd backend/data/otp
java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve .
```

You'll know it's ready when you see `Grizzly server running`. OTP will be available at `http://localhost:8080`.

**Java not installed?**
```bash
# macOS
brew install openjdk@17
echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Ubuntu/Debian
sudo apt install openjdk-17-jre
```

#### Option B: Docker

```bash
# From project root
docker-compose up -d otp

# Monitor build progress (~15-20 minutes)
docker logs -f fluxroute-otp

# Wait for "Grizzly server running"
```

#### Verify OTP is working

```bash
# Check server responds
curl http://localhost:8080/otp/routers/default

# Test a multi-agency route (Finch Station to Union Station)
curl "http://localhost:8080/otp/routers/default/plan?fromPlace=43.7804,-79.4153&toPlace=43.6453,-79.3806&mode=TRANSIT,WALK"
```

> **Note:** The OTP JAR is not stored in git (too large). It's downloaded from Maven Central. The `.gitignore` excludes `*.jar` files. See `docs/OTP_SETUP.md` for troubleshooting.

### 7. Start the application

Open two (or three) terminals:

**Terminal 1 — OTP (if not already running):**
```bash
cd backend/data/otp
java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve .
```

**Terminal 2 — Backend:**
```bash
cd backend
python3 -m uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

**Terminal 3 — Frontend:**
```bash
cd frontend
npm run dev
```
The app will be available at `http://localhost:3000`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/routes` | Generate multimodal route options (OTP-first, GTFS fallback) |
| GET | `/api/predict-delay` | ML delay prediction for a TTC line |
| POST | `/api/chat` | Gemini AI chat assistant |
| GET | `/api/alerts` | Current service alerts |
| GET | `/api/vehicles` | Live vehicle positions |
| GET | `/api/transit-shape/{id}` | GeoJSON shape for a transit route |
| GET | `/api/nearby-stops` | Find stops near coordinates |
| GET | `/api/weather` | Current weather conditions |
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

---

## Team

Built by **Team FluxRoute** at CTRL+HACK+DEL 2025.
