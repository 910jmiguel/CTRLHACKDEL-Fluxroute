# FluxRoute — Hackathon Roadmap & Checklist

**Deadline:** Sunday, February 16, 2025 — 9:00 AM
**Last Updated:** Saturday, February 15, 2025 — 3:00 AM
**Time Remaining:** ~15-17 hours of working time (after sleep)
**Team:** Team FluxRoute — CTRL+HACK+DEL 2025 Hackathon

### Schedule Overview
```
Sat Feb 15  3:00 AM  ── NOW (wrap up, go to sleep)
            ~10 AM   ── Wake up, start Phase 0 + 1
            ~2 PM    ── Phase 2 (Real Data & Multi-Agency)
            ~7 PM    ── Phase 3 (ML & AI Polish)
            ~10 PM   ── Phase 4 (UI/UX & Demo Polish)
Sun Feb 16  ~1 AM    ── Phase 5 (Final Submission Prep)
            ~3 AM    ── FREEZE: stop adding features, only fix bugs
            9:00 AM  ── DEADLINE
```

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Target Architecture](#2-target-architecture)
3. [Time Budget](#3-time-budget)
4. [Phase 0 — Critical Fixes (NOW)](#phase-0--critical-fixes-now--1-hour)
5. [Phase 1 — Core Functionality Lock-In](#phase-1--core-functionality-lock-in-3-4-hours)
6. [Phase 2 — Real Data & Multi-Agency Transit](#phase-2--real-data--multi-agency-transit-4-5-hours)
7. [Phase 3 — ML & AI Polish](#phase-3--ml--ai-polish-3-4-hours)
8. [Phase 4 — UI/UX & Demo Polish](#phase-4--uiux--demo-polish-3-4-hours)
9. [Phase 5 — Final Submission Prep](#phase-5--final-submission-prep-1-2-hours)
10. [Data Sources & API Reference](#data-sources--api-reference)
11. [Risk Register](#risk-register)
12. [Decision Log](#decision-log)

---

## 1. Current State Assessment

### What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI backend structure | **Working** | Lifespan, CORS, all 9 endpoints defined |
| Pydantic v2 models | **Working** | Full API contract, type-safe |
| Route engine (transit/drive/walk/hybrid) | **Working** | Generates multimodal routes with segments |
| GTFS static data (TTC) | **Working** | 9,388 stops, 230 routes loaded on startup |
| ML delay predictor (heuristic fallback) | **Working** | Rule-based predictions active |
| Gemini AI chat assistant | **Working** | Tool use with 4 tools implemented |
| Cost calculator | **Working** | TTC fares, gas, parking |
| Weather integration (Open-Meteo) | **Working** | Real-time weather, no API key needed |
| GTFS-RT poller | **Working** | Falls back to mock data when feeds unavailable |
| Next.js 14 frontend | **Working** | All 10 components built |
| Mapbox GL map | **Working** | Dark theme, route polylines, markers |
| Geocoder (origin/destination) | **Working** | Mapbox GL Geocoder with Toronto bounds |
| Route cards + Decision Matrix | **Working** | Fastest / Thrifty / Zen comparison |
| Chat assistant UI | **Working** | Floating panel, message history |
| Live alerts banner | **Working** | Rotating alerts display |
| Vehicle position overlay | **Working** | 15-second polling on map |

### What's Broken or Incomplete

| Issue | Severity | Details |
|-------|----------|---------|
| ML model file missing | **Medium** | `delay_model.joblib` not generated — heuristic works but less accurate |
| ~~Documentation outdated~~ | **Done** | CLAUDE.md and README updated to reference Gemini (fixed Feb 15 3AM) |
| Only TTC data | **High** | No GO Transit, MiWay, YRT, or Brampton Transit data |
| GTFS-RT uses mock data | **High** | Real-time feeds not connected (mock vehicles/alerts) |
| No multi-agency routing | **High** | Can't plan trips across TTC + GO + regional agencies |
| Transit routing is nearest-stop heuristic | **Medium** | Not a real graph search — misses optimal transfers |
| API keys in `.env.local` | **Low** | Should be `.env` (gitignored) — minor file naming issue |
| Git has uncommitted changes | **Low** | `.gitignore`, `README.md`, `package-lock.json` modified |

### What's Missing Entirely

| Feature | Priority | Notes |
|---------|----------|-------|
| OpenTripPlanner integration | **P0** | Needed for real multi-agency transit routing |
| Transitland API integration | **P1** | Unified discovery layer for all GTHA agencies |
| Multi-agency GTFS data (GO, YRT, MiWay, Brampton) | **P1** | Only TTC currently loaded |
| Real GTFS-RT feeds | **P1** | Vehicle positions + alerts from live feeds |
| Trained XGBoost model | **P1** | Need to run training pipeline |
| Google Routes API for last-mile | **P2** | Currently using Mapbox for everything |
| Community reporting | **P3** | Stretch goal |
| Voice copilot | **P3** | Stretch goal — skip unless time permits |

---

## 2. Target Architecture

### Current Architecture (MVP)

```
User → Frontend (Next.js) → Backend (FastAPI) → Mapbox Directions API
                                              → TTC GTFS Static (local)
                                              → Mock GTFS-RT data
                                              → XGBoost heuristic
                                              → Gemini AI chat
                                              → Open-Meteo weather
```

### Target Architecture (Upgraded)

```
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                            │
│                                                         │
│  GTFS Static Files (per agency):                        │
│  ├── TTC (Toronto Transit Commission)     ✅ Have it    │
│  ├── GO Transit / Metrolinx              🔲 Need it    │
│  ├── YRT / Viva (York Region)            🔲 Need it    │
│  ├── MiWay (Mississauga)                 🔲 Need it    │
│  └── Brampton Transit                    🔲 Need it    │
│                                                         │
│  Discovery: Transitland API (transit.land)              │
│  → Browse/download all GTHA feeds from one place        │
│  → Free tier, 2,500+ operators indexed                  │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌──────────────────────┴──────────────────────────────────┐
│              ROUTING ENGINE LAYER                        │
│                                                         │
│  OpenTripPlanner (OTP) — Self-hosted                    │
│  → Ingests ALL agency GTFS files                        │
│  → Cross-agency journey planning (TTC→GO→YRT)           │
│  → Handles transfers, schedules, real routing graph      │
│  → Replaces our nearest-stop heuristic                  │
│  → Free, open-source, industry standard                 │
│                                                         │
│  Mapbox Directions API (driving/walking/cycling)        │
│  → Last-mile segments to/from transit stops             │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌──────────────────────┴──────────────────────────────────┐
│             REAL-TIME DATA LAYER                         │
│                                                         │
│  GTFS-RT Feeds (per agency):                            │
│  ├── TTC — Vehicle positions + service alerts           │
│  ├── GO/Metrolinx — Via Metrolinx Open Data API         │
│  └── Others — Via Transitland GTFS-RT proxy             │
│                                                         │
│  Polling: 15-second interval, cached in app_state       │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌──────────────────────┴──────────────────────────────────┐
│              ML / AI LAYER                               │
│                                                         │
│  XGBoost Delay Predictor                                │
│  → Trained on TTC historical delay CSV                  │
│  → Features: line, station, hour, day, month, weather   │
│  → Output: delay probability + expected minutes         │
│                                                         │
│  Google Gemini AI Chat Assistant                         │
│  → Tool use: routes, delays, alerts, weather            │
│  → Context-aware (user location, current routes)        │
│                                                         │
│  Open-Meteo Weather API                                 │
│  → Feeds into delay prediction + stress scoring         │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌──────────────────────┴──────────────────────────────────┐
│              PRESENTATION LAYER                          │
│                                                         │
│  Next.js 14 Frontend                                    │
│  ├── Mapbox GL JS — Route visualization, live vehicles  │
│  ├── Decision Matrix — Fastest / Thrifty / Zen          │
│  ├── Route Cards — Multimodal comparison                │
│  ├── Chat Assistant — Gemini-powered advice             │
│  ├── Live Alerts — Rotating service alert banner        │
│  └── Delay Indicators — Green/Yellow/Red badges         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Time Budget

**Available:** ~15-17 working hours (Sat morning → Sun 9 AM)
**Buffer:** Always keep 2-3 hours for unexpected issues and bug fixes
**Code Freeze:** Sunday 3 AM — no new features after this, only bug fixes

| Phase | Est. Time | Window (Sat-Sun) | Priority |
|-------|-----------|-------------------|----------|
| **Phase 0** — Critical Fixes | 1-1.5 hrs | Sat 10:00 AM - 11:30 AM | MUST DO |
| **Phase 1** — Core Lock-In | 2-3 hrs | Sat 11:30 AM - 2:00 PM | MUST DO |
| **Phase 2** — Real Data & Multi-Agency | 4-5 hrs | Sat 2:00 PM - 7:00 PM | MUST DO |
| **Phase 3** — ML & AI Polish | 2-3 hrs | Sat 7:00 PM - 10:00 PM | SHOULD DO |
| **Phase 4** — UI/UX & Demo Polish | 3-4 hrs | Sat 10:00 PM - Sun 1:00 AM | SHOULD DO |
| **Phase 5** — Final Submission | 1-2 hrs | Sun 1:00 AM - 3:00 AM | MUST DO |
| **Bug Fix Buffer** | 2-3 hrs | Sun 3:00 AM - 6:00 AM (if needed) | RESERVE |
| **Sleep / Rest before demo** | — | Sun 6:00 AM - 9:00 AM | DO IT |

**Golden Rule:** At every phase boundary, you should have a _demoable_ product. Never be in a state where "it's all broken but it'll work when I finish this next thing."

**Tonight (3 AM):** Go to sleep. You've done the planning and doc updates. Fresh eyes tomorrow will be 10x more productive than grinding through bugs at 4 AM.

---

## Phase 0 — Critical Fixes | ~1-1.5 hours | Sat 10:00 AM

First thing when you wake up. Stabilize the current build before touching anything else.

### Environment & Config

- [ ] Verify `backend/.env` exists with correct keys:
  ```
  GEMINI_API_KEY=your-gemini-key
  MAPBOX_TOKEN=pk.your-mapbox-token
  ```
- [ ] Verify `frontend/.env.local` exists with correct keys:
  ```
  NEXT_PUBLIC_MAPBOX_TOKEN=pk.your-mapbox-token
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```
- [ ] Confirm backend starts without errors: `cd backend && python3 -m uvicorn app.main:app --reload`
- [ ] Confirm frontend starts without errors: `cd frontend && npm run dev`
- [ ] Test health endpoint: `curl http://localhost:8000/api/health`

### Quick Bug Fixes

- [ ] Fix any import errors or startup crashes (check terminal output)
- [ ] Verify the map renders at `http://localhost:3000`
- [ ] Verify geocoder (origin/destination input) works
- [ ] Test a route search end-to-end: enter origin → destination → see routes on map
- [ ] Verify chat assistant sends/receives messages

### Git Housekeeping

- [ ] Commit current uncommitted changes (`.gitignore`, `README.md`, `package-lock.json`)
- [ ] Create a `stable-mvp` tag or branch as a safety checkpoint

**Exit Criteria:** App runs locally, routes appear on map, chat works. You have a stable baseline to build on.

---

## Phase 1 — Core Functionality Lock-In | 2-3 hours | Sat 11:30 AM

Lock in all existing features so they work reliably before adding new data sources.

### Backend Stability

- [ ] Train the XGBoost ML model:
  ```bash
  cd backend && python3 -m ml.train_model
  ```
  Verify `backend/ml/delay_model.joblib` is generated.
- [ ] Restart backend and confirm ML predictor loads in "ML mode" (check logs for "Loaded XGBoost model")
- [ ] Test delay prediction endpoint:
  ```bash
  curl "http://localhost:8000/api/predict-delay?line=Line+1&hour=8&day_of_week=0"
  ```
- [ ] Test route generation returns delay info with ML predictions (not just heuristic)
- [ ] Verify Gemini chat assistant responds with tool use (ask it "What's the fastest route from Union Station to Finch?")
- [ ] Test weather endpoint returns real data: `curl http://localhost:8000/api/weather`

### Frontend Stability

- [ ] Verify route cards display correctly (duration, cost, delay badge, summary)
- [ ] Verify Decision Matrix picks correct winners (Fastest/Thrifty/Zen)
- [ ] Verify CostBreakdown expands and shows fare/gas/parking
- [ ] Verify DelayIndicator colors are correct (green <30%, yellow 30-60%, red >60%)
- [ ] Verify LiveAlerts banner rotates alerts
- [ ] Verify vehicle markers appear on map (even if mock data)
- [ ] Test sidebar collapse/expand on different screen sizes
- [ ] Verify route selection highlights the route on the map

### Bug Hunt Checklist

- [ ] Check browser console for JavaScript errors
- [ ] Check backend terminal for Python exceptions
- [ ] Test with various origin/destination pairs (not just downtown)
- [ ] Test edge case: origin and destination very close together
- [ ] Test edge case: origin and destination very far apart (across GTA)
- [ ] Verify no CORS errors in browser network tab

**Exit Criteria:** All existing features work reliably. ML model is trained and serving real predictions. No crashes on typical usage.

---

## Phase 2 — Real Data & Multi-Agency Transit | 4-5 hours | Sat 2:00 PM

This is the biggest and most important upgrade — moving from TTC-only mock data to real multi-agency GTHA transit. **Grab lunch first**, then grind this out.

### 2A. Gather Multi-Agency GTFS Data | ~1 hour

Use **Transitland** (transit.land) as your discovery layer to find and download feeds.

- [ ] **TTC** — Already have it in `backend/data/gtfs/`
- [ ] **GO Transit / Metrolinx** — Download GTFS static feed
  - Source: Transitland or [Metrolinx Open Data](https://www.metrolinx.com/en/about-us/open-data)
  - Save to: `backend/data/gtfs-go/`
- [ ] **YRT / Viva (York Region Transit)** — Download GTFS static feed
  - Source: Transitland or [YRT Open Data](https://www.yrt.ca/en/about-us/open-data.aspx)
  - Save to: `backend/data/gtfs-yrt/`
- [ ] **MiWay (Mississauga Transit)** — Download GTFS static feed
  - Source: Transitland or [MiWay Open Data](https://www.mississauga.ca/services-and-programs/transportation-and-streets/miway/developer-download/)
  - Save to: `backend/data/gtfs-miway/`
- [ ] **Brampton Transit** — Download GTFS static feed
  - Source: Transitland or [Brampton Open Data](https://geohub.brampton.ca/)
  - Save to: `backend/data/gtfs-brampton/`

> **Tip:** All of these agencies are indexed on Transitland. Go to `transit.land/feeds`, search for each one, and grab the download URL. You can also use the Transitland REST API to query feeds programmatically.

### 2B. Set Up OpenTripPlanner (OTP) | ~2 hours

OTP is your **unified routing engine** — it ingests all GTFS feeds and handles cross-agency journey planning natively.

- [ ] Download OTP 2.x JAR file:
  ```bash
  mkdir -p otp && cd otp
  curl -L -o otp-shaded.jar "https://repo1.maven.org/maven2/org/opentripplanner/otp/2.5.0/otp-2.5.0-shaded.jar"
  ```
- [ ] Create OTP data directory and copy all GTFS zips:
  ```bash
  mkdir -p otp/data
  # Copy all agency GTFS zip files into otp/data/
  cp backend/data/gtfs.zip otp/data/ttc-gtfs.zip        # re-zip if needed
  cp backend/data/gtfs-go/*.zip otp/data/go-gtfs.zip
  cp backend/data/gtfs-yrt/*.zip otp/data/yrt-gtfs.zip
  # ... etc for each agency
  ```
- [ ] Download OpenStreetMap data for GTA (needed for street routing):
  ```bash
  cd otp/data
  # Download Ontario extract from Geofabrik
  curl -L -o ontario.osm.pbf "https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf"
  ```
  > **Note:** This file is ~500MB. If too slow, use a smaller bounding-box extract from BBBike.
- [ ] Build OTP graph:
  ```bash
  java -Xmx4G -jar otp-shaded.jar --build --save otp/data
  ```
  This processes all GTFS + OSM data into a routing graph. Takes 5-15 minutes.
- [ ] Start OTP server:
  ```bash
  java -Xmx2G -jar otp-shaded.jar --load otp/data
  ```
  OTP API will be available at `http://localhost:8080`
- [ ] Test OTP routing:
  ```bash
  curl "http://localhost:8080/otp/routers/default/plan?fromPlace=43.6532,-79.3832&toPlace=43.7804,-79.4153&mode=TRANSIT,WALK&date=2025-02-15&time=08:00:00"
  ```
- [ ] Verify cross-agency routing works (e.g., TTC to GO transfer)

### 2C. Integrate OTP into FluxRoute Backend | ~1.5 hours

Replace the current nearest-stop heuristic with real OTP routing.

- [ ] Create `backend/app/otp_client.py` — async HTTP client for OTP API:
  ```python
  # Key function: query_otp_routes(origin, destination, modes, departure_time)
  # Parses OTP itineraries into our RouteOption/RouteSegment models
  ```
- [ ] Update `backend/app/route_engine.py`:
  - [ ] Add OTP as primary transit routing source
  - [ ] Keep Mapbox Directions for driving/walking/cycling
  - [ ] Keep existing heuristic as fallback if OTP is down
  - [ ] Map OTP itinerary legs → our `RouteSegment` model
  - [ ] Preserve delay prediction, cost calc, and stress scoring on top of OTP routes
- [ ] Update `backend/app/main.py`:
  - [ ] Add OTP health check to startup lifespan
  - [ ] Store OTP base URL in app_state
  - [ ] Add `OTP_BASE_URL` to `.env` (default: `http://localhost:8080`)
- [ ] Test end-to-end: frontend → backend → OTP → response with real multi-agency routes

### 2D. Connect Real GTFS-RT Feeds | ~1 hour

Replace mock data with live vehicle positions and service alerts.

- [ ] **TTC GTFS-RT feeds** (no API key required):
  - Vehicle positions: `https://alerts.ttc.ca/api/alerts/live-map/getVehicles`
  - Service alerts: `https://alerts.ttc.ca/api/alerts/list`
  - Or use protobuf feeds if available
- [ ] **Metrolinx / GO GTFS-RT** (may require API key):
  - Check Metrolinx Open Data portal for real-time feed URLs
  - Or use Transitland GTFS-RT proxy
- [ ] Update `backend/app/gtfs_realtime.py`:
  - [ ] Add real TTC feed URLs
  - [ ] Add GO Transit feed URLs (if available)
  - [ ] Keep mock fallback for agencies where feeds aren't available
  - [ ] Parse protobuf responses into our `VehiclePosition` and `ServiceAlert` models
- [ ] **Transitland API integration** (optional but powerful):
  - [ ] Sign up for Transitland API key at `transit.land`
  - [ ] Use `/api/v2/rest/feeds` to discover feed URLs
  - [ ] Use `/api/v2/rest/routes` and `/api/v2/rest/stops` for enriched data
  - [ ] Add `TRANSITLAND_API_KEY` to `.env`
- [ ] Test: verify real vehicle positions appear on the map
- [ ] Test: verify real service alerts appear in the banner

**Exit Criteria:** Routes are generated using real OTP graph routing across multiple agencies. Real-time vehicle positions and alerts are live (at least for TTC). The app shows real transit data, not just mock.

---

## Phase 3 — ML & AI Polish | 2-3 hours | Sat 7:00 PM

Improve the intelligence layer now that real data is flowing. **Grab dinner first.**

### ML Delay Predictor

- [ ] Verify XGBoost model is loaded and serving predictions
- [ ] Test predictions for different lines, times, and days:
  ```bash
  # Rush hour Monday on Line 1
  curl "http://localhost:8000/api/predict-delay?line=Line+1&hour=8&day_of_week=0"
  # Weekend afternoon on Line 2
  curl "http://localhost:8000/api/predict-delay?line=Line+2&hour=14&day_of_week=5"
  ```
- [ ] Verify delay predictions integrate into route responses (check `delay_info` in route JSON)
- [ ] Ensure weather data feeds into delay predictions (precipitation → higher delay probability)
- [ ] Tune stress scoring weights if they feel off during testing:
  - Transfers: 0.1 per transfer
  - Delay probability: 0.3 weight
  - Weather: 0.2 if bad
  - Rush hour: 0.1
  - Walking: 0.05/km
  - Driving: 0.15 base

### Gemini AI Chat Assistant

- [ ] Test chat with route-related questions:
  - "What's the fastest way to get from Union to Finch?"
  - "Is there any delays on Line 1 right now?"
  - "Should I drive or take transit to the airport?"
- [ ] Verify tool use works (Gemini calls get_routes, predict_delay, etc.)
- [ ] Test chat retains context across messages (conversation history)
- [ ] Verify suggested actions appear and are relevant
- [ ] If OTP is integrated, update chat tools to use real routing data
- [ ] Test error handling: what happens if Gemini API key is invalid or rate-limited?
- [ ] Add transit-specific system prompt enhancements if needed (e.g., GTHA knowledge, fare info for all agencies)

### Data Quality

- [ ] Spot-check a few routes for sanity:
  - Duration reasonable? (not 0 min or 999 min)
  - Distance reasonable?
  - Cost breakdown makes sense?
  - Route geometry actually follows roads/rails on the map?
- [ ] Verify routes from multiple agencies appear (if OTP integrated)
- [ ] Check that hybrid routes (park & ride) make geographic sense

**Exit Criteria:** ML predictions feel realistic. Chat assistant gives helpful transit advice. Route data passes the "sniff test" — nothing obviously wrong.

---

## Phase 4 — UI/UX & Demo Polish | 3-4 hours | Sat 10:00 PM

Make it look and feel like a polished product for the demo. This is the late-night push.

### Visual Polish

- [ ] Verify glassmorphism theme looks good (backdrop-blur, transparency)
- [ ] Check route colors are distinct and meaningful:
  - Transit: blue (#3b82f6)
  - Driving: purple (#8b5cf6)
  - Walking: green (#10b981)
  - Cycling: orange (#f59e0b)
  - Hybrid: gradient
- [ ] Verify map is centered on Toronto (43.6532, -79.3832) on load
- [ ] Verify route polylines render cleanly (no gaps, no weird loops)
- [ ] Check that vehicle markers pulse/animate on map
- [ ] Test the loading overlay appears during route calculation
- [ ] Make sure the chat panel doesn't overlap important UI elements

### Responsive & Edge Cases

- [ ] Test on the screen size you'll use for the demo (likely laptop)
- [ ] Verify sidebar collapses cleanly
- [ ] Test with 1 route result, 3 route results, and 0 route results
- [ ] Handle "no routes found" gracefully (user-friendly message)
- [ ] Handle API errors gracefully (not just blank screen or console errors)

### Demo-Specific Prep

- [ ] Pick 2-3 origin/destination pairs that showcase the app well:
  - **Demo Route 1:** Suburban → Downtown (shows hybrid option advantage)
    - e.g., Vaughan Metropolitan Centre → Union Station
  - **Demo Route 2:** Cross-town (shows transit vs driving tradeoff)
    - e.g., Scarborough Centre → Kipling Station
  - **Demo Route 3:** Short trip (shows walking as viable option)
    - e.g., King Station → St. Andrew Station
- [ ] Pre-test these routes to make sure they produce good results
- [ ] Prepare a few chat prompts that get impressive AI responses
- [ ] Make sure live alerts are showing something (even if simulated)

### Documentation Updates

- [ ] Update `README.md`:
  - [ ] Replace all "Claude" / "Anthropic" references with "Gemini" / "Google"
  - [ ] Add multi-agency support description (if implemented)
  - [ ] Update setup instructions for OTP (if integrated)
  - [ ] Add screenshots if time permits
- [ ] Update `CLAUDE.md`:
  - [ ] Fix all `claude_agent.py` references → `gemini_agent.py`
  - [ ] Fix `ANTHROPIC_API_KEY` references → `GEMINI_API_KEY`
  - [ ] Add OTP architecture section (if integrated)
  - [ ] Add new GTFS data directories to project structure
- [ ] Update `API_KEYS_SETUP.md` with current key requirements

**Exit Criteria:** App looks polished on demo screen. Demo routes are pre-tested and impressive. Documentation matches the actual codebase.

---

## Phase 5 — Final Submission Prep | 1-2 hours | Sun 1:00 AM

**Code freeze at 3:00 AM.** After that, only bug fixes. Get some rest before 9 AM.

### Final Testing (Sun ~1:00 AM - 2:00 AM)

- [ ] Full cold-start test: kill all servers, restart from scratch
  ```bash
  # Terminal 1: OTP (if using)
  cd otp && java -Xmx2G -jar otp-shaded.jar --load data

  # Terminal 2: Backend
  cd backend && python3 -m uvicorn app.main:app --reload

  # Terminal 3: Frontend
  cd frontend && npm run dev
  ```
- [ ] Run through all 3 demo routes end-to-end
- [ ] Test chat assistant with 2-3 questions
- [ ] Verify no console errors, no crashes
- [ ] Check that real-time data is flowing (vehicles on map, alerts in banner)

### Git & Submission (Sun ~2:00 AM - 3:00 AM)

- [ ] Commit ALL changes with a clean commit message
- [ ] Push to GitHub: `git push origin main`
- [ ] Verify the repo looks good on GitHub (README renders, files are there)
- [ ] Double-check `.gitignore` — no API keys, no node_modules, no .env files committed
- [ ] Tag the submission: `git tag -a v1.0-hackathon -m "CTRL+HACK+DEL 2025 submission"`

### Submission Materials

- [ ] Prepare a 1-paragraph project summary (for submission form)
- [ ] Note all tech used: Next.js 14, FastAPI, Mapbox GL, XGBoost, Google Gemini, OpenTripPlanner, Transitland, TTC GTFS, Tailwind CSS
- [ ] List team members
- [ ] Have the GitHub repo URL ready
- [ ] Have the local demo ready to screen-share (if virtual) or run on laptop (if in-person)

### Code Freeze (Sun 3:00 AM)

**STOP adding features.** Only fix breaking bugs after this point.

- [ ] If something is broken, fix it. If something is missing, skip it.
- [ ] Make sure the app starts cleanly and the demo routes work.

### Backup Plan

- [ ] If OTP isn't working: fall back to existing TTC-only routing (it works!)
- [ ] If GTFS-RT is flaky: mock data fallback is already built in
- [ ] If Gemini API is rate-limited: chat returns friendly error, app still works
- [ ] If ML model is acting up: heuristic fallback is solid

### Rest (Sun 3:00 AM - 9:00 AM)

- [ ] Get some sleep or at least rest before the submission window
- [ ] Set an alarm for 8:00 AM to do a final sanity check
- [ ] At 8:30 AM: verify servers are running, do one last demo walkthrough

**Exit Criteria:** App submitted. Repo pushed. Demo-ready. Get some rest.

---

## Data Sources & API Reference

### GTFS Static Feeds (Download Once)

| Agency | Source | URL | Notes |
|--------|--------|-----|-------|
| **TTC** | Toronto Open Data | [CKAN Link](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169) | Already downloaded |
| **GO Transit** | Metrolinx Open Data | [Metrolinx](https://www.metrolinx.com/en/about-us/open-data) | Covers GO Bus + Train |
| **YRT/Viva** | York Region Open Data | [YRT](https://www.yrt.ca/en/about-us/open-data.aspx) | York Region Transit |
| **MiWay** | Mississauga Open Data | [MiWay](https://www.mississauga.ca/services-and-programs/transportation-and-streets/miway/developer-download/) | Mississauga Transit |
| **Brampton Transit** | Brampton Open Data | [Brampton GeoHub](https://geohub.brampton.ca/) | Brampton/Züm |
| **All of the above** | **Transitland** | [transit.land/feeds](https://transit.land/feeds) | One-stop shop for all feeds |

### GTFS-RT Real-Time Feeds

| Agency | Feed Type | URL / Notes |
|--------|-----------|-------------|
| **TTC** | Vehicle Positions | `https://alerts.ttc.ca/api/alerts/live-map/getVehicles` |
| **TTC** | Service Alerts | `https://alerts.ttc.ca/api/alerts/list` |
| **Metrolinx/GO** | GTFS-RT | Metrolinx Open Data API (may require key) |
| **Transitland** | RT Proxy | Transitland can proxy GTFS-RT for some feeds |

### APIs Used

| API | Purpose | Auth | Free Tier |
|-----|---------|------|-----------|
| **Mapbox** | Maps, directions, geocoding | Token (`pk.`) | 50K map loads, 100K directions/mo |
| **Google Gemini** | AI chat assistant | API key | Free tier (rate-limited) |
| **Open-Meteo** | Weather data | None | Unlimited, no key needed |
| **OpenTripPlanner** | Multi-agency transit routing | None (self-hosted) | Fully free/open-source |
| **Transitland** | GTFS feed discovery | API key (free tier) | Free tier available |

### Key Environment Variables

```bash
# backend/.env
GEMINI_API_KEY=your-gemini-api-key        # Google AI Studio
MAPBOX_TOKEN=pk.your-mapbox-token         # Mapbox account
METROLINX_API_KEY=optional                # Metrolinx Open Data
TRANSITLAND_API_KEY=optional              # transit.land
OTP_BASE_URL=http://localhost:8080        # OpenTripPlanner (if self-hosted)

# frontend/.env.local
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your-mapbox-token
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OTP setup takes too long | Medium | High | Skip OTP, use existing TTC-only routing (works fine for demo) |
| GTFS-RT feeds require auth we can't get | Medium | Medium | Mock data fallback already built in |
| Gemini API rate limit during demo | Low | High | Pre-cache some chat responses; heuristic fallback |
| Mapbox free tier exceeded | Very Low | High | Unlikely in hackathon; have Leaflet as backup plan |
| OSM data download too slow | Medium | Medium | Use smaller GTA-only extract from BBBike instead of all Ontario |
| XGBoost training fails | Low | Low | Heuristic predictor is already working |
| CORS issues with OTP | Medium | Low | Add proxy route in FastAPI to forward OTP requests |
| Team runs out of time | Medium | High | Every phase has a demoable checkpoint. Ship what you have. |

---

## Decision Log

Track major decisions here so the team stays aligned.

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Migrated from Anthropic Claude to Google Gemini | Cost/availability for hackathon | Feb 2025 |
| 2 | Using Mapbox over Google Maps | Generous free tier, better DX | Feb 2025 |
| 3 | XGBoost for delay prediction | Fast to train, works well on tabular data | Feb 2025 |
| 4 | Adding OpenTripPlanner for routing | Industry-standard, handles multi-agency natively | Feb 14 |
| 5 | Using Transitland for feed discovery | Unified source for all GTHA agency data | Feb 14 |
| 6 | Keeping all fallbacks in place | Demo reliability > feature completeness | Feb 14 |

---

## Quick Reference: Key Commands

```bash
# Start everything (3 terminals)

# Terminal 1: OTP (if set up)
cd otp && java -Xmx2G -jar otp-shaded.jar --load data

# Terminal 2: Backend
cd backend && python3 -m uvicorn app.main:app --reload

# Terminal 3: Frontend
cd frontend && npm run dev

# Train ML model
cd backend && python3 -m ml.train_model

# Test API
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin":{"lat":43.7804,"lng":-79.4153},"destination":{"lat":43.6453,"lng":-79.3806}}'

# Test OTP (if running)
curl "http://localhost:8080/otp/routers/default/plan?fromPlace=43.6532,-79.3832&toPlace=43.7804,-79.4153&mode=TRANSIT,WALK"
```

---

**Remember:** A working demo with fewer features beats a broken demo with everything. Ship early, ship often, keep the fallbacks.

---

## Timeline At-a-Glance

```
SAT FEB 15
──────────
 3:00 AM   Planning done. Go to sleep.
10:00 AM   Phase 0 — Critical fixes, verify app runs
11:30 AM   Phase 1 — Train ML model, lock in all features
 2:00 PM   Phase 2 — GTFS data download, OTP setup, real-time feeds (BIGGEST BLOCK)
 7:00 PM   Phase 3 — Tune ML predictions, polish Gemini chat
10:00 PM   Phase 4 — UI polish, pre-test demo routes, update docs

SUN FEB 16
──────────
 1:00 AM   Phase 5 — Cold-start test, git push, tag submission
 3:00 AM   CODE FREEZE — no new features, only critical bug fixes
 6:00 AM   Rest / sleep
 8:00 AM   Wake up, final sanity check
 9:00 AM   DEADLINE
```

Good luck, Team FluxRoute!
