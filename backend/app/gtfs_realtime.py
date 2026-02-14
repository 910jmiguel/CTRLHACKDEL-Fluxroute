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

# TTC GTFS-RT endpoints (protobuf)
TTC_VEHICLE_URL = "https://opendata.toronto.ca/toronto-transit-commission/ttc-routes-and-schedules/opendata_ttc_vehicle_positions"
TTC_ALERTS_URL = "https://opendata.toronto.ca/toronto-transit-commission/ttc-routes-and-schedules/opendata_ttc_alerts"

# TTC JSON-based API (more reliable fallback)
TTC_LIVE_VEHICLES_URL = "https://alerts.ttc.ca/api/alerts/live-map/getVehicles"
TTC_LIVE_ALERTS_URL = "https://alerts.ttc.ca/api/alerts/list"

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
    "5": {  # Eglinton Crosstown LRT
        "name": "Line 5 Eglinton",
        "color": "#FF6600",
        "coords": [
            (43.6898, -79.5520), (43.6909, -79.5299), (43.6921, -79.5105),
            (43.6930, -79.4882), (43.6942, -79.4650), (43.6956, -79.4432),
            (43.6972, -79.4210), (43.6986, -79.3989), (43.7000, -79.3780),
            (43.7017, -79.3593), (43.7032, -79.3442), (43.7048, -79.3292),
            (43.7065, -79.3150), (43.7078, -79.2990), (43.7090, -79.2815),
            (43.7100, -79.2636),
        ],
    },
    "6": {  # Finch West LRT
        "name": "Line 6 Finch West",
        "color": "#8B4513",
        "coords": [
            (43.7630, -79.5950), (43.7635, -79.5750), (43.7640, -79.5550),
            (43.7645, -79.5350), (43.7650, -79.5150), (43.7655, -79.4950),
            (43.7660, -79.4770), (43.7665, -79.4590), (43.7670, -79.4410),
            (43.7675, -79.4230), (43.7680, -79.4111),
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


async def _try_fetch_vehicles_protobuf(client: httpx.AsyncClient) -> list[VehiclePosition]:
    """Try TTC GTFS-RT protobuf vehicle feed."""
    resp = await client.get(TTC_VEHICLE_URL)
    if resp.status_code != 200:
        return []

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
    return vehicles


async def _try_fetch_vehicles_json(client: httpx.AsyncClient) -> list[VehiclePosition]:
    """Try TTC JSON vehicle API (fallback)."""
    resp = await client.get(TTC_LIVE_VEHICLES_URL)
    if resp.status_code != 200:
        return []

    data = resp.json()
    vehicles = []
    ts = int(time.time())

    # The TTC live-map API returns vehicles grouped by route
    if isinstance(data, dict):
        for route_id, route_vehicles in data.items():
            if not isinstance(route_vehicles, list):
                continue
            for v in route_vehicles:
                try:
                    vehicles.append(VehiclePosition(
                        vehicle_id=str(v.get("id", f"ttc_{route_id}_{len(vehicles)}")),
                        route_id=str(route_id),
                        latitude=float(v.get("lat", 0)),
                        longitude=float(v.get("lon", v.get("lng", 0))),
                        bearing=float(v["heading"]) if v.get("heading") else None,
                        speed=float(v["speed"]) if v.get("speed") else None,
                        timestamp=ts,
                    ))
                except (ValueError, KeyError):
                    continue
    elif isinstance(data, list):
        for v in data:
            try:
                vehicles.append(VehiclePosition(
                    vehicle_id=str(v.get("id", f"ttc_{len(vehicles)}")),
                    route_id=str(v.get("routeId", v.get("route_id", ""))),
                    latitude=float(v.get("lat", v.get("latitude", 0))),
                    longitude=float(v.get("lon", v.get("lng", v.get("longitude", 0)))),
                    bearing=float(v["heading"]) if v.get("heading") else None,
                    speed=float(v["speed"]) if v.get("speed") else None,
                    timestamp=ts,
                ))
            except (ValueError, KeyError):
                continue

    return vehicles


async def _try_fetch_alerts_protobuf(client: httpx.AsyncClient) -> list[ServiceAlert]:
    """Try TTC GTFS-RT protobuf alerts feed."""
    resp = await client.get(TTC_ALERTS_URL)
    if resp.status_code != 200:
        return []

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
    return alerts


async def _try_fetch_alerts_json(client: httpx.AsyncClient) -> list[ServiceAlert]:
    """Try TTC JSON alerts API (fallback)."""
    resp = await client.get(TTC_LIVE_ALERTS_URL)
    if resp.status_code != 200:
        return []

    data = resp.json()
    alerts = []

    # TTC alerts API uses "routes" key, other formats may use "alerts" or "data"
    alert_list = data if isinstance(data, list) else data.get("routes", data.get("alerts", data.get("data", [])))
    for item in alert_list:
        try:
            # Map TTC severity values
            severity = "info"
            sev_str = str(item.get("severity", item.get("priority", ""))).lower()
            if "critical" in sev_str or sev_str == "error":
                severity = "error"
            elif "major" in sev_str or "warning" in sev_str or str(item.get("priority", "")) == "1":
                severity = "warning"

            # Use headerText (TTC format) or title
            title = item.get("headerText", item.get("customHeaderText", item.get("title", "Service Alert")))
            description = item.get("description", "") or title

            route_id = item.get("route")
            if route_id and str(route_id) == "9999":
                route_id = None  # TTC uses 9999 for system-wide alerts

            alerts.append(ServiceAlert(
                id=str(item.get("id", f"alert_{len(alerts)}")),
                route_id=str(route_id) if route_id else None,
                title=title[:200] if title else "Service Alert",
                description=description[:500] if description else "No details",
                severity=severity,
            ))
        except (ValueError, KeyError):
            continue

    return alerts


async def _try_fetch_realtime(app_state: dict) -> None:
    """Try to fetch real GTFS-RT data, fall back to mock."""
    vehicles_fetched = False
    alerts_fetched = False

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Try vehicle positions: protobuf first, then JSON
            try:
                vehicles = await _try_fetch_vehicles_protobuf(client)
                if vehicles:
                    app_state["vehicles"] = vehicles
                    vehicles_fetched = True
                    logger.info(f"Fetched {len(vehicles)} real vehicle positions (protobuf)")
            except Exception as e:
                logger.debug(f"TTC protobuf vehicle feed unavailable: {e}")

            if not vehicles_fetched:
                try:
                    vehicles = await _try_fetch_vehicles_json(client)
                    if vehicles:
                        app_state["vehicles"] = vehicles
                        vehicles_fetched = True
                        logger.info(f"Fetched {len(vehicles)} real vehicle positions (JSON)")
                except Exception as e:
                    logger.debug(f"TTC JSON vehicle feed unavailable: {e}")

            # Try alerts: protobuf first, then JSON
            try:
                alerts = await _try_fetch_alerts_protobuf(client)
                if alerts:
                    app_state["alerts"] = alerts
                    alerts_fetched = True
                    logger.info(f"Fetched {len(alerts)} real alerts (protobuf)")
            except Exception as e:
                logger.debug(f"TTC protobuf alerts feed unavailable: {e}")

            if not alerts_fetched:
                try:
                    alerts = await _try_fetch_alerts_json(client)
                    if alerts:
                        app_state["alerts"] = alerts
                        alerts_fetched = True
                        logger.info(f"Fetched {len(alerts)} real alerts (JSON)")
                except Exception as e:
                    logger.debug(f"TTC JSON alerts feed unavailable: {e}")

    except Exception as e:
        logger.debug(f"Real-time fetch failed: {e}")

    # Fallback to mock data for anything we couldn't fetch
    if not vehicles_fetched:
        app_state["vehicles"] = _generate_mock_vehicles()
        logger.debug("Using mock vehicle data")
    if not alerts_fetched:
        app_state["alerts"] = _get_mock_alerts()
        logger.debug("Using mock alert data")


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
