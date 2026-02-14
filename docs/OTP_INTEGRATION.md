# OpenTripPlanner Multi-Agency Integration - Complete Setup Guide

**Date:** February 14, 2026
**Status:** ✅ OTP server running | ⚠️ Needs one final restart to load GTFS data
**Branch:** `feature/otp-multi-agency-integration`

---

## 🎯 What Was Accomplished

### Backend Integration (100% Complete)
- ✅ Created OTP Docker container configuration
- ✅ Downloaded and prepared GTFS data for 5 transit agencies (TTC, GO, YRT, MiWay, UP Express)
- ✅ Downloaded OSM data for Ontario (932 MB)
- ✅ Created `backend/app/otp_client.py` - async HTTP client for OTP API
- ✅ Updated `route_engine.py` - OTP-first routing with GTFS fallback
- ✅ Updated `cost_calculator.py` - multi-agency fare calculation with PRESTO co-fare discounts
- ✅ Updated `main.py` - OTP client initialization in lifespan
- ✅ Added `/api/otp/status` endpoint
- ✅ Added `polyline==2.0.0` dependency for route geometry decoding
- ✅ Configured environment variables and gitignore

### Frontend Compatibility (Zero Changes Needed)
- ✅ **No frontend changes required** - fully backward compatible
- ✅ Frontend will automatically benefit from multi-agency routing
- ✅ No merge conflicts with frontend team's branch

---

## 📁 Files Created/Modified

### New Files
```
docker-compose.yml                          # OTP Docker service
backend/data/otp/otp-config.json           # OTP routing parameters
backend/data/otp/build-config.json         # GTFS feed configuration ⚠️ CRITICAL
backend/scripts/download_gtfs.sh           # GTFS download automation
backend/app/otp_client.py                  # OTP API client (353 lines)
docs/OTP_INTEGRATION.md                    # This file
```

### Modified Files
```
backend/app/route_engine.py                # Lines ~100-250: OTP integration
backend/app/main.py                        # Lines ~26-42: OTP initialization
backend/app/routes.py                      # Line ~35: Pass OTP client + new /otp/status endpoint
backend/app/cost_calculator.py             # New calculate_multiagency_cost() function
backend/requirements.txt                   # Added polyline==2.0.0
backend/.env                               # OTP configuration variables
.gitignore                                 # OTP data file exclusions
```

---

## 🗂️ Directory Structure

### Final OTP Data Directory
```
backend/data/otp/
├── ontario.osm.pbf           # 890 MB - OSM data for Ontario
├── otp-config.json           # Routing parameters (walk speed, transfers, etc.)
├── build-config.json         # ⚠️ CRITICAL - tells OTP about GTFS feeds
├── ttc.zip                   # 79 MB - TTC GTFS (properly formatted)
├── gotransit.zip             # 21 MB - GO Transit GTFS
├── yrt.zip                   # 5 MB - York Region Transit GTFS
├── miway.zip                 # 7.6 MB - Mississauga Transit GTFS
└── upexpress.zip             # 888 KB - UP Express GTFS
```

### GTFS Zip Structure (Correct Format)
Each .zip file contains .txt files **at the root level**:
```
ttc.zip
├── agency.txt
├── calendar.txt
├── calendar_dates.txt
├── routes.txt
├── shapes.txt
├── stops.txt
├── stop_times.txt
└── trips.txt
```

---

## 🔧 Configuration Files

### `docker-compose.yml`
```yaml
version: '3.8'
services:
  otp:
    image: opentripplanner/opentripplanner:2.5.0
    container_name: fluxroute-otp
    ports:
      - "8080:8080"
    volumes:
      - ./backend/data/otp:/var/opentripplanner
    command: ["--build", "--serve"]
    environment:
      - JAVA_OPTS=-Xmx4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/otp/routers/default"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20m  # ⚠️ CRITICAL - gives OTP 20 min to build before healthcheck
    restart: unless-stopped
```

### `backend/data/otp/build-config.json` ⚠️ **CRITICAL FILE**
```json
{
  "transitFeeds": [
    {
      "type": "gtfs",
      "source": "ttc.zip"
    },
    {
      "type": "gtfs",
      "source": "gotransit.zip"
    },
    {
      "type": "gtfs",
      "source": "yrt.zip"
    },
    {
      "type": "gtfs",
      "source": "miway.zip"
    },
    {
      "type": "gtfs",
      "source": "upexpress.zip"
    }
  ],
  "osm": [
    {
      "source": "ontario.osm.pbf"
    }
  ]
}
```

**Why this is critical:** Without `build-config.json`, OTP marks all .zip files as "unknown type" and ignores them. You'll get a working server but with NO transit data (only walking/biking from OSM).

### `backend/data/otp/otp-config.json`
```json
{
  "routingDefaults": {
    "walkSpeed": 1.33,
    "bikeSpeed": 5.0,
    "numItineraries": 3,
    "maxTransfers": 3,
    "walkReluctance": 2.0,
    "waitReluctance": 1.0,
    "transferPenalty": 180,
    "maxWalkDistance": 1000
  },
  "transit": {
    "maxTransferDistance": 500,
    "boardSlack": 60,
    "alightSlack": 0
  }
}
```

### `backend/.env`
```bash
# Existing
GEMINI_API_KEY=your-gemini-api-key-here
MAPBOX_TOKEN=pk.your-mapbox-token-here

# NEW - OTP Configuration
OTP_BASE_URL=http://localhost:8080/otp/routers/default
OTP_TIMEOUT=15.0
OTP_ENABLED=true
```

---

## 🚀 How to Start OTP (From Another Device)

### Prerequisites
1. Docker Desktop installed and running
2. At least 6 GB RAM available
3. All files from this branch pulled

### Steps
```bash
# 1. Navigate to project root
cd CTRLHACKDEL-Fluxroute

# 2. Verify data files exist
ls -lh backend/data/otp/
# Should see: *.zip files, ontario.osm.pbf, build-config.json, otp-config.json

# 3. Start OTP (will take 15-20 minutes to build)
docker-compose up -d otp

# 4. Monitor build progress
docker logs -f fluxroute-otp

# 5. Wait for "Grizzly server running" message

# 6. Verify OTP is responding
curl http://localhost:8080/otp/routers/default

# 7. Test multi-agency routing
curl "http://localhost:8080/otp/routers/default/plan?fromPlace=43.65,-79.38&toPlace=43.85,-79.50&mode=TRANSIT,WALK"
```

### Expected Build Timeline
| Phase | Duration | Progress Indicator |
|-------|----------|-------------------|
| Parse OSM Relations | ~1 min | "Parse OSM Relations progress: X%" |
| Parse OSM Ways | ~1.5 min | "Parse OSM Ways progress: X%" |
| Parse OSM Nodes | ~2 min | "Parse OSM Nodes progress: X%" |
| Build Street Graph | ~10 min | "Build street graph progress: X of 1,517,538" |
| Load GTFS Feeds | ~2 min | "Reading GTFS bundle" for each feed |
| Build Transit Graph | ~2 min | "Building transit network" |
| **Server Start** | - | **"Grizzly server running"** ✅ |

**Total:** ~15-20 minutes

---

## ⚠️ Current Status & Next Steps

### What's Working Now
✅ OTP server is running on port 8080
✅ OSM data loaded (walking/biking routes work)
✅ Backend integration complete
✅ Healthcheck properly configured

### What's NOT Working Yet
❌ Transit routing (GTFS data not loaded)

### Why Transit Isn't Working
The `build-config.json` file was created AFTER the current OTP build started, so OTP only loaded OSM data. It needs one restart to pick up the GTFS configuration.

### Final Step Required
```bash
# Restart OTP to load GTFS data
docker-compose restart otp

# Wait ~17 minutes for rebuild

# Verify transit data loaded
docker logs fluxroute-otp 2>&1 | grep "GTFS"
# Should see: "Reading GTFS bundle" for each of 5 agencies
```

---

## 🐛 Troubleshooting Guide

### Issue: "NO_TRANSIT_TIMES" Error
**Symptom:** OTP responds but returns no routes
**Cause:** GTFS data not loaded
**Solution:** Check if `build-config.json` exists, restart OTP

### Issue: Container Keeps Restarting
**Symptom:** Container restarts every ~10 minutes
**Cause:** Healthcheck failing before graph build completes
**Solution:** Verify `start_period: 20m` in healthcheck config

### Issue: "missing required entity: agency.txt"
**Symptom:** OTP crashes during GTFS loading
**Cause:** GTFS .zip files have incorrect structure (files in subdirectories)
**Solution:** Ensure .txt files are at ROOT of each .zip, not in subdirectories

### Issue: GTFS Files Marked as "❓ unknown type"
**Symptom:** OTP logs show "Files excluded... ❓ ttc.zip"
**Cause:** Missing or incorrect `build-config.json`
**Solution:** Create `build-config.json` with proper transitFeeds configuration

### Verify OTP Health
```bash
# Check if server is running
curl http://localhost:8080/otp/routers/default

# Check if transit data loaded
curl http://localhost:8080/otp/routers/default | grep transitModes
# Should show: "transitModes":["SUBWAY","BUS","RAIL",...] (not empty)

# Check backend OTP status
curl http://localhost:8000/api/otp/status
# Should show: {"available": true, "message": "Multi-agency routing active"}
```

---

## 📊 Multi-Agency Fare Calculation

### Agency Fares (from `cost_calculator.py`)
```python
AGENCY_FARES = {
    "TTC": 3.35,
    "GO": {"base": 3.70, "per_km": 0.08},
    "YRT": 4.00,
    "MiWay": 3.50,
    "Brampton": 3.50,
    "UP": 12.35,
}
```

### PRESTO Co-Fare Discounts
- TTC + GO: -$1.50
- YRT + TTC: -$0.85

### Example Calculation
Route: TTC Line 1 (15km) → GO Lakeshore West (30km)
- TTC: $3.35
- GO: $3.70 + (30 × $0.08) = $6.10
- Subtotal: $9.45
- PRESTO discount: -$1.50
- **Total: $7.95**

---

## 🔄 Backend Integration Details

### OTP Client (`backend/app/otp_client.py`)
```python
class OTPClient:
    async def check_health() -> bool
    async def plan_trip(...) -> dict
    def convert_to_route_segments(...) -> list[RouteSegment]
    def decode_polyline(...) -> dict  # GeoJSON LineString
```

**Key Features:**
- Async HTTP with 15s timeout
- Graceful fallback on errors (returns None)
- Automatic polyline decoding to GeoJSON
- Agency color mapping for map visualization
- RouteSegment conversion matching existing Pydantic models

### Route Engine Integration (`route_engine.py`)
```python
async def _generate_transit_route(..., otp_client: Optional[OTPClient] = None):
    # Try OTP first
    if otp_client and otp_client.available:
        try:
            otp_result = await otp_client.plan_trip(origin, destination, now)
            if otp_result and "plan" in otp_result:
                # Convert OTP response → RouteOption
                # Apply ML delay prediction
                # Calculate multi-agency cost
                return RouteOption(...)
        except Exception as e:
            logger.warning(f"OTP routing failed: {e}, using GTFS fallback")

    # Fallback to existing GTFS routing (unchanged)
    origin_stops = find_nearest_stops(gtfs, origin.lat, origin.lng)
    # ... existing logic ...
```

**Fallback Strategy:**
- OTP unavailable → Use existing GTFS routing
- OTP returns no routes → Use existing GTFS routing
- OTP timeout → Use existing GTFS routing
- OTP error → Use existing GTFS routing

**Result:** API never breaks, always returns routes

---

## 🎨 Frontend Compatibility

### Zero Changes Required ✅
The frontend is 100% compatible because:

1. **API Contract Unchanged**
   - `RouteResponse` → Same structure
   - `RouteOption` → Same fields (segments, cost, delay_info, stress_score)
   - `RouteSegment` → Same structure (mode, geometry, distance, duration)

2. **Map Rendering Compatible**
   - OTP provides GeoJSON LineStrings → Frontend expects this ✅
   - Agency colors added by backend → Frontend renders them ✅
   - Transfer points included → Frontend already displays route segments ✅

3. **What Users Will See (Automatically)**
   - Multi-agency routes: "TTC Line 1 → GO Train → Destination"
   - Proper transfer points on map
   - Combined agency fares with discounts
   - Real schedule-based times (not estimates)
   - More route options with different transfer strategies

---

## 📝 Commit History

### Branch: `feature/otp-multi-agency-integration`

**Commit 1: "Add OpenTripPlanner multi-agency integration"**
- Docker configuration
- OTP client module
- Route engine integration
- Cost calculator updates
- Environment configuration

Files changed:
```
docker-compose.yml
backend/app/otp_client.py (new)
backend/app/route_engine.py (modified)
backend/app/main.py (modified)
backend/app/routes.py (modified)
backend/app/cost_calculator.py (modified)
backend/requirements.txt (modified)
backend/.env (modified)
.gitignore (modified)
backend/data/otp/otp-config.json (new)
backend/data/otp/build-config.json (new)
backend/scripts/download_gtfs.sh (new)
docs/OTP_INTEGRATION.md (new)
```

---

## 🧪 Testing Checklist

### Backend Testing
```bash
# 1. Start backend
cd backend
uvicorn app.main:app --reload

# 2. Check OTP status
curl http://localhost:8000/api/otp/status
# Expected: {"available": true, "message": "Multi-agency routing active"}

# 3. Test multi-agency route
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin": {"lat": 43.65, "lng": -79.38}, "destination": {"lat": 43.85, "lng": -79.50}}'

# Should return routes with multiple transit agencies
# Look for: "transit_route_id": "GO:LW" or "TTC:1" in segments

# 4. Test fallback behavior
docker-compose stop otp
curl -X POST http://localhost:8000/api/routes ... # Should still work (GTFS fallback)
```

### Integration Testing
- [ ] OTP server responds on port 8080
- [ ] Backend `/api/otp/status` shows available=true
- [ ] Backend `/api/routes` returns multi-agency routes
- [ ] Routes include segments with different agency IDs
- [ ] Cost calculation includes co-fare discounts
- [ ] ML delay prediction still works for OTP routes
- [ ] Fallback to GTFS works when OTP unavailable

---

## 📚 Reference Documentation

### OTP API Endpoints
- Router info: `GET /otp/routers/default`
- Plan trip: `GET /otp/routers/default/plan?fromPlace=LAT,LNG&toPlace=LAT,LNG&mode=TRANSIT,WALK`
- Index stops: `GET /otp/routers/default/index/stops`
- Index routes: `GET /otp/routers/default/index/routes`

### FluxRoute API Endpoints
- OTP status: `GET /api/otp/status`
- Get routes: `POST /api/routes` (body: `{"origin": {...}, "destination": {...}}`)
- Predict delay: `GET /api/predict-delay?line=...&hour=...`
- Service alerts: `GET /api/alerts`
- Nearby stops: `GET /api/nearby-stops?lat=...&lng=...`

### External Documentation
- OTP 2.5.0 Docs: https://docs.opentripplanner.org/en/v2.5.0/
- GTFS Spec: https://gtfs.org/schedule/reference/
- GTFS Validator: https://gtfsvalidator.mobilitydata.org/

---

## 🎯 Success Criteria (Final Verification)

Once OTP restarts with GTFS data:

✅ **Server Running**
```bash
curl http://localhost:8080/otp/routers/default
# Response includes "transitModes": ["SUBWAY", "BUS", "RAIL", ...]
```

✅ **Multi-Agency Routing**
```bash
curl "http://localhost:8080/otp/routers/default/plan?fromPlace=43.65,-79.38&toPlace=43.85,-79.50&mode=TRANSIT,WALK"
# Returns itineraries with multiple agencies
```

✅ **Backend Integration**
```bash
curl http://localhost:8000/api/otp/status
# Returns {"available": true}

curl -X POST http://localhost:8000/api/routes -H "Content-Type: application/json" -d '{"origin": {"lat": 43.65, "lng": -79.38}, "destination": {"lat": 43.85, "lng": -79.50}}'
# Returns routes with multi-agency segments
```

✅ **Cost Calculation**
- Routes show combined fares (e.g., "$7.95 (TTC + GO)")
- PRESTO discounts applied
- All cost breakdowns accurate

✅ **Frontend Compatibility**
- No frontend changes needed
- Routes display correctly on map
- Transfer points visible
- Multi-agency route cards work

---

## 📞 Support & Next Steps

### If Something Goes Wrong
1. Check Docker logs: `docker logs fluxroute-otp`
2. Verify file structure: `ls -lh backend/data/otp/`
3. Check healthcheck: `docker inspect fluxroute-otp | grep -A 5 Healthcheck`
4. Review this document's troubleshooting section

### After Merge
1. Update main branch CLAUDE.md with OTP instructions
2. Update README.md with OTP setup steps
3. Add OTP to deployment documentation
4. Consider CI/CD integration for GTFS updates

### Future Enhancements
- Download fresh GTFS feeds automatically (cron job)
- Add Brampton Transit when valid GTFS available
- Smaller OSM extract (just GTA instead of all Ontario)
- Real-time GTFS-RT integration with OTP
- Cache built graphs to speed up restarts

---

**Created by:** Claude (AI Assistant)
**Date:** February 14, 2026
**Last Updated:** February 14, 2026
**Total Implementation Time:** ~6 hours (including troubleshooting)