# FluxRoute — Full Setup Guide

One-stop guide to get FluxRoute running from scratch. Every command is copy-pasteable.

> **Already have the basics?** Skip to [Step 8: Run the App](#step-8-run-the-app).

---

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| **Python** | 3.10+ (tested 3.12) | Backend API server |
| **Node.js** | 18+ (tested 22.9.0) | Frontend dev server |
| **Git** | Any recent | Version control |
| **Git LFS** | Any recent | Large data files (GTFS zips, OSM data) |
| **Homebrew** | Latest (macOS only) | Installing `libomp` for XGBoost |
| **Java 17+** | Optional | Running OpenTripPlanner natively (multi-agency routing) |
| **Docker** | Optional | Alternative to Java for running OTP |

### Install prerequisites (macOS)

```bash
# Git LFS
brew install git-lfs

# XGBoost dependency
brew install libomp

# Java 17+ (only if you want OTP multi-agency routing)
brew install openjdk@17
echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Install prerequisites (Ubuntu/Debian)

```bash
# Git LFS
sudo apt install git-lfs

# Java 17+ (only if you want OTP)
sudo apt install openjdk-17-jre
```

---

## Step 1: Clone & Pull LFS Data

```bash
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute
git lfs install
git lfs pull
```

If you already have the repo:

```bash
git pull
git lfs pull
```

---

## Step 2: Backend Setup

### Create a virtual environment (recommended)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

> **macOS users:** If `xgboost` fails to install, run `brew install libomp` first.

```bash
cd ..
```

---

## Step 3: Download TTC GTFS Data

**This step is critical.** Without the GTFS data (specifically `shapes.txt`), transit lines will render as ugly straight lines between stations instead of following actual track geometry along streets and rail corridors. The GTFS feed contains **437,000+ shape waypoints** that make transit routes look correct on the map.

```bash
cd backend/data/gtfs
curl -L -o gtfs.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"
unzip gtfs.zip && rm gtfs.zip
cd ../../..
```

Verify it worked — you should see files like `stops.txt`, `routes.txt`, `shapes.txt`, `trips.txt`, `stop_times.txt`:

```bash
ls backend/data/gtfs/*.txt
```

> **Alternative:** There's a helper script at `backend/scripts/download_gtfs.sh` that downloads GTFS feeds for multiple agencies (TTC, GO, YRT, MiWay) into the OTP data directory. The manual commands above are for the local GTFS parser which only needs TTC data.

---

## Step 4: Environment Variables

You need two `.env` files — one for the backend and one for the frontend.

### Get your API keys

| Key | Where to get it | Cost |
|-----|-----------------|------|
| **Mapbox Token** | [mapbox.com/access-tokens](https://account.mapbox.com/access-tokens/) | Free (50k map loads/month) |
| **Gemini API Key** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Free tier available |
| **Metrolinx API Key** | [gotransit.com/en/open-data](https://www.gotransit.com/en/open-data) | Free (optional) |

See [API_KEYS_SETUP.md](API_KEYS_SETUP.md) for detailed instructions on obtaining each key.

### Create `backend/.env`

```bash
cat > backend/.env << 'EOF'
MAPBOX_TOKEN=pk.your-mapbox-token-here
GEMINI_API_KEY=your-gemini-api-key-here
METROLINX_API_KEY=

# OTP Configuration (only needed if running OpenTripPlanner)
OTP_BASE_URL=http://localhost:8080/otp/routers/default
OTP_TIMEOUT=15.0
OTP_ENABLED=true
EOF
```

Then edit `backend/.env` and replace the placeholder values with your real keys.

### Create `frontend/.env.local`

```bash
cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your-mapbox-token-here
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

Replace the Mapbox token with the same token you used in the backend `.env`.

> **Important:** The Mapbox token must be set in **both** files. The backend uses it for directions/geocoding API calls. The frontend uses it for rendering the map.

---

## Step 5: Train ML Model (Optional)

```bash
cd backend
python3 -m ml.train_model
cd ..
```

This trains an XGBoost model on TTC subway delay data and saves it to `backend/ml/delay_model.joblib`. If you skip this step, the app automatically uses a heuristic fallback that works well — you won't notice a difference in the demo.

---

## Step 6: Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

## Step 7: OTP Setup (Optional — Multi-Agency Routing)

OpenTripPlanner enables routing across **5 GTA transit agencies** (TTC, GO Transit, YRT, MiWay, UP Express) instead of just TTC.

**What you get with OTP:** Real multi-agency itineraries — e.g., "take the TTC subway to Union, transfer to GO Train to Oakville."

**What you get without OTP:** TTC-only routing via the local GTFS parser. Driving, walking, and hybrid routes are unaffected.

If you want multi-agency routing, follow the full guide: **[OTP_SETUP.md](OTP_SETUP.md)**

Quick summary:

```bash
# Download OTP JAR (~174 MB, one-time)
curl -L -o backend/data/otp/otp-2.5.0-shaded.jar \
  "https://repo1.maven.org/maven2/org/opentripplanner/otp/2.5.0/otp-2.5.0-shaded.jar"

# Build graph and start server (~45 min first time, instant after)
cd backend/data/otp
java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve .
```

Wait for `Grizzly server running` before starting the backend.

---

## Step 8: Run the App

Open 2 terminals (3 if running OTP).

### Terminal 1 (optional): OTP Server

```bash
cd backend/data/otp
java -Xmx8G -jar otp-2.5.0-shaded.jar --build --serve .
# Wait for "Grizzly server running"
```

### Terminal 2: Backend

```bash
cd backend
source .venv/bin/activate   # if using a virtual environment
python3 -m uvicorn app.main:app --reload
```

The API will be at **http://localhost:8000**.

### Terminal 3: Frontend

```bash
cd frontend
npm run dev
```

The app will be at:
- **http://localhost:3000** — Landing page
- **http://localhost:3000/map** — Map application

---

## Step 9: Verify Everything Works

### Health check

```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok","service":"FluxRoute API"}
```

### Test route generation

```bash
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin":{"lat":43.7804,"lng":-79.4153},"destination":{"lat":43.6453,"lng":-79.3806}}'
```

You should get back a JSON response with multiple route options (transit, driving, hybrid).

### Check OTP status (if running OTP)

```bash
curl http://localhost:8000/api/otp/status
# Expected: {"available":true,"message":"Multi-agency routing active"}
```

### Visual check

1. Open **http://localhost:3000/map** in your browser
2. Enter an origin and destination (e.g., "Finch Station" to "Union Station")
3. Verify that transit route lines **follow curved track geometry** (not straight lines between stations)
4. Check that driving routes follow actual roads

---

## Troubleshooting

### Transit lines look like straight lines (not following tracks)

**Cause:** Missing GTFS data — specifically `shapes.txt` which contains 437K waypoints for route geometry.

**Fix:** Download GTFS data (Step 3):

```bash
cd backend/data/gtfs
curl -L -o gtfs.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"
unzip gtfs.zip && rm gtfs.zip
```

Then restart the backend.

### Map doesn't load (blank gray area)

**Cause:** Missing or invalid Mapbox token in the frontend.

**Fix:** Check `frontend/.env.local` has `NEXT_PUBLIC_MAPBOX_TOKEN=pk.xxxxx` (must start with `pk.`). Restart the frontend dev server after changing the file.

### Driving routes are straight lines (not following roads)

**Cause:** Missing Mapbox token in the backend. The backend calls Mapbox Directions API for driving geometry.

**Fix:** Check `backend/.env` has `MAPBOX_TOKEN=pk.xxxxx`. Restart the backend.

### AI chat doesn't respond

**Cause:** Missing or invalid Gemini API key.

**Fix:** Check `backend/.env` has `GEMINI_API_KEY=your_key`. Check backend logs for authentication errors. Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

### No routes found / backend errors on route request

**Cause:** GTFS data not loaded on startup.

**Fix:** Check backend startup logs. You should see lines about loading GTFS data. If not, verify `backend/data/gtfs/` contains `.txt` files (Step 3).

### `xgboost` install fails on macOS

**Cause:** Missing OpenMP library.

**Fix:**

```bash
brew install libomp
pip install -r backend/requirements.txt
```

### OTP not detected by backend

**Cause:** OTP wasn't running when the backend started, or wrong URL.

**Fix:**
1. Start OTP first and wait for `Grizzly server running`
2. Check `backend/.env` has `OTP_BASE_URL=http://localhost:8080/otp/routers/default`
3. **Restart the backend** — it only checks OTP availability on startup

### Port already in use

```bash
# Find what's using port 8000 (backend) or 3000 (frontend)
lsof -i :8000
lsof -i :3000

# Kill the process if needed
kill -9 <PID>
```

### Git LFS files not downloading

```bash
git lfs install
git lfs pull
```

If files in `backend/data/otp/` are tiny (< 1 KB), they're LFS pointers that haven't been pulled yet.
