# FluxRoute — Project Roadmap & Status

**Hackathon:** CTRL+HACK+DEL 2025
**Team:** Team FluxRoute
**Last Updated:** February 14, 2026

---

## Current State Summary

FluxRoute is a fully functional multimodal transit routing app for the GTA. The core application, multi-agency integration, ML pipeline, AI assistant, and real-time data feeds are all built and working.

### What's Built and Working

| Component | Status | Details |
|-----------|--------|---------|
| **FastAPI Backend** | Working | Lifespan startup, CORS, 11 API endpoints |
| **Pydantic v2 Models** | Working | Full API contract with strict type validation |
| **Route Engine** | Working | OTP-first transit routing with GTFS fallback, Mapbox driving/walking |
| **OpenTripPlanner Integration** | Working | 5-agency multi-agency routing (TTC, GO, YRT, MiWay, UP Express) |
| **OTP Client** | Working | Async HTTP client, health checks, polyline decoding |
| **GTFS Static Data (TTC)** | Working | 9,388 stops, 230 routes loaded on startup |
| **Multi-Agency GTFS Data** | Working | 5 agencies via OTP (Git LFS tracked) |
| **Ontario OSM Street Network** | Working | 890 MB PBF file for OTP graph building |
| **XGBoost ML Model** | Working | Trained delay predictor with heuristic fallback |
| **Gemini AI Chat** | Working | Tool use with route prediction, delay checking, transit info |
| **Cost Calculator** | Working | Multi-agency fares, gas, parking, PRESTO co-fare discounts |
| **Weather Integration** | Working | Open-Meteo API, feeds into delay predictions + stress scoring |
| **Road Closures** | Working | City of Toronto closure data, factored into stress scoring |
| **GTFS-RT Poller** | Working | Vehicle positions + service alerts (mock fallback) |
| **Real-Time Traffic** | Working | Mapbox congestion annotations for driving/hybrid routes |
| **Next.js 14 Frontend** | Working | All 11 components built |
| **Mapbox GL Map** | Working | Dark theme, congestion-colored routes, vehicle markers |
| **Geocoder Input** | Working | Mapbox Geocoder with Toronto bounding box |
| **Route Cards + Decision Matrix** | Working | Fastest / Thrifty / Zen comparison |
| **Turn-by-Turn Directions** | Working | DirectionSteps component for driving/walking |
| **Chat Assistant UI** | Working | Floating panel, message history, suggested actions |
| **Live Alerts Banner** | Working | Rotating service alerts display |
| **Vehicle Overlay** | Working | 15-second polling, pulsing markers on map |
| **Time-Based Theme** | Working | Map style adapts to dawn/day/dusk/night |
| **Docker Compose** | Working | OTP service containerization |
| **Git LFS** | Working | Large GTFS/OSM files tracked and pushed |

---

## Architecture (Current)

```
Browser (localhost:3000)
    |
    v
Next.js 14 Frontend (TypeScript, Mapbox GL JS)
    |  HTTP requests
    v
FastAPI Backend (localhost:8000)
    |
    |-- OpenTripPlanner (localhost:8080)
    |   |-- TTC GTFS (subway, bus, streetcar)
    |   |-- GO Transit GTFS (trains, buses)
    |   |-- YRT GTFS (York Region Transit)
    |   |-- MiWay GTFS (Mississauga Transit)
    |   |-- UP Express GTFS
    |   |-- Ontario OSM (street network)
    |
    |-- Mapbox Directions API
    |   |-- driving-traffic profile + congestion annotations
    |   |-- walking profile
    |   |-- geocoding
    |
    |-- Google Gemini API (AI chat with tool use)
    |-- Open-Meteo Weather API (real-time weather)
    |-- TTC GTFS-RT (live vehicle positions + alerts)
    |-- City of Toronto (road closures)
    |-- XGBoost ML Model (delay prediction)
    |
    v
Frontend renders:
    - Congestion-colored route polylines
    - Multi-agency route cards with cost breakdown
    - Decision matrix (Fastest/Thrifty/Zen)
    - Turn-by-turn directions
    - Live vehicle markers
    - Service alert banner
    - AI chat assistant
```

---

## Completed Milestones

### Phase 0 — Core Infrastructure
- [x] FastAPI backend with lifespan, CORS, all endpoints
- [x] Pydantic v2 models for full API contract
- [x] Next.js 14 frontend with App Router
- [x] Mapbox GL JS map with dark-v11 style
- [x] Geocoder-powered origin/destination input
- [x] Environment variable configuration (.env, .env.local)

### Phase 1 — Core Routing & Features
- [x] Route engine generating transit, driving, walking, hybrid routes
- [x] TTC GTFS static data loading (9,388 stops, 230 routes)
- [x] Mapbox Directions API integration (driving-traffic profile)
- [x] Cost calculator (TTC fares, gas, parking)
- [x] Stress scoring (transfers, delays, weather, traffic, walking)
- [x] Decision Matrix (Fastest / Thrifty / Zen)
- [x] Route cards with duration, cost, delay badge, summary
- [x] Sidebar collapse/expand
- [x] Loading overlay during route calculation

### Phase 2 — ML & AI
- [x] XGBoost model training pipeline (feature engineering + train)
- [x] ML delay predictor with heuristic fallback
- [x] Delay predictions integrated into route responses
- [x] Weather data feeds into delay predictions
- [x] Google Gemini AI chat assistant with tool use
- [x] Chat UI with message history and suggested actions
- [x] DelayIndicator badge (green/yellow/red)

### Phase 3 — Real-Time Data
- [x] GTFS-RT poller for vehicle positions + service alerts
- [x] Live vehicle markers on map (15-second polling)
- [x] Rotating service alert banner
- [x] Mock fallback when feeds unavailable
- [x] Weather API integration (Open-Meteo)

### Phase 4 — Traffic & Map Enhancements
- [x] Mapbox congestion annotations for driving/hybrid routes
- [x] Congestion-colored route polylines (green/yellow/orange/red)
- [x] Traffic-aware stress scoring (replaces rush-hour heuristic)
- [x] Rush-hour heuristic fallback when congestion data unavailable
- [x] Time-based map theme (dawn/day/dusk/night)
- [x] Turn-by-turn direction steps component
- [x] Road closure data from City of Toronto

### Phase 5 — Multi-Agency OTP Integration
- [x] Downloaded GTFS data for 5 agencies (TTC, GO, YRT, MiWay, UP Express)
- [x] Downloaded Ontario OSM street network (890 MB)
- [x] OTP build-config.json and otp-config.json created
- [x] Docker Compose configuration for OTP service
- [x] OTP client module (async HTTP, polyline decoding, health checks)
- [x] Route engine: OTP-first with GTFS fallback
- [x] Multi-agency cost calculator with PRESTO co-fare discounts
- [x] `/api/otp/status` endpoint
- [x] Git LFS tracking for large data files
- [x] OTP data files merged into main branch
- [x] Setup documentation (OTP_SETUP.md, OTP_INTEGRATION.md)
- [x] GTFS download helper script

---

## What's Next — Potential Enhancements

These are ideas for future development beyond the hackathon scope.

### High Priority

| Enhancement | Description | Effort |
|-------------|-------------|--------|
| Real GTFS-RT feeds | Replace mock vehicle/alert data with live TTC GTFS-RT protobuf feeds | Medium |
| OTP GTFS-RT integration | Feed real-time updates into OTP for schedule-adjusted routing | Medium |
| Brampton Transit | Add Brampton/Zum GTFS data as 6th agency in OTP | Low |
| Smaller OSM extract | Use GTA-only OSM extract (~200 MB) instead of all Ontario (~890 MB) | Low |

### Medium Priority

| Enhancement | Description | Effort |
|-------------|-------------|--------|
| GO Transit real-time | Metrolinx Open Data API for live GO train/bus positions | Medium |
| Cached OTP graph | Save built graph to skip 15-minute rebuild on restart | Low |
| User preferences | Avoid transfers, prefer subway, accessibility options | Medium |
| Bike-share integration | Bike Share Toronto stations as first/last mile options | Medium |
| Carbon footprint | CO2 emissions comparison across route modes | Low |

### Low Priority (Stretch Goals)

| Enhancement | Description | Effort |
|-------------|-------------|--------|
| Multi-stop trips | Plan routes with intermediate stops | High |
| Historical performance | Track route reliability over time | High |
| Community reporting | User-submitted delay/incident reports | High |
| Voice copilot | Voice input for route queries | Medium |
| Accessibility routing | Wheelchair-accessible route filtering | Medium |
| GTFS auto-refresh | Cron job to download fresh GTFS feeds weekly | Low |

---

## Tech Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14, TypeScript, React 18 | App framework |
| **Map** | Mapbox GL JS 3.18 | Route visualization, geocoding |
| **Styling** | Tailwind CSS 3.4 | Glassmorphism UI theme |
| **Backend** | FastAPI, Python 3.12, Uvicorn | API server |
| **Transit Routing** | OpenTripPlanner 2.5 | Multi-agency graph routing |
| **ML** | XGBoost, scikit-learn | Delay prediction |
| **AI Chat** | Google Gemini | Conversational assistant with tool use |
| **Weather** | Open-Meteo API | Real-time weather (no API key) |
| **Traffic** | Mapbox Directions API | Congestion annotations |
| **Real-time** | TTC GTFS-RT | Vehicle positions + alerts |
| **Data** | Pandas, Git LFS | GTFS processing, large file storage |
| **Infra** | Docker Compose | OTP containerization |

---

## Data Sources

### GTFS Static Feeds (via OTP)

| Agency | File | Size | Coverage |
|--------|------|------|----------|
| TTC | `ttc.zip` | 79 MB | Subway, bus, streetcar |
| GO Transit | `gotransit.zip` | 21 MB | Commuter rail + bus |
| YRT/Viva | `yrt.zip` | 5 MB | York Region Transit |
| MiWay | `miway.zip` | 7.6 MB | Mississauga Transit |
| UP Express | `upexpress.zip` | 888 KB | Airport rail link |
| **Street Network** | `ontario.osm.pbf` | 890 MB | OpenStreetMap Ontario |

### APIs

| API | Purpose | Auth | Free Tier |
|-----|---------|------|-----------|
| Mapbox | Maps, directions, geocoding, congestion | Token | 50K loads, 100K directions/mo |
| Google Gemini | AI chat assistant | API key | Free tier (rate-limited) |
| Open-Meteo | Weather data | None | Unlimited |
| OpenTripPlanner | Multi-agency routing | None (self-hosted) | Fully free/open-source |
| TTC GTFS-RT | Vehicle positions + alerts | None | Public feeds |
| City of Toronto | Road closures | None | Public data |

---

## Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Google Gemini for AI chat | Free tier, tool use support | Feb 2025 |
| 2 | Mapbox over Google Maps | Generous free tier, better DX, congestion annotations | Feb 2025 |
| 3 | XGBoost for delay prediction | Fast training, good for tabular data | Feb 2025 |
| 4 | OpenTripPlanner for transit routing | Industry-standard, handles multi-agency natively | Feb 2025 |
| 5 | Git LFS for large files | GTFS zips and OSM PBF too large for regular git | Feb 2025 |
| 6 | OTP JAR via Maven Central | JAR too large for git (~174 MB), easy curl download | Feb 2025 |
| 7 | Keep all fallbacks | Demo reliability over feature completeness | Feb 2025 |
| 8 | Mapbox driving-traffic profile | Real congestion data for driving vs transit comparison | Feb 2025 |
| 9 | PRESTO co-fare discounts | Accurate multi-agency cost comparison | Feb 2025 |

---

## Quick Reference

```bash
# Download OTP JAR (one-time)
curl -L -o backend/data/otp/otp-2.5.0-shaded.jar \
  "https://repo1.maven.org/maven2/org/opentripplanner/otp/2.5.0/otp-2.5.0-shaded.jar"

# Start OTP (Terminal 1, ~15-20 min first build)
cd backend/data/otp && java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve .

# Start Backend (Terminal 2)
cd backend && python3 -m uvicorn app.main:app --reload

# Start Frontend (Terminal 3)
cd frontend && npm run dev

# Train ML model (optional)
cd backend && python3 -m ml.train_model

# Test API
curl http://localhost:8000/api/health
curl http://localhost:8000/api/otp/status
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin":{"lat":43.7804,"lng":-79.4153},"destination":{"lat":43.6453,"lng":-79.3806}}'
```
