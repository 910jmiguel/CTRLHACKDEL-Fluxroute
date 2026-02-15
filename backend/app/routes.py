import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models import (
    ChatRequest,
    ChatResponse,
    Coordinate,
    CustomRouteRequest,
    DelayPredictionResponse,
    LineStopsResponse,
    LineStop,
    RouteMode,
    RouteRequest,
    RouteResponse,
)

logger = logging.getLogger("fluxroute.routes")

router = APIRouter()


def _get_state():
    from app.main import app_state
    return app_state


@router.get("/health")
async def health():
    return {"status": "ok", "service": "FluxRoute API"}


@router.get("/otp/status")
async def get_otp_status():
    """Check connection to OpenTripPlanner."""
    state = _get_state()
    available = state.get("otp_available", False)
    return {
        "available": available,
        "message": "Multi-agency routing active" if available else "Using GTFS fallback",
    }


@router.post("/routes", response_model=RouteResponse)
async def get_routes(request: RouteRequest):
    """Generate multimodal route options."""
    from app.route_engine import generate_routes

    state = _get_state()
    gtfs = state.get("gtfs", {})
    predictor = state.get("predictor")

    if not predictor:
        raise HTTPException(status_code=503, detail="ML predictor not initialized")

    routes = await generate_routes(
        origin=request.origin,
        destination=request.destination,
        gtfs=gtfs,
        predictor=predictor,
        modes=request.modes,
        app_state=state,
    )

    return RouteResponse(
        routes=routes,
        origin=request.origin,
        destination=request.destination,
    )


@router.get("/predict-delay", response_model=DelayPredictionResponse)
async def predict_delay(
    line: str = Query(..., description="TTC line name"),
    station: Optional[str] = Query(None),
    hour: int = Query(12),
    day_of_week: int = Query(0),
    month: Optional[int] = Query(None),
    mode: str = Query("subway", description="Transit mode (subway, bus, streetcar)"),
):
    """Get ML delay prediction for a specific line/time."""
    state = _get_state()
    predictor = state.get("predictor")

    if not predictor:
        raise HTTPException(status_code=503, detail="ML predictor not initialized")

    result = predictor.predict(
        line=line,
        station=station,
        hour=hour,
        day_of_week=day_of_week,
        month=month,
        mode=mode,
    )

    return DelayPredictionResponse(**result)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with Gemini AI assistant."""
    from app.gemini_agent import chat_with_gemini

    state = _get_state()
    try:
        response = await chat_with_gemini(
            message=request.message,
            history=request.history,
            context=request.context,
            app_state=state,
        )
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            message="I'm sorry, I'm having trouble connecting right now. Please try again in a moment.",
            suggested_actions=["Check service status", "Try a different question"],
        )


@router.get("/alerts")
async def get_alerts():
    """Get cached GTFS-RT service alerts."""
    state = _get_state()
    alerts = state.get("alerts", [])
    return {"alerts": [a.model_dump() if hasattr(a, 'model_dump') else a for a in alerts]}


@router.get("/vehicles")
async def get_vehicles():
    """Get cached vehicle positions."""
    state = _get_state()
    vehicles = state.get("vehicles", [])
    return {"vehicles": [v.model_dump() if hasattr(v, 'model_dump') else v for v in vehicles]}


@router.get("/transit-lines")
async def get_transit_lines():
    """Get cached transit line geometries and station positions for map overlay."""
    state = _get_state()
    transit_data = state.get("transit_lines", {})
    return transit_data


@router.get("/transit-shape/{route_id}")
async def get_transit_shape(route_id: str):
    """Get GeoJSON shape for a transit route."""
    from app.gtfs_parser import get_route_shape

    state = _get_state()
    gtfs = state.get("gtfs", {})

    shape = get_route_shape(gtfs, route_id)
    if not shape:
        raise HTTPException(status_code=404, detail="Shape not found")

    return {"route_id": route_id, "geometry": shape}


@router.get("/nearby-stops")
async def get_nearby_stops(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(2.0),
    limit: int = Query(5),
):
    """Find transit stops near coordinates."""
    from app.gtfs_parser import find_nearest_stops

    state = _get_state()
    gtfs = state.get("gtfs", {})

    stops = find_nearest_stops(gtfs, lat, lng, radius_km, limit)
    return {"stops": stops}


@router.get("/weather")
async def get_weather(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
):
    """Get current weather conditions."""
    from app.weather import get_current_weather

    weather = await get_current_weather(lat, lng)
    return weather


@router.get("/line-stops/{line_id}", response_model=LineStopsResponse)
async def get_line_stops(line_id: str):
    """Get ordered stops for a TTC rapid transit line."""
    from app.gtfs_parser import get_line_stations, TTC_LINE_INFO

    state = _get_state()
    gtfs = state.get("gtfs", {})

    line_info = TTC_LINE_INFO.get(line_id)
    if not line_info:
        raise HTTPException(status_code=404, detail=f"Line '{line_id}' not found")

    stations = get_line_stations(gtfs, line_id)
    stops = [LineStop(stop_id=s["stop_id"], stop_name=s["stop_name"], lat=s["lat"], lng=s["lng"]) for s in stations]

    return LineStopsResponse(
        line_id=line_id,
        line_name=line_info["name"],
        color=line_info["color"],
        stops=stops,
    )


@router.post("/custom-route")
async def calculate_custom_route_endpoint(request: CustomRouteRequest):
    """Calculate a user-defined custom route."""
    from app.route_engine import calculate_custom_route
    from app.weather import get_current_weather

    state = _get_state()
    gtfs = state.get("gtfs", {})
    predictor = state.get("predictor")
    http_client = state.get("http_client")

    if not predictor:
        raise HTTPException(status_code=503, detail="ML predictor not initialized")

    weather = await get_current_weather(request.trip_origin.lat, request.trip_origin.lng)

    route = await calculate_custom_route(
        request=request,
        gtfs=gtfs,
        predictor=predictor,
        http_client=http_client,
        weather=weather,
    )

    return route.model_dump()


@router.get("/road-closures")
async def get_road_closures():
    """Get active road closures from Toronto Open Data."""
    from app.road_closures import fetch_road_closures

    closures = await fetch_road_closures()
    return closures
