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
