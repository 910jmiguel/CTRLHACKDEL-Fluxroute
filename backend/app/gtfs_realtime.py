import asyncio
import logging
import os
import random
import time
from typing import Optional

import httpx

from app.models import ServiceAlert, VehiclePosition

logger = logging.getLogger("fluxroute.realtime")

POLL_INTERVAL = 30  # seconds
METROLINX_API_KEY = os.getenv("METROLINX_API_KEY", "")

# TTC GTFS-RT endpoints
TTC_VEHICLE_URL = "https://opendata.toronto.ca/toronto-transit-commission/ttc-routes-and-schedules/opendata_ttc_vehicle_positions"
TTC_ALERTS_URL = "https://opendata.toronto.ca/toronto-transit-commission/ttc-routes-and-schedules/opendata_ttc_alerts"

# TTC subway line coordinates for mock vehicles
SUBWAY_LINES = {
    "1": {  # Yonge-University
        "name": "Line 1 Yonge-University",
        "color": "#FFCC00",
        "coords": [
            (43.7804, -79.4153), (43.7615, -79.4111), (43.7440, -79.4066),
            (43.7251, -79.4024), (43.7057, -79.3983), (43.6880, -79.3934),
            (43.6709, -79.3857), (43.6561, -79.3803), (43.6453, -79.3806),
            (43.6507, -79.3872), (43.6600, -79.3909), (43.6683, -79.3997),
            (43.6748, -79.4069), (43.6841, -79.4150), (43.7158, -79.4440),
            (43.7339, -79.4502), (43.7494, -79.4618), (43.7943, -79.5273),
        ],
    },
    "2": {  # Bloor-Danforth
        "name": "Line 2 Bloor-Danforth",
        "color": "#00A651",
        "coords": [
            (43.6372, -79.5361), (43.6386, -79.5246), (43.6502, -79.4952),
            (43.6540, -79.4668), (43.6567, -79.4526), (43.6601, -79.4356),
            (43.6660, -79.4110), (43.6672, -79.4037), (43.6709, -79.3857),
            (43.6722, -79.3764), (43.6770, -79.3584), (43.6799, -79.3451),
            (43.6831, -79.3302), (43.6890, -79.3012), (43.6917, -79.2794),
            (43.7326, -79.2637),
        ],
    },
    "4": {  # Sheppard
        "name": "Line 4 Sheppard",
        "color": "#A8518A",
        "coords": [
            (43.7615, -79.4111), (43.7670, -79.3868), (43.7693, -79.3763),
            (43.7710, -79.3659), (43.7757, -79.3461),
        ],
    },
}

MOCK_ALERTS = [
    ServiceAlert(
        id="alert_1",
        route_id="1",
        title="Line 1: Minor Delays",
        description="Expect 5-10 minute delays on Line 1 due to signal issues at Bloor-Yonge.",
        severity="warning",
    ),
    ServiceAlert(
        id="alert_2",
        route_id="2",
        title="Line 2: Normal Service",
        description="Line 2 Bloor-Danforth is operating normally.",
        severity="info",
    ),
    ServiceAlert(
        id="alert_3",
        route_id=None,
        title="TTC Weekend Service",
        description="Weekend service schedules are in effect. Plan extra time for your trip.",
        severity="info",
    ),
    ServiceAlert(
        id="alert_4",
        route_id="1",
        title="Accessibility Notice",
        description="Elevators at Dundas station are temporarily out of service.",
        severity="warning",
    ),
]


def _generate_mock_vehicles() -> list[VehiclePosition]:
    """Generate realistic vehicle positions along subway lines."""
    vehicles = []
    ts = int(time.time())

    for line_id, line_data in SUBWAY_LINES.items():
        coords = line_data["coords"]
        # Place 4-8 vehicles per line
        num_vehicles = random.randint(4, 8)

        for i in range(num_vehicles):
            # Interpolate position between two stations
            idx = random.randint(0, len(coords) - 2)
            t = random.random()
            lat = coords[idx][0] + t * (coords[idx + 1][0] - coords[idx][0])
            lng = coords[idx][1] + t * (coords[idx + 1][1] - coords[idx][1])

            # Add small random jitter
            lat += random.uniform(-0.001, 0.001)
            lng += random.uniform(-0.001, 0.001)

            # Calculate bearing
            dlng = coords[idx + 1][1] - coords[idx][1]
            dlat = coords[idx + 1][0] - coords[idx][0]
            import math
            bearing = math.degrees(math.atan2(dlng, dlat)) % 360

            vehicles.append(VehiclePosition(
                vehicle_id=f"TTC_{line_id}_{i:03d}",
                route_id=line_id,
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                bearing=round(bearing, 1),
                speed=round(random.uniform(20, 60), 1),
                timestamp=ts,
            ))

    return vehicles


def _get_mock_alerts() -> list[ServiceAlert]:
    """Return a subset of mock alerts."""
    return random.sample(MOCK_ALERTS, k=min(3, len(MOCK_ALERTS)))


async def _try_fetch_realtime(app_state: dict) -> None:
    """Try to fetch real GTFS-RT data, fall back to mock."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try TTC vehicle positions
            try:
                resp = await client.get(TTC_VEHICLE_URL)
                if resp.status_code == 200:
                    from google.transit import gtfs_realtime_pb2
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(resp.content)

                    vehicles = []
                    for entity in feed.entity:
                        if entity.HasField("vehicle"):
                            vp = entity.vehicle
                            vehicles.append(VehiclePosition(
                                vehicle_id=str(vp.vehicle.id) if vp.vehicle.id else entity.id,
                                route_id=str(vp.trip.route_id) if vp.trip.route_id else None,
                                latitude=vp.position.latitude,
                                longitude=vp.position.longitude,
                                bearing=vp.position.bearing if vp.position.bearing else None,
                                speed=vp.position.speed if vp.position.speed else None,
                                timestamp=vp.timestamp if vp.timestamp else None,
                            ))

                    if vehicles:
                        app_state["vehicles"] = vehicles
                        logger.info(f"Fetched {len(vehicles)} real vehicle positions")
                        return
            except Exception as e:
                logger.debug(f"TTC vehicle feed unavailable: {e}")

            # Try TTC alerts
            try:
                resp = await client.get(TTC_ALERTS_URL)
                if resp.status_code == 200:
                    from google.transit import gtfs_realtime_pb2
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(resp.content)

                    alerts = []
                    for entity in feed.entity:
                        if entity.HasField("alert"):
                            alert = entity.alert
                            title = ""
                            desc = ""
                            if alert.header_text and alert.header_text.translation:
                                title = alert.header_text.translation[0].text
                            if alert.description_text and alert.description_text.translation:
                                desc = alert.description_text.translation[0].text

                            route_id = None
                            if alert.informed_entity:
                                route_id = alert.informed_entity[0].route_id or None

                            alerts.append(ServiceAlert(
                                id=entity.id,
                                route_id=route_id,
                                title=title or "Service Alert",
                                description=desc or "No details available",
                                severity="warning",
                            ))

                    if alerts:
                        app_state["alerts"] = alerts
                        logger.info(f"Fetched {len(alerts)} real alerts")
            except Exception as e:
                logger.debug(f"TTC alerts feed unavailable: {e}")

    except Exception as e:
        logger.debug(f"Real-time fetch failed: {e}")

    # Fallback to mock data
    app_state["vehicles"] = _generate_mock_vehicles()
    app_state["alerts"] = _get_mock_alerts()
    logger.debug("Using mock real-time data")


async def _poller_loop(app_state: dict):
    """Background polling loop."""
    while True:
        try:
            await _try_fetch_realtime(app_state)
        except Exception as e:
            logger.error(f"Poller error: {e}")
            app_state["vehicles"] = _generate_mock_vehicles()
            app_state["alerts"] = _get_mock_alerts()
        await asyncio.sleep(POLL_INTERVAL)


async def start_realtime_poller(app_state: dict) -> Optional[asyncio.Task]:
    """Start the background real-time data poller."""
    # Initialize with mock data immediately
    app_state["vehicles"] = _generate_mock_vehicles()
    app_state["alerts"] = _get_mock_alerts()

    task = asyncio.create_task(_poller_loop(app_state))
    logger.info("Real-time poller started")
    return task


async def stop_realtime_poller(app_state: dict):
    """Stop the background poller."""
    task = app_state.get("poller_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("Real-time poller stopped")
