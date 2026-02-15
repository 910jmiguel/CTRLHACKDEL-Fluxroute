from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RouteMode(str, Enum):
    TRANSIT = "transit"
    DRIVING = "driving"
    WALKING = "walking"
    CYCLING = "cycling"
    HYBRID = "hybrid"


class Coordinate(BaseModel):
    lat: float
    lng: float


class DirectionStep(BaseModel):
    instruction: str = ""
    distance_km: float = 0.0
    duration_min: float = 0.0
    maneuver_type: str = ""
    maneuver_modifier: str = ""


class RouteSegment(BaseModel):
    mode: RouteMode
    geometry: dict  # GeoJSON LineString
    distance_km: float
    duration_min: float
    instructions: Optional[str] = None
    transit_line: Optional[str] = None
    transit_route_id: Optional[str] = None
    color: Optional[str] = None
    steps: list[DirectionStep] = Field(default_factory=list)
    congestion_level: Optional[str] = None  # "low", "moderate", "heavy", "severe"
    congestion_segments: Optional[list[dict]] = None  # Sub-segments with per-segment congestion


class CostBreakdown(BaseModel):
    fare: float = 0.0
    gas: float = 0.0
    parking: float = 0.0
    total: float = 0.0


class DelayInfo(BaseModel):
    probability: float = 0.0
    expected_minutes: float = 0.0
    confidence: float = 0.0
    factors: list[str] = Field(default_factory=list)


class ParkingInfo(BaseModel):
    station_name: str = ""
    daily_rate: float = 0.0
    capacity: int = 0
    parking_type: str = ""  # "surface", "structure"
    agency: str = ""


class RouteOption(BaseModel):
    id: str
    label: str  # "Direct Drive", "Transit via ...", "Park & Ride (...)", etc.
    mode: RouteMode
    segments: list[RouteSegment]
    total_distance_km: float
    total_duration_min: float
    cost: CostBreakdown
    delay_info: DelayInfo
    stress_score: float = 0.0  # 0.0 (zen) to 1.0 (max stress)
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    summary: str = ""
    traffic_summary: str = ""  # "Heavy traffic", "Moderate traffic", etc.
    parking_info: Optional[ParkingInfo] = None


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    modes: list[RouteMode] = Field(
        default_factory=lambda: [
            RouteMode.TRANSIT,
            RouteMode.DRIVING,
            RouteMode.WALKING,
            RouteMode.HYBRID,
        ]
    )
    departure_time: Optional[str] = None


class RouteResponse(BaseModel):
    routes: list[RouteOption]
    origin: Coordinate
    destination: Coordinate


class DelayPredictionRequest(BaseModel):
    line: str
    station: Optional[str] = None
    hour: int = 12
    day_of_week: int = 0  # 0=Monday
    month: Optional[int] = None


class DelayPredictionResponse(BaseModel):
    delay_probability: float
    expected_delay_minutes: float
    confidence: float
    contributing_factors: list[str]


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    context: Optional[dict] = None  # current route info, location, etc.


class ChatResponse(BaseModel):
    message: str
    suggested_actions: list[str] = Field(default_factory=list)


class ServiceAlert(BaseModel):
    id: str
    route_id: Optional[str] = None
    title: str
    description: str
    severity: str = "info"  # info, warning, error
    active: bool = True


class VehiclePosition(BaseModel):
    vehicle_id: str
    route_id: Optional[str] = None
    latitude: float
    longitude: float
    bearing: Optional[float] = None
    speed: Optional[float] = None
    timestamp: Optional[int] = None


class CustomSegmentRequest(BaseModel):
    mode: RouteMode
    line_id: Optional[str] = None  # e.g. "1", "2", "4", "5"
    start_station_id: Optional[str] = None
    end_station_id: Optional[str] = None
    origin: Optional[Coordinate] = None
    destination: Optional[Coordinate] = None


class CustomRouteRequest(BaseModel):
    segments: list[CustomSegmentRequest]
    trip_origin: Coordinate
    trip_destination: Coordinate


class LineStop(BaseModel):
    stop_id: str
    stop_name: str
    lat: float
    lng: float


class LineStopsResponse(BaseModel):
    line_id: str
    line_name: str
    color: str
    stops: list[LineStop]


# --- V2 Custom Route Builder Models ---


class TransitRouteSuggestion(BaseModel):
    """A suggested transit route (subway line, bus route, streetcar) for the user's trip."""
    suggestion_id: str
    route_id: str
    display_name: str  # e.g. "Line 1 Yonge-University", "96 Wilson"
    transit_mode: str  # "SUBWAY", "BUS", "TRAM"
    color: str  # Hex color for display
    board_stop_name: str
    board_coord: Coordinate
    board_stop_id: Optional[str] = None
    alight_stop_name: str
    alight_coord: Coordinate
    alight_stop_id: Optional[str] = None
    direction_hint: str  # e.g. "Southbound", "Eastbound"
    relevance_reason: str  # Why this route is suggested
    estimated_duration_min: float = 0.0
    estimated_distance_km: float = 0.0
    intermediate_stops: list[dict] = Field(default_factory=list)  # [{stop_id, stop_name, lat, lng}]
    transfer_group_id: Optional[str] = None       # Links paired transfer legs
    transfer_sequence: Optional[int] = None        # 1 = first leg, 2 = second leg
    transfer_station_name: Optional[str] = None    # e.g. "Eglinton" for display


class TransitSuggestionsRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate


class TransitSuggestionsResponse(BaseModel):
    suggestions: list[TransitRouteSuggestion]
    source: str = "gtfs"  # "otp", "gtfs", or "otp+gemini"


class CustomSegmentRequestV2(BaseModel):
    mode: RouteMode
    # For transit segments: use suggestion data
    suggestion_id: Optional[str] = None
    route_id: Optional[str] = None
    board_coord: Optional[Coordinate] = None
    alight_coord: Optional[Coordinate] = None
    board_stop_name: Optional[str] = None
    alight_stop_name: Optional[str] = None
    board_stop_id: Optional[str] = None
    alight_stop_id: Optional[str] = None
    transit_mode: Optional[str] = None  # "SUBWAY", "BUS", "TRAM"
    display_name: Optional[str] = None
    color: Optional[str] = None
    # For driving/walking: auto-routed (no explicit coords needed)


class CustomRouteRequestV2(BaseModel):
    segments: list[CustomSegmentRequestV2]
    trip_origin: Coordinate
    trip_destination: Coordinate


class StopSearchResult(BaseModel):
    stop_id: str
    stop_name: str
    lat: float
    lng: float
    route_id: Optional[str] = None
    line: Optional[str] = None


class StopSearchResponse(BaseModel):
    stops: list[StopSearchResult]


# --- Navigation Models (Phase 1 & 2) ---

class NavigationInstruction(BaseModel):
    """Navigation-grade instruction for a single maneuver."""
    instruction: str = ""
    distance_km: float = 0.0
    duration_min: float = 0.0
    maneuver_type: str = ""
    maneuver_modifier: str = ""
    voice_instruction: Optional[str] = None  # SSML or plain text for TTS
    banner_primary: Optional[str] = None  # Primary banner text (e.g. "Turn right onto Yonge St")
    banner_secondary: Optional[str] = None  # Secondary banner (e.g. "Then continue for 2 km")
    lane_guidance: Optional[list[dict]] = None  # Lane arrow indicators
    geometry: Optional[dict] = None  # Step-level GeoJSON LineString


class NavigationRoute(BaseModel):
    """Route with full navigation instructions (voice, banner, lanes)."""
    route: RouteOption
    navigation_instructions: list[NavigationInstruction] = Field(default_factory=list)
    voice_locale: str = "en-US"
    alternatives: list[RouteOption] = Field(default_factory=list)


class NavigationRouteRequest(BaseModel):
    """Extended route request with navigation options."""
    origin: Coordinate
    destination: Coordinate
    waypoints: list[Coordinate] = Field(default_factory=list)
    profile: str = "driving-traffic"  # driving-traffic, driving, walking, cycling
    alternatives: bool = True
    voice_instructions: bool = True
    banner_instructions: bool = True
    exclude: list[str] = Field(default_factory=list)  # toll, ferry, motorway
    depart_at: Optional[str] = None  # ISO 8601 datetime
    voice_locale: str = "en-US"


class IsochroneRequest(BaseModel):
    """Request for reachability polygons."""
    center: Coordinate
    profile: str = "driving"  # driving, walking, cycling
    contours_minutes: list[int] = Field(default_factory=lambda: [10, 20, 30])
    polygons: bool = True


class IsochroneResponse(BaseModel):
    """GeoJSON FeatureCollection of isochrone polygons."""
    geojson: dict  # GeoJSON FeatureCollection
    center: Coordinate
    profile: str
    contours_minutes: list[int]


class OptimizationRequest(BaseModel):
    """Multi-stop route optimization request."""
    coordinates: list[Coordinate]  # First = start, last = end, middle = waypoints to optimize
    profile: str = "driving"
    roundtrip: bool = False
    source: str = "first"  # first, last, any
    destination: str = "last"  # first, last, any


class OptimizationResponse(BaseModel):
    """Optimized multi-stop route response."""
    waypoint_order: list[int]  # Optimized ordering indices
    routes: list[RouteOption]
    total_distance_km: float
    total_duration_min: float


class NavigationPositionUpdate(BaseModel):
    """Client position update during active navigation."""
    lat: float
    lng: float
    speed: Optional[float] = None  # m/s
    bearing: Optional[float] = None  # degrees from north
    timestamp: Optional[float] = None


class NavigationUpdate(BaseModel):
    """Server-sent navigation state update."""
    type: str = "navigation_update"  # navigation_update, reroute, traffic_update, arrival
    step_index: int = 0
    remaining_distance_km: float = 0.0
    remaining_duration_min: float = 0.0
    eta: Optional[str] = None
    instruction: Optional[str] = None
    voice_instruction: Optional[str] = None
    lane_guidance: Optional[list[dict]] = None
    speed_limit: Optional[float] = None  # km/h
    new_route: Optional[dict] = None  # Only for reroute type
    reason: Optional[str] = None  # Reroute reason
