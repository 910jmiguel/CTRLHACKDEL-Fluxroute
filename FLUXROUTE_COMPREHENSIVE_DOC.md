# FluxRoute — Comprehensive Project Documentation

**Project:** FluxRoute — AI-Powered Multimodal GTA Transit Routing  
**Hackathon:** CTRL+HACK+DEL 2025  
**Team:** Team FluxRoute  
**Last Updated:** February 16, 2026

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Features Overview](#features-overview)
3. [System Architecture](#system-architecture)
4. [Tech Stack](#tech-stack)
5. [Backend Deep Dive](#backend-deep-dive)
6. [Frontend Deep Dive](#frontend-deep-dive)
7. [Machine Learning Pipeline](#machine-learning-pipeline)
8. [AI Chat Assistant](#ai-chat-assistant)
9. [Data Sources & Integrations](#data-sources--integrations)
10. [API Reference](#api-reference)
11. [Resilience & Fallback Strategy](#resilience--fallback-strategy)
12. [Project Structure](#project-structure)
13. [Setup & Installation](#setup--installation)
14. [Roadmap & Future Enhancements](#roadmap--future-enhancements)
15. [Decision Log](#decision-log)

---

## Executive Summary

FluxRoute is a full-stack, production-grade multimodal transit routing application for the Greater Toronto Area (GTA). It empowers commuters to compare transit, driving, walking, and hybrid (park & ride) routes in real-time, leveraging machine learning for TTC delay predictions, live traffic congestion overlays, and a conversational AI assistant powered by Google Gemini.

The platform integrates **5 GTA transit agencies** (TTC, GO Transit, YRT, MiWay, UP Express) through OpenTripPlanner, combines real-time data from Mapbox, GTFS-RT feeds, Open-Meteo weather, and City of Toronto road closures, and renders everything on an immersive Mapbox GL JS map with glassmorphism-themed dark UI.

### Key Differentiators

- **True multimodal comparison** — side-by-side transit, driving, walking, and hybrid routes with cost, time, and stress scoring
- **ML-powered delay prediction** — XGBoost model trained on historical TTC subway delay data
- **Intelligent hybrid routing** — park & ride suggestions with parking data, service disruption awareness, and strategic station selection
- **AI conversational assistant** — Google Gemini with tool use for natural-language route queries
- **Graceful degradation** — every external dependency has a fallback, so the app never breaks

---

## Features Overview

### Core Routing

| Feature | Description |
|---------|-------------|
| **Multi-Agency Transit Routing** | Routes across 5 GTA agencies via OpenTripPlanner with GTFS fallback |
| **Driving Routes** | Real road-following directions via Mapbox Directions API (driving-traffic profile) |
| **Walking Routes** | Pedestrian directions with step-by-step instructions |
| **Hybrid (Park & Ride)** | Drive to a strategically-chosen station, take transit downtown |
| **Decision Matrix** | Instantly compare routes by **Fastest** (speed), **Thrifty** (cost), and **Zen** (comfort) |
| **Turn-by-Turn Directions** | Step-by-step navigation instructions for driving and walking segments |

### Real-Time Data

| Feature | Description |
|---------|-------------|
| **Live Traffic Congestion** | Mapbox congestion annotations color-code driving routes (green/yellow/orange/red) |
| **Live Vehicle Tracking** | Real-time TTC vehicle positions on the map (15-second polling) |
| **Service Alerts** | Live TTC service alerts displayed in a rotating banner with severity indicators |
| **Road Closures** | Active City of Toronto road closures displayed on map and factored into stress scoring |
| **Weather Integration** | Real-time weather from Open-Meteo, affecting delay predictions and route scoring |

### Intelligence

| Feature | Description |
|---------|-------------|
| **ML Delay Predictions** | XGBoost model predicts delay probability and expected wait times by line, time, and season |
| **Stress Scoring** | Composite score based on transfers, delays, traffic congestion, weather, and road closures |
| **Cost Breakdown** | Detailed fare, gas, and parking cost calculations with PRESTO co-fare discounts |
| **AI Chat Assistant** | Google Gemini-powered assistant for route planning, delay checks, and transit tips |

### User Experience

| Feature | Description |
|---------|-------------|
| **Glassmorphism Dark UI** | Premium dark theme with glass-effect panels and backdrop blur |
| **Time-Based Map Theme** | Map style automatically adapts to dawn, day, dusk, and night |
| **Intro Zoom Animation** | Cinematic zoom from space into the CN Tower on page load |
| **Transit Line Overlay** | Always-visible subway/GO train/LRT lines with hover tooltips |
| **Map Layers Control** | Toggle transit lines, traffic, vehicles, road closures per line |
| **Isochrone Visualization** | "How far can I go in X minutes?" polygons on the map |
| **Responsive Design** | Desktop and tablet-friendly with collapsible sidebar |
| **Route Builder** | Custom route creation with segment editor and AI suggestions |
| **Turn-by-Turn Navigation** | Full navigation mode with user location tracking and re-center button |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (localhost:3000)                      │
│                                                                 │
│  Next.js 14 Frontend (TypeScript, React 18, Mapbox GL JS)       │
│  ┌───────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────┐ │
│  │  FluxMap   │ │ TopBar   │ │ RouteCards │ │ ChatAssistant    │ │
│  │ (Mapbox)   │ │ (Search) │ │ (Results)  │ │ (Gemini)         │ │
│  └───────────┘ └──────────┘ └────────────┘ └──────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / WebSocket
                         v
┌─────────────────────────────────────────────────────────────────┐
│               FastAPI Backend (localhost:8000)                    │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Route Engine │  │ ML Predictor │  │  Gemini Agent          │  │
│  │ (1887 lines) │  │  (XGBoost)   │  │  (tool use, 7 tools)  │  │
│  └──────┬──────┘  └──────────────┘  └────────────────────────┘  │
│         │                                                        │
│  ┌──────┴──────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ OTP Client  │  │ GTFS Parser  │  │ Navigation Service     │  │
│  │ (async HTTP)│  │ (9388 stops) │  │ (WebSocket, sessions)  │  │
│  └──────┬──────┘  └──────────────┘  └────────────────────────┘  │
│         │                                                        │
│  ┌──────┴──────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │Cost Calc    │  │GTFS-RT Poller│  │ Transit Lines          │  │
│  │(multi-fare) │  │(15s polling) │  │ (map overlay GeoJSON)  │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Weather     │  │Road Closures │  │ Parking Data           │  │
│  │(Open-Meteo) │  │(Toronto Open)│  │ (GO/TTC stations)      │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└────────┬──────────────┬──────────────┬───────────────────────────┘
         │              │              │
         v              v              v
  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐
  │   OTP    │  │ Mapbox APIs  │  │  External Data       │
  │ (8080)   │  │ (Directions, │  │  - Open-Meteo        │
  │ 5 GTFS  │  │  Geocoding)  │  │  - TTC GTFS-RT       │
  │ + OSM    │  │              │  │  - Toronto Open Data  │
  └──────────┘  └──────────────┘  │  - Google Gemini     │
                                  └──────────────────────┘
```

### Data Flow — Route Generation

1. User enters origin/destination in the geocoder search bar
2. Frontend sends `POST /api/routes` with coordinates
3. Backend route engine fires parallel requests:
   - **Transit:** OTP plan query (falls back to GTFS nearest-stop heuristic)
   - **Driving:** Mapbox Directions `driving-traffic` with congestion annotations
   - **Walking:** Mapbox Directions `walking` profile
   - **Hybrid:** Scores park-and-ride station candidates, queries OTP + Mapbox
4. Each route gets enriched with:
   - ML delay prediction (XGBoost or heuristic)
   - Cost breakdown (fares, gas, parking, PRESTO discounts)
   - Stress score (transfers, delays, congestion, weather, closures)
   - Congestion-colored geometry sub-segments
   - GTFS-RT schedule enrichment (next departures, trip updates)
5. Frontend renders congestion-colored polylines on the map, route cards in the sidebar, and decision matrix comparison

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.12 | Runtime |
| **FastAPI** | Latest | API framework with async support |
| **Uvicorn** | Latest | ASGI server |
| **OpenTripPlanner** | 2.5 | Multi-agency transit graph routing |
| **XGBoost** | Latest | ML delay prediction classifier + regressor |
| **scikit-learn** | Latest | Feature engineering, model evaluation |
| **httpx** | Latest | Async HTTP client (connection pooling, IPv4) |
| **Pydantic** | v2 | Request/response validation (40+ models) |
| **pandas** | Latest | GTFS data processing |
| **protobuf** | Latest | GTFS-RT feed parsing |
| **google-generativeai** | Latest | Gemini AI chat integration |
| **polyline** | Latest | OTP encoded polyline decoding |
| **joblib** | Latest | ML model serialization |
| **python-dotenv** | Latest | Environment variable management |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 14 (App Router) | React framework with SSR |
| **React** | 18 | UI component library |
| **TypeScript** | 5.x | Type-safe development |
| **Mapbox GL JS** | 3.18 | Interactive map rendering |
| **Tailwind CSS** | 3.4 | Utility-first CSS with glassmorphism theme |
| **Lucide React** | Latest | Icon library |
| **mapbox-gl** | Latest | Map SDK |

### Infrastructure

| Technology | Purpose |
|-----------|---------|
| **Docker Compose** | OTP service containerization |
| **Git LFS** | Large file storage (GTFS zips, OSM PBF) |
| **Java 17+** | OTP JAR runtime (native mode) |

---

## Backend Deep Dive

The backend consists of **18 Python modules** in `backend/app/`, orchestrated by a FastAPI lifespan that initializes all services at startup.

### Module Inventory

| Module | Lines | Size | Purpose |
|--------|-------|------|---------|
| `route_engine.py` | 1,887 | 76.6 KB | Core routing logic — OTP-first transit, Mapbox driving/walking, hybrid park-and-ride |
| `gtfs_parser.py` | ~1,000 | 46.1 KB | TTC GTFS static data loading and querying (9,388 stops, 230 routes) |
| `route_builder_suggestions.py` | ~800 | 35.6 KB | AI-powered transit route suggestions for the custom route builder |
| `gemini_agent.py` | 526 | 22.8 KB | Google Gemini AI chat with 7 tool definitions and execution |
| `routes.py` | 652 | 21.6 KB | API endpoint definitions (25 endpoints) |
| `gtfs_realtime.py` | ~400 | 17.6 KB | GTFS-RT polling for vehicle positions + service alerts |
| `transit_lines.py` | ~350 | 15.1 KB | Transit line geometries + station GeoJSON for map overlay |
| `mapbox_navigation.py` | ~300 | 13.4 KB | Mapbox Navigation API integration for turn-by-turn |
| `otp_client.py` | ~300 | 13.3 KB | Async OTP HTTP client with health checks and polyline decoding |
| `parking_data.py` | ~300 | 12.9 KB | Parking information for GO and TTC stations |
| `ml_predictor.py` | ~250 | 11.3 KB | ML delay prediction with XGBoost + heuristic fallback |
| `navigation_service.py` | ~250 | 10.7 KB | WebSocket-based real-time navigation session management |
| `models.py` | 354 | 10.8 KB | 40+ Pydantic v2 data models (full API contract) |
| `main.py` | 118 | 4.0 KB | FastAPI app, CORS, lifespan startup |
| `weather.py` | ~80 | 3.5 KB | Open-Meteo weather API integration |
| `cost_calculator.py` | ~80 | 3.4 KB | Multi-agency fare, gas, parking, PRESTO discount calculations |
| `road_closures.py` | ~50 | 2.2 KB | City of Toronto road closure data fetching |

### Route Engine (`route_engine.py`) — The Heart of FluxRoute

The 1,887-line route engine is the core module that orchestrates all routing logic. Key functions:

| Function | Purpose |
|----------|---------|
| `generate_routes()` | Entry point — generates 3-4 route options for origin/destination |
| `_generate_single_route()` | Generates one route option for a given mode |
| `_generate_transit_route()` | Full transit routing with walking to/from stations, GTFS-RT enrichment |
| `_generate_hybrid_routes()` | Generates 1-3 hybrid (drive + transit) routes via scored station candidates |
| `_score_park_and_ride_candidate()` | Scores stations by strategic value (betweenness, drive ratio, parking, disruption, frequency) |
| `_enrich_transit_segment()` | Enriches segments with GTFS-RT trip updates, static schedules, next departures |
| `_cached_mapbox_directions()` | Mapbox Directions with per-request caching |
| `_split_geometry_by_congestion()` | Splits LineStrings into sub-segments by Mapbox congestion level |
| `_check_line_disruption()` | Checks alerts for line disruptions (avoids disrupted routes) |
| `_compute_congestion_summary()` | Produces human-readable traffic labels from congestion arrays |

**Hybrid Routing Algorithm:**
1. Collects all rapid transit stations (no bus stops) within range
2. Filters for stations with parking data
3. Checks for active service disruptions on each line
4. Scores candidates on: geometric betweenness, drive-ratio sweet spot (20-40%), parking availability, disruption status, next departure proximity, GO Transit preference
5. Returns top 1-3 hybrid routes sorted by score

### Startup Lifecycle (`main.py`)

On server start, the lifespan initializer:
1. Loads **GTFS static data** — 9,388 stops, 230 routes
2. Loads **ML delay predictor** — XGBoost model or heuristic fallback
3. Checks **OTP health** — enables multi-agency routing if available
4. Creates **shared httpx client** — IPv4-forced, connection-pooled (50 max, 20 keepalive)
5. Fetches **transit line overlay** — GeoJSON geometries + stations for always-visible map layer
6. Initializes **navigation session manager** — for WebSocket-based real-time navigation
7. Starts **GTFS-RT poller** — 15-second polling for vehicle positions + alerts

### Pydantic Models (`models.py`)

40+ strictly typed models define the API contract:

| Model | Purpose |
|-------|---------|
| `RouteOption` | Complete route with segments, cost, delay, stress score, traffic summary |
| `RouteSegment` | Individual leg (walk, drive, transit) with geometry, schedule, and GTFS-RT data |
| `CostBreakdown` | Fare, gas, parking, total |
| `DelayInfo` | Probability, expected minutes, confidence, contributing factors |
| `ParkingInfo` | Station parking rates, capacity, agency |
| `ServiceAlert` | Route-level alerts with severity |
| `VehiclePosition` | Live vehicle lat/lng, bearing, speed |
| `NavigationInstruction` | Voice/banner text, maneuver type, lane guidance |
| `TransitRouteSuggestion` | AI-suggested transit routes for custom route builder |

---

## Frontend Deep Dive

The frontend is a **Next.js 14** application with the App Router, built with TypeScript and styled using Tailwind CSS with a custom glassmorphism theme.

### Component Inventory (27 components)

#### Map & Visualization

| Component | Size | Purpose |
|-----------|------|---------|
| `FluxMap.tsx` | 25.6 KB | Core Mapbox GL map — route rendering, congestion coloring, transit overlay, vehicle markers, navigation mode, traffic layers, road closures, isochrones |
| `MapLayersControl.tsx` | 6.3 KB | Toggle visibility of transit lines (Line 1/2/4/5/6, streetcars), traffic, vehicles |
| `NavigationView.tsx` | 8.1 KB | Turn-by-turn navigation UI with user location tracking, re-center, and compass |

#### Route Display & Comparison

| Component | Size | Purpose |
|-----------|------|---------|
| `RouteCards.tsx` | 12.0 KB | Scrollable route option cards with duration, cost, delay badge, and summary |
| `RoutePanel.tsx` | 5.7 KB | Selected route detail panel |
| `RoutePills.tsx` | 7.3 KB | Pill-style route mode selector |
| `DecisionMatrix.tsx` | 5.9 KB | Fastest / Thrifty / Zen comparison table |
| `RouteComparisonTable.tsx` | 8.2 KB | Detailed multi-route comparison table |
| `JourneyTimeline.tsx` | 15.1 KB | Visual timeline showing each segment of a multimodal route |
| `DirectionSteps.tsx` | 2.5 KB | Step-by-step navigation instructions list |
| `CostBreakdown.tsx` | 1.6 KB | Expandable cost details (fare, gas, parking) |
| `DelayIndicator.tsx` | 3.0 KB | Green/yellow/red delay probability badge |
| `LineStripDiagram.tsx` | 3.0 KB | Visual diagram of stops along a transit line |

#### Route Building

| Component | Size | Purpose |
|-----------|------|---------|
| `RouteBuilderModal.tsx` | 21.2 KB | Custom route creation modal with AI suggestions |
| `SegmentEditor.tsx` | 15.9 KB | Drag-and-drop segment editor for custom routes |

#### Search & Input

| Component | Size | Purpose |
|-----------|------|---------|
| `TopBar.tsx` | 17.0 KB | Top navigation bar with origin/destination search, alerts, theme toggle |
| `RouteInput.tsx` | 14.5 KB | Mapbox Geocoder-powered origin/destination input with swap + locate buttons |

#### Layout & UI

| Component | Size | Purpose |
|-----------|------|---------|
| `Sidebar.tsx` | 6.3 KB | Collapsible left panel for route cards and details |
| `BottomSheet.tsx` | 4.3 KB | Mobile-friendly bottom sheet for route info |
| `DashboardView.tsx` | 6.4 KB | Dashboard overview with system status |
| `LoadingOverlay.tsx` | 1.0 KB | Route calculation spinner overlay |
| `ThemeToggle.tsx` | 0.7 KB | Light/dark theme toggle button |
| `IsochronePanel.tsx` | 5.8 KB | Isochrone ("how far in X minutes?") control panel |

#### Alerts & Real-Time

| Component | Size | Purpose |
|-----------|------|---------|
| `LiveAlerts.tsx` | 4.2 KB | Rotating service alerts banner |
| `AlertsBell.tsx` | 0.9 KB | Alert notification bell icon with badge count |
| `AlertsPanel.tsx` | 6.8 KB | Expandable alerts panel with per-line filtering and severity icons |
| `ChatAssistant.tsx` | 5.3 KB | Floating AI chat panel with message history and suggested actions |

### Custom Hooks (6 hooks)

| Hook | Size | Purpose |
|------|------|---------|
| `useRoutes.ts` | 2.0 KB | Route fetching, selection state, and API calls |
| `useChat.ts` | 1.7 KB | Chat message state management for AI assistant |
| `useNavigation.ts` | 12.3 KB | Full navigation session management (GPS, WebSocket, instructions) |
| `useCustomRoute.ts` | 6.8 KB | Custom route builder state (segments, suggestions, V2 API) |
| `useMediaQuery.ts` | 0.7 KB | Responsive breakpoint detection |
| `useTimeBasedTheme.ts` | 0.2 KB | Automatic map theme switching (dawn/day/dusk/night) |

### Library Files (4 files)

| File | Size | Purpose |
|------|------|---------|
| `types.ts` | 7.7 KB | TypeScript interfaces mirroring backend Pydantic models |
| `constants.ts` | 3.6 KB | Config: API URL, Mapbox token, Toronto bounds, TTC line colors, congestion colors, isochrone colors, line logos, alert icons |
| `api.ts` | 5.0 KB | Typed API client with all endpoint functions |
| `mapUtils.ts` | 17.7 KB | Map drawing utilities — congestion-colored polylines, markers, transit overlay, isochrones, vehicle rendering |

### Styling & Design System

The UI uses a **glassmorphism dark theme** defined in `globals.css` (11.4 KB):

- **Glass cards:** `backdrop-blur-md`, semi-transparent backgrounds, subtle borders
- **TTC line colors:** Yellow (#F0CC49), Green (#549F4D), Purple (#9C246E), Orange (#DE7731), Grey (#959595)
- **Congestion palette:** Green → Amber → Orange → Red
- **Mode icons:** 🚇 Transit, 🚗 Driving, 🚶 Walking, 🚲 Cycling, 🔄 Hybrid
- **Stress labels:** Zen / Moderate / Stressful
- **Intro animation:** Globe zoom → CN Tower over 10 seconds

### Page Structure

```
app/
├── layout.tsx       → Root layout with fonts (GeistSans, GeistMono) and metadata
├── page.tsx         → Landing page with route to /map
├── globals.css      → Full design system (glassmorphism, Mapbox overrides, animations)
├── map/
│   └── page.tsx     → Main map application page (composes all components)
└── fonts/           → Local Geist font files
```

---

## Machine Learning Pipeline

### Training Pipeline (`backend/ml/`)

| File | Purpose |
|------|---------|
| `feature_engineering.py` | Extracts features from TTC subway delay CSV data |
| `train_model.py` | Trains XGBoost classifier (delay yes/no) + regressor (delay minutes) |
| `delay_model.joblib` | Serialized trained model (generated, gitignored) |

### Features Used

| Feature | Type | Description |
|---------|------|-------------|
| `line` | Categorical | TTC subway line (1, 2, 4) |
| `hour` | Numeric | Hour of day (0-23) — captures rush hour patterns |
| `day_of_week` | Numeric | Day of week (0=Mon, 6=Sun) |
| `month` | Numeric | Month of year — captures seasonal patterns |
| `station` | Categorical | Station name (optional) |
| `mode` | Categorical | Transit mode (subway, bus, streetcar) |

### Prediction Output

```json
{
  "delay_probability": 0.62,
  "expected_delay_minutes": 4.2,
  "confidence": 0.85,
  "contributing_factors": ["Rush hour (8 AM)", "Line 1 historically delayed", "Winter month"]
}
```

### Heuristic Fallback

When the trained model isn't available, the system uses a heuristic predictor based on known TTC delay patterns:
- Higher probability during rush hours (7-9 AM, 4-7 PM)
- Line 1 has higher delay rates than Line 2
- Winter months have more delays due to weather
- Weekend service is more reliable

---

## AI Chat Assistant

### Architecture

The Gemini agent (`gemini_agent.py`, 526 lines) implements a conversational AI with **7 callable tools**:

| Tool | Description |
|------|-------------|
| `get_routes` | Get multimodal route options between two GTA locations |
| `predict_delay` | Get ML delay prediction for a specific TTC line/time |
| `get_service_alerts` | Get current TTC service alerts and disruptions |
| `get_weather` | Get current weather conditions near a location |
| `find_nearby_stations` | Find transit stations near coordinates with parking info |
| `recommend_hybrid_route` | Get park-and-ride recommendations for a specific station |
| `get_parking_info` | Get parking details for a specific station |

### System Prompt

The agent is configured as "FluxRoute Assistant, an AI-powered Toronto transit expert" with:
- Knowledge of all 5 GTA transit agencies
- Proactive suggestion of hybrid routes for suburban commuters
- Fact-checking responsibilities (never fabricates schedules)
- Concise responses (2-3 sentences max unless detail requested)

### Tool Execution Flow

1. User sends message via chat UI
2. Backend builds Gemini conversation with system prompt + tool definitions
3. Gemini may invoke tools (multi-turn loop, up to 5 rounds)
4. Tool results are fed back to Gemini for natural-language synthesis
5. Response + contextual suggested actions returned to frontend

---

## Data Sources & Integrations

### GTFS Static Feeds (via OpenTripPlanner)

| Agency | File | Size | Coverage |
|--------|------|------|----------|
| TTC | `ttc.zip` | 79 MB | Subway, bus, streetcar |
| GO Transit | `gotransit.zip` | 21 MB | Commuter rail + bus |
| YRT/Viva | `yrt.zip` | 5 MB | York Region Transit |
| MiWay | `miway.zip` | 7.6 MB | Mississauga Transit |
| UP Express | `upexpress.zip` | 888 KB | Airport rail link |
| **Street Network** | `ontario.osm.pbf` | 890 MB | OpenStreetMap Ontario |

### External APIs

| API | Purpose | Auth | Free Tier |
|-----|---------|------|-----------|
| **Mapbox** | Maps, directions, geocoding, congestion | Token | 50K loads, 100K directions/mo |
| **Google Gemini** | AI chat assistant with tool use | API key | Free tier (rate-limited) |
| **Open-Meteo** | Weather data (temp, wind, precip) | None | Unlimited |
| **OpenTripPlanner** | Multi-agency transit routing | None (self-hosted) | Fully free/open-source |
| **TTC GTFS-RT** | Live vehicle positions + service alerts | None | Public protobuf feeds |
| **City of Toronto** | Active road closures | None | Public data |

### API Key Configuration

| Key | File | Purpose |
|-----|------|---------|
| `MAPBOX_TOKEN` | `backend/.env` | Backend driving/walking directions |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | `frontend/.env.local` | Frontend map rendering |
| `GEMINI_API_KEY` | `backend/.env` | AI chat assistant |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | Backend API base URL |
| `OTP_BASE_URL` | `backend/.env` | OpenTripPlanner endpoint |

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/otp/status` | OTP server availability check |
| `POST` | `/api/routes` | Generate multimodal route options |
| `GET` | `/api/predict-delay` | ML delay prediction for a TTC line |
| `POST` | `/api/chat` | Gemini AI chat assistant |

### Real-Time Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/alerts` | Current service alerts |
| `GET` | `/api/vehicles` | Live vehicle positions |
| `GET` | `/api/weather` | Current weather conditions |
| `GET` | `/api/road-closures` | Active road closures (GeoJSON) |

### Transit Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/transit-lines` | Transit line geometries for map overlay |
| `GET` | `/api/transit-shape/{id}` | GeoJSON shape for a specific transit route |
| `GET` | `/api/nearby-stops` | Find stops near coordinates |
| `GET` | `/api/search-stops` | Search GTFS stops by name |
| `GET` | `/api/line-stops/{id}` | Ordered stops for a rapid transit line |

### Route Building

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/custom-route` | Calculate user-defined custom route (v1) |
| `POST` | `/api/custom-route-v2` | Calculate custom route from AI suggestions |
| `POST` | `/api/transit-suggestions` | Get AI-suggested transit routes for a trip |

### Navigation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/navigation/route` | Get navigation-grade route with voice/banner instructions |
| `POST` | `/api/navigation/session` | Create navigation session for WebSocket |
| `POST` | `/api/navigation/optimize` | Optimize multi-stop route ordering |
| `POST` | `/api/navigation/isochrone` | Get reachability isochrone polygons |
| `WS` | `/api/navigation/ws/{session_id}` | Real-time navigation WebSocket |

### Example Requests

**Get Routes:**
```bash
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin":{"lat":43.7804,"lng":-79.4153},"destination":{"lat":43.6453,"lng":-79.3806}}'
```

**Predict Delay:**
```bash
curl "http://localhost:8000/api/predict-delay?line=Line+1&hour=8&day_of_week=0"
```

**Chat with AI:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the fastest way from Finch Station to Union?","history":[]}'
```

---

## Resilience & Fallback Strategy

FluxRoute is designed to work even when external services are unavailable:

| Failure | Fallback | Impact |
|---------|----------|--------|
| **OTP server down** | Local GTFS nearest-stop routing (TTC only) | Single-agency transit only |
| **GTFS files missing** | Hardcoded TTC subway station data (75 stations) | Basic subway routing |
| **Delay CSV unavailable** | Heuristic predictor based on real TTC patterns | Still accurate predictions |
| **GTFS-RT feeds down** | Mock vehicle positions along subway lines + sample alerts | Simulated real-time data |
| **Mapbox API unavailable** | Straight-line geometry with haversine distance estimates | No road-following routes |
| **Mapbox congestion unavailable** | Rush-hour heuristic (7-9am, 4-7pm) for stress scoring | Estimated traffic data |
| **Gemini API unavailable** | Chat shows friendly error message | All other features work |
| **Weather API down** | Default Toronto winter conditions | Conservative estimates |
| **Road closure API down** | Routes generated without closure data | No closure awareness |

### Connection Pooling & Performance

- **Shared httpx client** — 50 max connections, 20 keepalive, 12s timeout
- **IPv4 forced** — avoids IPv6 timeouts to Mapbox/CloudFront CDNs
- **Per-request Mapbox cache** — avoids duplicate API calls for same coordinates
- **OTP health check** — single check at startup, graceful fallback if unavailable

---

## Project Structure

```
CTRLHACKDEL-Fluxroute/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, CORS, lifespan startup
│   │   ├── routes.py                  # 25 API endpoints
│   │   ├── models.py                  # 40+ Pydantic v2 models
│   │   ├── route_engine.py            # Core routing engine (1,887 lines)
│   │   ├── otp_client.py              # Async OTP API client
│   │   ├── gtfs_parser.py             # TTC GTFS data loading & querying
│   │   ├── gtfs_realtime.py           # GTFS-RT vehicle positions & alerts
│   │   ├── ml_predictor.py            # XGBoost delay prediction
│   │   ├── gemini_agent.py            # Gemini AI chat with 7 tools
│   │   ├── cost_calculator.py         # Multi-agency fares & parking
│   │   ├── weather.py                 # Open-Meteo weather API
│   │   ├── road_closures.py           # City of Toronto closures
│   │   ├── transit_lines.py           # Transit line GeoJSON overlay
│   │   ├── parking_data.py            # Station parking info
│   │   ├── navigation_service.py      # WebSocket navigation sessions
│   │   ├── mapbox_navigation.py       # Mapbox Navigation API
│   │   └── route_builder_suggestions.py # AI route suggestions
│   ├── ml/
│   │   ├── feature_engineering.py     # Feature extraction from delay CSV
│   │   └── train_model.py            # XGBoost training pipeline
│   ├── data/
│   │   ├── otp/                       # OTP data (GTFS zips, OSM, configs)
│   │   ├── gtfs/                      # TTC GTFS static feed
│   │   └── ttc-subway-delay-data.csv  # Historical delay data for ML
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout with fonts & metadata
│   │   ├── page.tsx                   # Landing page
│   │   ├── globals.css                # Full design system (11.4 KB)
│   │   └── map/page.tsx               # Main map application page
│   ├── components/                    # 27 React components
│   ├── hooks/                         # 6 custom hooks
│   ├── lib/
│   │   ├── types.ts                   # TypeScript interfaces
│   │   ├── constants.ts               # Configuration & constants
│   │   ├── api.ts                     # Typed API client
│   │   └── mapUtils.ts               # Map drawing utilities (17.7 KB)
│   ├── package.json
│   └── tailwind.config.ts
├── docs/
│   ├── ROADMAP.md                     # Project roadmap & status
│   ├── API_KEYS_SETUP.md             # API key instructions
│   ├── OTP_SETUP.md                  # OTP setup guide
│   ├── OTP_INTEGRATION.md            # OTP integration details
│   ├── TRAFFIC_INTEGRATION.md        # Traffic integration docs
│   ├── LANDING_PAGE_PLAN.md          # Landing page design
│   └── ML_ENHANCEMENT.md            # ML enhancement plans
├── docker-compose.yml                 # OTP Docker service
├── README.md                          # Project README
└── CLAUDE.md                          # Project guide for AI assistants
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+ (tested with 3.12)
- Node.js 18+ (tested with 22.9.0)
- Java 17+ (for OTP natively) or Docker
- Git LFS

### Quick Start

```bash
# 1. Clone and pull large files
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute
git lfs install && git lfs pull

# 2. Backend
pip install -r backend/requirements.txt
# macOS only: brew install libomp

# 3. Configure environment
# backend/.env → MAPBOX_TOKEN, GEMINI_API_KEY, OTP_BASE_URL
# frontend/.env.local → NEXT_PUBLIC_MAPBOX_TOKEN, NEXT_PUBLIC_API_URL

# 4. Frontend
cd frontend && npm install && cd ..

# 5. Start OTP (Terminal 1, ~15-20 min first build)
cd backend/data/otp && java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve .

# 6. Start Backend (Terminal 2)
cd backend && python3 -m uvicorn app.main:app --reload

# 7. Start Frontend (Terminal 3)
cd frontend && npm run dev

# Open http://localhost:3000
```

### Optional: Train ML Model

```bash
cd backend && python3 -m ml.train_model
```

---

## Roadmap & Future Enhancements

### Completed Phases

- ✅ **Phase 0** — Core infrastructure (FastAPI, Next.js, Mapbox, geocoding)
- ✅ **Phase 1** — Core routing & features (multi-mode routing, cost calc, stress scoring, decision matrix)
- ✅ **Phase 2** — ML & AI (XGBoost training, Gemini chat with tool use)
- ✅ **Phase 3** — Real-time data (GTFS-RT poller, live vehicles, alerts, weather)
- ✅ **Phase 4** — Traffic & map enhancements (congestion coloring, road closures, time-based theme)
- ✅ **Phase 5** — Multi-agency OTP integration (5 agencies, OSM, Docker, Git LFS)

### Potential Future Work

| Priority | Enhancement | Effort |
|----------|-------------|--------|
| High | Real GTFS-RT feeds (replace mock data) | Medium |
| High | OTP GTFS-RT integration (schedule-adjusted routing) | Medium |
| High | Brampton Transit as 6th agency | Low |
| Medium | GO Transit real-time positions via Metrolinx API | Medium |
| Medium | Cached OTP graph (skip rebuild) | Low |
| Medium | User preferences (avoid transfers, accessibility) | Medium |
| Medium | Bike Share Toronto integration | Medium |
| Low | Multi-stop trip planning | High |
| Low | Voice copilot for route queries | Medium |
| Low | Historical route performance tracking | High |

---

## Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | **Google Gemini** for AI chat | Free tier, native tool use support | Feb 2025 |
| 2 | **Mapbox** over Google Maps | Generous free tier, better DX, congestion annotations | Feb 2025 |
| 3 | **XGBoost** for delay prediction | Fast training, ideal for tabular data | Feb 2025 |
| 4 | **OpenTripPlanner** for transit routing | Industry-standard, handles multi-agency natively | Feb 2025 |
| 5 | **Git LFS** for large files | GTFS zips + OSM PBF too large for regular git | Feb 2025 |
| 6 | **OTP JAR via Maven Central** | JAR too large for git (~174 MB), easy curl download | Feb 2025 |
| 7 | **Keep all fallbacks** | Demo reliability over feature completeness | Feb 2025 |
| 8 | **Mapbox driving-traffic** | Real congestion data for drive vs transit comparison | Feb 2025 |
| 9 | **PRESTO co-fare discounts** | Accurate multi-agency cost comparison | Feb 2025 |

---

*Built by **Team FluxRoute** at CTRL+HACK+DEL 2025.*
