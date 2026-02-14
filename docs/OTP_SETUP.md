# OpenTripPlanner (OTP) Setup Guide

Quick setup guide for running OTP natively with FluxRoute's multi-agency GTFS data.

---

## Prerequisites

- **Java 17+** (OTP 2.5 requires Java 17 minimum)
- **8 GB RAM** available (OTP graph build is memory-intensive)
- **Git LFS** installed (large data files are tracked with LFS)

### Install Prerequisites (macOS)

```bash
# Java 17
brew install openjdk@17

# Git LFS
brew install git-lfs
git lfs install
```

### Verify Java

```bash
java -version
# Must show 17 or higher
```

---

## Step 1: Clone & Checkout

```bash
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute
git checkout feature/otp-multi-agency-integration
git lfs pull
```

If you already have the repo:

```bash
git checkout feature/otp-multi-agency-integration
git pull origin feature/otp-multi-agency-integration
git lfs pull
```

---

## Step 2: Download OTP JAR

The OTP JAR (~174 MB) is not stored in git. Download it from Maven Central:

```bash
curl -L -o backend/data/otp/otp-2.5.0-shaded.jar \
  "https://repo1.maven.org/maven2/org/opentripplanner/otp/2.5.0/otp-2.5.0-shaded.jar"
```

Verify the download:

```bash
ls -lh backend/data/otp/otp-2.5.0-shaded.jar
# Should be ~174 MB
```

---

## Step 3: Verify Data Files

```bash
ls -lh backend/data/otp/
```

You should see:

| File | Size | Description |
|------|------|-------------|
| `otp-2.5.0-shaded.jar` | 174 MB | OTP server (downloaded in Step 2) |
| `ontario.osm.pbf` | 890 MB | OpenStreetMap data for Ontario |
| `ttc.zip` | 79 MB | TTC GTFS (subway, bus, streetcar) |
| `gotransit.zip` | 21 MB | GO Transit GTFS (trains, buses) |
| `yrt.zip` | 5 MB | York Region Transit GTFS |
| `miway.zip` | 7.6 MB | Mississauga MiWay GTFS |
| `upexpress.zip` | 888 KB | UP Express GTFS |
| `build-config.json` | <1 KB | Tells OTP which GTFS feeds to load |
| `otp-config.json` | <1 KB | Routing parameters |

If any data files are missing, run:

```bash
git lfs pull
```

---

## Step 4: Build & Run OTP

```bash
cd backend/data/otp

java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve .
```

This will:
1. Parse the OSM file (~3 min)
2. Build the street graph (~10 min)
3. Load all 5 GTFS feeds (~2 min)
4. Start the HTTP server on **port 8080**

**Total build time: ~15-20 minutes** (first run only, subsequent starts are faster if graph is cached)

You'll know it's ready when you see:

```
Grizzly server running
```

---

## Step 5: Verify OTP is Working

In a new terminal:

```bash
# Check server is responding
curl http://localhost:8080/otp/routers/default

# Test a transit route (Finch Station to Union Station)
curl "http://localhost:8080/otp/routers/default/plan?fromPlace=43.7804,-79.4153&toPlace=43.6453,-79.3806&mode=TRANSIT,WALK"
```

The response should include itineraries with transit legs from multiple agencies.

---

## Step 6: Start FluxRoute Backend

In another terminal:

```bash
cd backend
python3 -m uvicorn app.main:app --reload
```

Verify the backend sees OTP:

```bash
curl http://localhost:8000/api/otp/status
# Expected: {"available": true, "message": "Multi-agency routing active"}
```

---

## Step 7: Start Frontend (Optional)

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:3000
```

---

## Architecture

```
Browser (localhost:3000)
    |
    v
Next.js Frontend
    |  HTTP requests
    v
FastAPI Backend (localhost:8000)
    |  /api/routes tries OTP first, falls back to GTFS
    v
OpenTripPlanner (localhost:8080)
    |  Reads GTFS + OSM data
    v
5 Transit Agencies: TTC, GO, YRT, MiWay, UP Express
```

The backend's route engine (`route_engine.py`) queries OTP first. If OTP is unavailable or returns no results, it falls back to the original GTFS-based routing. The frontend requires **zero changes** — the API contract is identical.

---

## Troubleshooting

### OTP crashes with `OutOfMemoryError`

Increase the heap size:

```bash
java -Xmx10G -jar otp-2.5.0-shaded.jar --build --serve .
```

If your machine has less than 8 GB free, close other applications first.

### `java: command not found`

Install Java 17+:

```bash
# macOS
brew install openjdk@17
echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Ubuntu/Debian
sudo apt install openjdk-17-jre
```

### OTP starts but returns no transit routes

Check that `build-config.json` exists in the same directory as the JAR. Without it, OTP ignores the GTFS zip files. You should see log lines like:

```
Reading GTFS bundle ttc.zip
Reading GTFS bundle gotransit.zip
...
```

If you see `unknown type` warnings for the zip files, the `build-config.json` is missing or malformed.

### Port 8080 already in use

```bash
# Find what's using the port
lsof -i :8080

# Use a different port
java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve --port 9090 .
```

Then update `OTP_BASE_URL` in `backend/.env` to match.

### Backend says OTP is unavailable

1. Make sure OTP finished building (look for "Grizzly server running")
2. Check `backend/.env` has `OTP_BASE_URL=http://localhost:8080/otp/routers/default`
3. Check `OTP_ENABLED=true` in `backend/.env`

---

## Running with Docker (Alternative)

If you prefer Docker over running the JAR directly:

```bash
# From project root
docker-compose up -d otp

# Monitor build progress
docker logs -f fluxroute-otp

# Wait for "Grizzly server running" (~15-20 min)
```

See `docker-compose.yml` for the full configuration.
