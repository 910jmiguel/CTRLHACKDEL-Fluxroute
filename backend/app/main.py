import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # Load .env before any other imports that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("fluxroute")
logging.basicConfig(level=logging.INFO)

# Global state populated during startup
app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data, ML model, and start real-time poller on startup."""
    mapbox_token = os.getenv("MAPBOX_TOKEN", "")
    if not mapbox_token or mapbox_token == "your-mapbox-token-here":
        logger.warning(
            "MAPBOX_TOKEN is missing or placeholder in backend/.env — "
            "driving/walking routes will use straight-line fallback. "
            "Copy backend/.env.example to backend/.env and add your "
            "Mapbox token for road-following routes."
        )

    from app.gtfs_parser import load_gtfs_data
    from app.ml_predictor import DelayPredictor
    from app.gtfs_realtime import start_realtime_poller, stop_realtime_poller

    logger.info("Loading GTFS data...")
    gtfs = load_gtfs_data()
    app_state["gtfs"] = gtfs
    logger.info(f"GTFS loaded: {len(gtfs.get('stops', []))} stops")

    logger.info("Loading ML model...")
    predictor = DelayPredictor()
    predictor.load()
    app_state["predictor"] = predictor
    logger.info(f"ML predictor mode: {predictor.mode}")

    # Check OTP availability
    from app.otp_client import check_otp_health
    otp_available = await check_otp_health()
    app_state["otp_available"] = otp_available
    if otp_available:
        logger.info("OpenTripPlanner is available — using OTP for transit routing")
    else:
        logger.info("OpenTripPlanner not available — using heuristic transit routing (fallback)")

    logger.info("Starting real-time poller...")
    poller_task = await start_realtime_poller(app_state)
    app_state["poller_task"] = poller_task

    yield

    logger.info("Shutting down...")
    await stop_realtime_poller(app_state)


app = FastAPI(title="FluxRoute API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes import router  # noqa: E402

app.include_router(router, prefix="/api")
