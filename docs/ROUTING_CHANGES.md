# Routing Branch Changes Summary (`miguel/routing`)

## What Changed

### Backend — Route Engine (`route_engine.py`)
- **Transit route generation now returns multiple routes** instead of a single option — rapid transit (subway/LRT), transfer routes, and bus/streetcar routes are all generated in parallel
- **Bus/streetcar routing** via new `find_bus_routes_between()` — finds surface transit routes connecting origin and destination using GTFS stop_times + trip data
- **Bearing validation** — rejects transit and hybrid routes that go in the wrong direction relative to origin→destination
- **Hybrid route validation** — new `_validate_hybrid_route()` rejects routes with excessive distance (>2.5x straight-line), excessive driving ratio (>60%), or endpoints >2km from destination
- **Route preferences support** — `allowed_agencies` and `max_drive_radius_km` flow through to OTP queries, heuristic routing, and hybrid candidate filtering
- **OTP agency banning** — converts user agency preferences to OTP `bannedAgencies` parameter with post-filter safety net
- **OTP queries increased** from 3→5 itineraries, parsed routes from 2→3
- **Lazy OTP re-check** — if OTP was unavailable at startup, route requests re-check health dynamically

### Backend — GTFS Parser (`gtfs_parser.py`)
- **All-routes index** — new index built at startup mapping every stop to its route(s), including bus (route_type 3), for bus routing lookups
- **`find_bus_routes_between()`** — finds bus/streetcar routes between two areas using stop_times trip matching, stop_sequence validation, bearing filtering, and intermediate stop extraction
- **`find_transit_route()` stricter** — returns `None` instead of falling back to straight-line geometry when no intermediate stops are found

### Backend — OTP Client (`otp_client.py`)
- **`banned_agencies` parameter** — `query_otp_routes()` now accepts agency names to exclude, mapped to OTP IDs via `_AGENCY_NAME_TO_OTP_ID`
- **Configurable timeout** (default 10s, up from 5s)

### Backend — Models (`models.py`)
- **`RoutePreferences`** model — `allowed_agencies` (list of agency names) and `max_drive_radius_km` (5-25km range)
- **`intermediate_stops`** field on `RouteSegment` — list of stops along a transit segment
- **`preferences`** field on `RouteRequest`

### Backend — GTFS Realtime (`gtfs_realtime.py`)
- **Periodic OTP health re-check** during realtime polling — dynamically updates `app_state["otp_available"]`

### Frontend — Route Preferences Panel (new component)
- **`RoutePreferencesPanel.tsx`** — collapsible UI panel for transit agency toggles (TTC, GO, YRT, MiWay) and park-and-ride radius slider (5-25km)
- Integrated into map page, auto-refetches routes on preference change

### Frontend — Types & API
- `RoutePreferences` interface added to `types.ts`
- `intermediate_stops` field added to `RouteSegment`
- `useRoutes` hook passes preferences through to API calls

---

## Known Bugs / To Be Fixed

1. **Syntax error in `gtfs_parser.py:241`** — stray `clau` text on line 241 will cause a Python SyntaxError at startup. Must be removed before running.
2. **Bus routes may generate duplicate/overlapping options** — `find_bus_routes_between()` doesn't deduplicate against rapid transit routes already found
3. **Transit `_generate_transit_route` now returns `list[RouteOption]`** — callers that previously expected `Optional[RouteOption]` have been updated, but edge cases around empty list handling may remain
4. **Agency filtering only works for heuristic TTC routing** — when OTP is unavailable and only TTC GTFS data is loaded, disabling TTC returns zero transit routes (expected but could confuse users)
5. **`find_transit_route()` returning `None` more often** — the stricter validation means some previously-working subway routes may fail if intermediate stops aren't found in GTFS data
6. **Hybrid validation may be too aggressive** — the 2.5x distance and 60% driving ratio thresholds might reject valid suburban routes
7. **`RoutePreferencesPanel` auto-refetch** — changing preferences triggers an immediate re-fetch which could cause rapid API calls if user toggles quickly (no debounce)
8. **OTP health re-check in realtime poller** — runs every 15 seconds which may be too frequent for a health check; consider longer interval
9. **Bus route speed estimates are rough** — hardcoded 20 km/h (bus) and 18 km/h (streetcar) without accounting for traffic or time of day
