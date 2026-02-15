"""Navigation session manager for real-time turn-by-turn navigation.

Handles active navigation sessions, position tracking, off-route detection,
and server-side rerouting.
"""

import asyncio
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.models import Coordinate, NavigationUpdate

logger = logging.getLogger("fluxroute.nav_service")

# Off-route threshold: >50m from route for 3+ consecutive updates
OFF_ROUTE_DISTANCE_M = 50.0
OFF_ROUTE_COUNT_THRESHOLD = 3

# Position update staleness threshold
STALE_POSITION_SEC = 30.0


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in meters."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_to_segment_distance(
    px: float, py: float,
    ax: float, ay: float,
    bx: float, by: float,
) -> float:
    """Approximate distance from point (px, py) to line segment (a, b) in meters.

    Uses flat-earth approximation (acceptable for short distances).
    """
    # Convert lat/lng to approximate meters (flat-earth projection)
    cos_lat = math.cos(math.radians(px))
    pxm = px * 110540
    pym = py * 111320 * cos_lat
    axm = ax * 110540
    aym = ay * 111320 * cos_lat
    bxm = bx * 110540
    bym = by * 111320 * cos_lat

    dx, dy = bxm - axm, bym - aym
    len_sq = dx * dx + dy * dy

    if len_sq == 0:
        return math.sqrt((pxm - axm) ** 2 + (pym - aym) ** 2)

    t = max(0, min(1, ((pxm - axm) * dx + (pym - aym) * dy) / len_sq))
    proj_x = axm + t * dx
    proj_y = aym + t * dy

    return math.sqrt((pxm - proj_x) ** 2 + (pym - proj_y) ** 2)


@dataclass
class NavigationSession:
    """Tracks state for one active navigation session."""
    session_id: str
    origin: Coordinate
    destination: Coordinate
    route_geometry: dict  # GeoJSON LineString
    steps: list[dict]  # Navigation steps
    navigation_instructions: list[dict]  # Full nav instructions
    total_distance_km: float
    total_duration_min: float

    # Current state
    current_step_index: int = 0
    remaining_distance_km: float = 0.0
    remaining_duration_min: float = 0.0
    last_position: Optional[Coordinate] = None
    last_position_time: float = 0.0
    off_route_count: int = 0
    reroute_count: int = 0
    started_at: float = field(default_factory=time.time)
    is_active: bool = True

    def __post_init__(self):
        self.remaining_distance_km = self.total_distance_km
        self.remaining_duration_min = self.total_duration_min


class NavigationSessionManager:
    """Manages all active navigation sessions."""

    def __init__(self):
        self.sessions: dict[str, NavigationSession] = {}

    def create_session(
        self,
        origin: Coordinate,
        destination: Coordinate,
        route_data: dict,
    ) -> str:
        """Create a new navigation session from route data.

        Returns session_id.
        """
        session_id = str(uuid.uuid4())[:12]

        session = NavigationSession(
            session_id=session_id,
            origin=origin,
            destination=destination,
            route_geometry=route_data.get("geometry", {}),
            steps=route_data.get("steps", []),
            navigation_instructions=route_data.get("navigation_instructions", []),
            total_distance_km=route_data.get("distance_km", 0),
            total_duration_min=route_data.get("duration_min", 0),
        )

        self.sessions[session_id] = session
        logger.info(f"Navigation session created: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[NavigationSession]:
        return self.sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        if session:
            session.is_active = False
            logger.info(f"Navigation session ended: {session_id}")
            return True
        return False

    def process_position_update(
        self,
        session_id: str,
        lat: float,
        lng: float,
        speed: Optional[float] = None,
        bearing: Optional[float] = None,
    ) -> NavigationUpdate:
        """Process a position update and return navigation state.

        Handles:
        - Current step detection
        - Remaining distance/time calculation
        - Off-route detection
        - Arrival detection
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return NavigationUpdate(
                type="error",
                instruction="Session not found or inactive",
            )

        session.last_position = Coordinate(lat=lat, lng=lng)
        session.last_position_time = time.time()

        coords = session.route_geometry.get("coordinates", [])
        if not coords:
            return NavigationUpdate(type="error", instruction="No route geometry")

        # Check arrival (within 50m of destination)
        dest_dist = _haversine_m(lat, lng, session.destination.lat, session.destination.lng)
        if dest_dist < 50:
            session.is_active = False
            return NavigationUpdate(
                type="arrival",
                step_index=len(session.steps) - 1,
                remaining_distance_km=0,
                remaining_duration_min=0,
                instruction="You have arrived at your destination",
                voice_instruction="You have arrived at your destination.",
            )

        # Find closest point on route and distance to route
        min_dist = float("inf")
        closest_segment_idx = 0

        for i in range(len(coords) - 1):
            # coords are [lng, lat]
            dist = _point_to_segment_distance(
                lat, lng,
                coords[i][1], coords[i][0],
                coords[i + 1][1], coords[i + 1][0],
            )
            if dist < min_dist:
                min_dist = dist
                closest_segment_idx = i

        # Off-route detection
        if min_dist > OFF_ROUTE_DISTANCE_M:
            session.off_route_count += 1
        else:
            session.off_route_count = 0

        if session.off_route_count >= OFF_ROUTE_COUNT_THRESHOLD:
            session.off_route_count = 0
            session.reroute_count += 1
            return NavigationUpdate(
                type="reroute",
                step_index=session.current_step_index,
                remaining_distance_km=session.remaining_distance_km,
                remaining_duration_min=session.remaining_duration_min,
                reason=f"Off route detected ({min_dist:.0f}m from route)",
                instruction="Recalculating route...",
                voice_instruction="Recalculating.",
            )

        # Calculate remaining distance from closest point to end
        remaining_dist_m = 0.0
        for i in range(closest_segment_idx + 1, len(coords) - 1):
            remaining_dist_m += _haversine_m(
                coords[i][1], coords[i][0],
                coords[i + 1][1], coords[i + 1][0],
            )
        # Add partial current segment
        remaining_dist_m += _haversine_m(
            lat, lng,
            coords[closest_segment_idx + 1][1], coords[closest_segment_idx + 1][0],
        )

        session.remaining_distance_km = round(remaining_dist_m / 1000, 2)

        # Estimate remaining time based on speed or average
        if speed and speed > 0:
            session.remaining_duration_min = round(remaining_dist_m / speed / 60, 1)
        else:
            # Use proportion of total
            progress = 1 - (remaining_dist_m / 1000 / max(session.total_distance_km, 0.01))
            session.remaining_duration_min = round(
                session.total_duration_min * (1 - max(0, min(1, progress))), 1
            )

        # Determine current step
        step_dist_accumulator = 0.0
        current_step = 0
        for i, step in enumerate(session.steps):
            step_dist_accumulator += step.get("distance_km", 0) * 1000
            if step_dist_accumulator > (session.total_distance_km * 1000 - remaining_dist_m):
                current_step = i
                break
        else:
            current_step = max(0, len(session.steps) - 1)

        session.current_step_index = current_step

        # Get current instruction
        instruction = ""
        voice_instruction = None
        lane_guidance = None
        speed_limit = None

        if current_step < len(session.navigation_instructions):
            nav_instr = session.navigation_instructions[current_step]
            instruction = nav_instr.get("banner_primary") or nav_instr.get("instruction", "")
            voice_instruction = nav_instr.get("voice_instruction")
            lane_guidance = nav_instr.get("lane_guidance")
        elif current_step < len(session.steps):
            instruction = session.steps[current_step].get("instruction", "")

        # Calculate ETA
        now = datetime.now()
        eta_minutes = session.remaining_duration_min
        eta_hour = now.hour + int(eta_minutes // 60)
        eta_min = now.minute + int(eta_minutes % 60)
        if eta_min >= 60:
            eta_hour += 1
            eta_min -= 60
        eta_str = f"{eta_hour % 24:02d}:{eta_min:02d}"

        return NavigationUpdate(
            type="navigation_update",
            step_index=current_step,
            remaining_distance_km=session.remaining_distance_km,
            remaining_duration_min=session.remaining_duration_min,
            eta=eta_str,
            instruction=instruction,
            voice_instruction=voice_instruction,
            lane_guidance=lane_guidance,
            speed_limit=speed_limit,
        )

    def get_active_sessions_count(self) -> int:
        return sum(1 for s in self.sessions.values() if s.is_active)

    def cleanup_stale_sessions(self, max_age_sec: float = 3600) -> int:
        """Remove sessions older than max_age_sec. Returns count removed."""
        now = time.time()
        stale = [
            sid for sid, s in self.sessions.items()
            if now - s.started_at > max_age_sec or (
                not s.is_active and now - s.started_at > 300
            )
        ]
        for sid in stale:
            del self.sessions[sid]
        if stale:
            logger.info(f"Cleaned up {len(stale)} stale navigation sessions")
        return len(stale)
