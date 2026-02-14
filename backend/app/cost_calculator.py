from app.models import RouteMode, CostBreakdown


# TTC fare constants
TTC_FARE = 3.35
GO_TRANSIT_BASE = 3.70
GO_TRANSIT_PER_KM = 0.08

# Driving costs
GAS_PRICE_PER_LITRE = 1.55
FUEL_CONSUMPTION_L_PER_100KM = 9.0

# Parking costs
PARKING_DOWNTOWN = 15.0
PARKING_SUBURBAN = 5.0
PARKING_STATION = 0.0

# Downtown Toronto bounding box (approximate)
DOWNTOWN_BOUNDS = {
    "min_lat": 43.635,
    "max_lat": 43.675,
    "min_lng": -79.410,
    "max_lng": -79.365,
}


def is_downtown(lat: float, lng: float) -> bool:
    """Check if coordinates are in downtown Toronto."""
    return (
        DOWNTOWN_BOUNDS["min_lat"] <= lat <= DOWNTOWN_BOUNDS["max_lat"]
        and DOWNTOWN_BOUNDS["min_lng"] <= lng <= DOWNTOWN_BOUNDS["max_lng"]
    )


def calculate_cost(
    mode: RouteMode,
    distance_km: float,
    dest_lat: float = 43.65,
    dest_lng: float = -79.38,
    num_transfers: int = 0,
    includes_go: bool = False,
) -> CostBreakdown:
    """Calculate trip cost based on mode and distance."""

    if mode == RouteMode.TRANSIT:
        fare = TTC_FARE
        if includes_go:
            fare += GO_TRANSIT_BASE + (distance_km * GO_TRANSIT_PER_KM)
        return CostBreakdown(fare=round(fare, 2), total=round(fare, 2))

    elif mode == RouteMode.DRIVING:
        gas = (distance_km / 100) * FUEL_CONSUMPTION_L_PER_100KM * GAS_PRICE_PER_LITRE
        parking = PARKING_DOWNTOWN if is_downtown(dest_lat, dest_lng) else PARKING_SUBURBAN
        total = gas + parking
        return CostBreakdown(
            gas=round(gas, 2),
            parking=round(parking, 2),
            total=round(total, 2),
        )

    elif mode == RouteMode.WALKING or mode == RouteMode.CYCLING:
        return CostBreakdown(total=0.0)

    elif mode == RouteMode.HYBRID:
        # Assume driving to nearest station (half distance) then transit
        drive_dist = distance_km * 0.4
        gas = (drive_dist / 100) * FUEL_CONSUMPTION_L_PER_100KM * GAS_PRICE_PER_LITRE
        parking = PARKING_STATION
        fare = TTC_FARE
        total = gas + parking + fare
        return CostBreakdown(
            fare=round(fare, 2),
            gas=round(gas, 2),
            parking=round(parking, 2),
            total=round(total, 2),
        )

    return CostBreakdown(total=0.0)
