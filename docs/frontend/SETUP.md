# FluxRoute Setup Guide

This guide will help you set up the FluxRoute application from scratch.

## Prerequisites

Ensure you have the following installed:

- **Python 3.10+** (Recommend 3.12)
- **Node.js 18+** (Recommend 20+)
- **npm** or **yarn**
- **Git**

## 1. Clone the Repository

```bash
git clone https://github.com/910jmiguel/CTRLHACKDEL-Fluxroute.git
cd CTRLHACKDEL-Fluxroute
```

## 2. Backend Setup

The backend is built with FastAPI and handles routing, ML predictions, and data processing.

### Create Virtual Environment (Optional but Recommended)

It's good practice to use a virtual environment to manage dependencies.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note for macOS users:** If `xgboost` installation fails, you might need `libomp`:
> ```bash
> brew install libomp
> ```

### Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
touch .env
```

Add your API keys to `.env`:

```env
# Google Gemini API Key (for AI Chat)
GEMINI_API_KEY=your_gemini_api_key_here

# Mapbox Access Token (for routing engine fallback)
MAPBOX_TOKEN=your_mapbox_token_here

# Metrolinx API Key (Optional, for GO Transit real-time data)
METROLINX_API_KEY=your_metrolinx_key_here
```

### Download GTFS Data

The app needs GTFS data to function optimally. By default, it looks for data in `backend/data/gtfs`.

```bash
mkdir -p data/gtfs
cd data/gtfs
# Download latest TTC schedules (URL may change, verify on Toronto Open Data)
curl -L -o gtfs.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"
unzip gtfs.zip && rm gtfs.zip
cd ../..
```

### Train the ML Model

Train the delay prediction model using the provided TTC delay data.

```bash
python3 -m ml.train_model
```

This will generate `backend/ml/delay_model.joblib`.

### Run the Backend Server

```bash
python3 -m uvicorn app.main:app --reload
```

The API will be running at `http://localhost:8000`. You can check the documentation at `http://localhost:8000/docs`.

## 3. Frontend Setup

The frontend is a Next.js application.

### Install Dependencies

Open a new terminal window and navigate to the frontend directory:

```bash
cd frontend
npm install
```

### Configure Environment Variables

Create a `.env.local` file in the `frontend` directory:

```bash
touch .env.local
```

Add the following (Note the `NEXT_PUBLIC_` prefix):

```env
# Mapbox Token (Required for the map component)
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_public_token_here

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run the Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## 4. Verification

1.  Ensure Backend is running on port 8000.
2.  Ensure Frontend is running on port 3000.
3.  Open `http://localhost:3000` in your browser.
4.  Try searching for a route (e.g., "Union Station" to "Finch Station").

## Troubleshooting

-   **Map not loading?** Check your `NEXT_PUBLIC_MAPBOX_TOKEN` in `frontend/.env.local`.
-   **Chat not working?** Check your `GEMINI_API_KEY` in `backend/.env`.
-   **No routes found?** Ensure the backend has loaded the GTFS data correctly (check backend logs).
-   **"Module not found" errors?** Make sure you activated the virtual environment (`backend`) and ran `npm install` (`frontend`).
