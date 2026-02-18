import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.models import (
    ChatRequest,
    ChatResponse,
    Coordinate,
    CustomRouteRequest,
    CustomRouteRequestV2,
    DelayPredictionResponse,
    IsochroneRequest,
    IsochroneResponse,
    LineStopsResponse,
    LineStop,
    NavigationPositionUpdate,
    NavigationRoute,
    NavigationRouteRequest,
    NavigationInstruction,
    OptimizationRequest,
    OptimizationResponse,
    RouteMode,
    RouteOption,
    RouteRequest,
    RouteResponse,
    TransitSuggestionsRequest,
    TransitSuggestionsResponse,
    StopSearchResult,
    StopSearchResponse,
    CostBreakdown,
    DelayInfo,
    RouteSegment,
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


@router.get("/stops/search", response_model=StopSearchResponse)
async def search_stops(
    query: str = Query(..., min_length=2),
    limit: int = Query(5, ge=1, le=20),
):
    """Search GTFS stops by name."""
    from app.gtfs_parser import search_stops as gtfs_search_stops

    state = _get_state()
    gtfs = state.get("gtfs", {})

    stops = gtfs_search_stops(gtfs, query, limit)
    return StopSearchResponse(stops=[StopSearchResult(**s) for s in stops])


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


@router.post("/suggest-transit-routes", response_model=TransitSuggestionsResponse)
async def suggest_transit_routes(request: TransitSuggestionsRequest):
    """Get AI-suggested transit routes for a trip origin/destination."""
    from app.route_builder_suggestions import get_transit_suggestions

    state = _get_state()
    gtfs = state.get("gtfs", {})
    http_client = state.get("http_client")
    otp_available = state.get("otp_available", False)

    suggestions, source = await get_transit_suggestions(
        origin=request.origin,
        destination=request.destination,
        gtfs=gtfs,
        http_client=http_client,
        otp_available=otp_available,
    )

    return TransitSuggestionsResponse(suggestions=suggestions, source=source)


@router.post("/custom-route-v2")
async def calculate_custom_route_v2_endpoint(request: CustomRouteRequestV2):
    """Calculate a user-defined custom route using V2 suggestion-based segments."""
    from app.route_engine import calculate_custom_route_v2
    from app.weather import get_current_weather

    state = _get_state()
    gtfs = state.get("gtfs", {})
    predictor = state.get("predictor")
    http_client = state.get("http_client")

    if not predictor:
        raise HTTPException(status_code=503, detail="ML predictor not initialized")

    weather = await get_current_weather(request.trip_origin.lat, request.trip_origin.lng)

    route = await calculate_custom_route_v2(
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


# --- Navigation Endpoints (Phase 1 & 2) ---

@router.post("/navigation-route", response_model=NavigationRoute)
async def get_navigation_route(request: NavigationRouteRequest):
    """Get navigation-grade route with voice/banner instructions and lane guidance."""
    from app.mapbox_navigation import get_navigation_directions
    from app.route_engine import _compute_congestion_summary, _split_geometry_by_congestion

    state = _get_state()
    http_client = state.get("http_client")

    results = await get_navigation_directions(
        origin=request.origin,
        destination=request.destination,
        waypoints=request.waypoints if request.waypoints else None,
        profile=request.profile,
        alternatives=request.alternatives,
        voice_instructions=request.voice_instructions,
        banner_instructions=request.banner_instructions,
        exclude=request.exclude if request.exclude else None,
        depart_at=request.depart_at,
        voice_locale=request.voice_locale,
        http_client=http_client,
    )

    if not results:
        raise HTTPException(status_code=502, detail="Could not fetch navigation route from Mapbox")

    primary = results[0]

    # Build congestion segments for the primary route
    congestion_data = primary.get("congestion")
    congestion_level = primary.get("congestion_level")
    congestion_segments = None
    if congestion_data and primary.get("geometry"):
        coords = primary["geometry"].get("coordinates", [])
        congestion_segments = _split_geometry_by_congestion(coords, congestion_data)

    # Build primary RouteOption
    mode = RouteMode.DRIVING if "driving" in request.profile else RouteMode.WALKING
    if request.profile == "cycling":
        mode = RouteMode.CYCLING

    traffic_summary = ""
    if congestion_data:
        _, traffic_summary = _compute_congestion_summary(congestion_data)

    primary_route = RouteOption(
        id="nav-primary",
        label="Navigation Route",
        mode=mode,
        segments=[RouteSegment(
            mode=mode,
            geometry=primary["geometry"],
            distance_km=primary["distance_km"],
            duration_min=primary["duration_min"],
            instructions=f"Navigate to destination",
            color="#3B82F6",
            congestion_level=congestion_level,
            congestion_segments=congestion_segments,
        )],
        total_distance_km=primary["distance_km"],
        total_duration_min=primary["duration_min"],
        cost=CostBreakdown(),
        delay_info=DelayInfo(),
        stress_score=0.0,
        summary=f"{primary['distance_km']:.1f} km, {primary['duration_min']:.0f} min",
        traffic_summary=traffic_summary,
    )

    # Build navigation instructions
    nav_instructions = [
        NavigationInstruction(**instr)
        for instr in primary.get("navigation_instructions", [])
    ]

    # Build alternative RouteOptions
    alternatives = []
    for i, alt in enumerate(results[1:], start=1):
        alt_route = RouteOption(
            id=f"nav-alt-{i}",
            label=f"Alternative {i}",
            mode=mode,
            segments=[RouteSegment(
                mode=mode,
                geometry=alt["geometry"],
                distance_km=alt["distance_km"],
                duration_min=alt["duration_min"],
                instructions=f"Alternative route {i}",
                color="#6B7280",
            )],
            total_distance_km=alt["distance_km"],
            total_duration_min=alt["duration_min"],
            cost=CostBreakdown(),
            delay_info=DelayInfo(),
            stress_score=0.0,
            summary=f"Alt {i}: {alt['distance_km']:.1f} km, {alt['duration_min']:.0f} min",
        )
        alternatives.append(alt_route)

    return NavigationRoute(
        route=primary_route,
        navigation_instructions=nav_instructions,
        voice_locale=request.voice_locale,
        alternatives=alternatives,
    )


@router.post("/optimize-route", response_model=OptimizationResponse)
async def optimize_route(request: OptimizationRequest):
    """Optimize multi-stop route ordering."""
    from app.mapbox_navigation import get_optimized_route

    state = _get_state()
    http_client = state.get("http_client")

    result = await get_optimized_route(
        coordinates=request.coordinates,
        profile=request.profile,
        roundtrip=request.roundtrip,
        source=request.source,
        destination=request.destination,
        http_client=http_client,
    )

    if not result:
        raise HTTPException(status_code=502, detail="Could not optimize route")

    mode = RouteMode.DRIVING if "driving" in request.profile else RouteMode.WALKING

    optimized_route = RouteOption(
        id="optimized",
        label="Optimized Route",
        mode=mode,
        segments=[RouteSegment(
            mode=mode,
            geometry=result["geometry"],
            distance_km=result["distance_km"],
            duration_min=result["duration_min"],
            instructions="Optimized multi-stop route",
            color="#8B5CF6",
        )],
        total_distance_km=result["distance_km"],
        total_duration_min=result["duration_min"],
        cost=CostBreakdown(),
        delay_info=DelayInfo(),
        summary=f"Optimized: {result['distance_km']:.1f} km, {result['duration_min']:.0f} min",
    )

    return OptimizationResponse(
        waypoint_order=result["waypoint_order"],
        routes=[optimized_route],
        total_distance_km=result["distance_km"],
        total_duration_min=result["duration_min"],
    )


@router.post("/isochrone", response_model=IsochroneResponse)
async def get_isochrone(request: IsochroneRequest):
    """Get reachability isochrone polygons."""
    from app.mapbox_navigation import get_isochrone as fetch_isochrone

    state = _get_state()
    http_client = state.get("http_client")

    geojson = await fetch_isochrone(
        center=request.center,
        profile=request.profile,
        contours_minutes=request.contours_minutes,
        polygons=request.polygons,
        http_client=http_client,
    )

    if not geojson:
        raise HTTPException(status_code=502, detail="Could not fetch isochrone data")

    return IsochroneResponse(
        geojson=geojson,
        center=request.center,
        profile=request.profile,
        contours_minutes=request.contours_minutes,
    )


@router.websocket("/ws/navigation/{session_id}")
async def navigation_websocket(websocket: WebSocket, session_id: str):
    """Real-time navigation WebSocket.

    Client sends: {"type": "position_update", "lat": ..., "lng": ..., "speed": ..., "bearing": ...}
    Server sends: NavigationUpdate messages
    """
    state = _get_state()
    nav_manager = state.get("nav_manager")

    if not nav_manager:
        await websocket.close(code=1011, reason="Navigation service unavailable")
        return

    session = nav_manager.get_session(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for navigation session: {session_id}")

    try:
        while session.is_active:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "position_update":
                update = nav_manager.process_position_update(
                    session_id=session_id,
                    lat=msg["lat"],
                    lng=msg["lng"],
                    speed=msg.get("speed"),
                    bearing=msg.get("bearing"),
                )

                # If reroute needed, fetch new route first then send combined message
                if update.type == "reroute":
                    from app.mapbox_navigation import get_navigation_directions

                    http_client = state.get("http_client")
                    new_routes = await get_navigation_directions(
                        origin=Coordinate(lat=msg["lat"], lng=msg["lng"]),
                        destination=session.destination,
                        profile=session.profile,
                        alternatives=False,
                        http_client=http_client,
                    )

                    if new_routes:
                        new_route = new_routes[0]
                        # Update session with new route
                        session.route_geometry = new_route["geometry"]
                        session.steps = new_route.get("steps", [])
                        session.navigation_instructions = new_route.get("navigation_instructions", [])
                        session.total_distance_km = new_route["distance_km"]
                        session.total_duration_min = new_route["duration_min"]
                        session.remaining_distance_km = new_route["distance_km"]
                        session.remaining_duration_min = new_route["duration_min"]
                        session.current_step_index = 0

                        reroute_msg = {
                            "type": "reroute",
                            "reason": "Off route detected",
                            "new_route": {
                                "geometry": new_route["geometry"],
                                "distance_km": new_route["distance_km"],
                                "duration_min": new_route["duration_min"],
                                "steps": new_route.get("steps", []),
                                "navigation_instructions": new_route.get("navigation_instructions", []),
                            },
                        }
                        await websocket.send_text(json.dumps(reroute_msg))
                    else:
                        # Mapbox reroute failed — send basic reroute notification
                        await websocket.send_text(update.model_dump_json())
                    continue

                # Send normal navigation update
                await websocket.send_text(update.model_dump_json())

                # If arrived, close connection
                if update.type == "arrival":
                    await websocket.send_text(json.dumps({"type": "arrival", "destination_reached": True}))
                    break

            elif msg.get("type") == "end_navigation":
                nav_manager.end_session(session_id)
                await websocket.send_text(json.dumps({"type": "session_ended"}))
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        logger.info(f"Navigation WebSocket closed: {session_id}")


@router.post("/navigation-session")
async def create_navigation_session(request: NavigationRouteRequest):
    """Create a navigation session and return session_id for WebSocket connection."""
    from app.mapbox_navigation import get_navigation_directions

    state = _get_state()
    nav_manager = state.get("nav_manager")
    http_client = state.get("http_client")

    if not nav_manager:
        raise HTTPException(status_code=503, detail="Navigation service unavailable")

    results = await get_navigation_directions(
        origin=request.origin,
        destination=request.destination,
        waypoints=request.waypoints if request.waypoints else None,
        profile=request.profile,
        alternatives=False,
        voice_instructions=request.voice_instructions,
        banner_instructions=request.banner_instructions,
        exclude=request.exclude if request.exclude else None,
        http_client=http_client,
    )

    if not results:
        raise HTTPException(status_code=502, detail="Could not fetch route for navigation")

    session_id = nav_manager.create_session(
        origin=request.origin,
        destination=request.destination,
        route_data=results[0],
        profile=request.profile,
    )

    return {
        "session_id": session_id,
        "websocket_url": f"/api/ws/navigation/{session_id}",
        "route": results[0],
    }
