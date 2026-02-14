import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition } from "./types";
import { MODE_COLORS } from "./constants";

const ROUTE_SOURCE_PREFIX = "route-";
const ROUTE_LAYER_PREFIX = "route-layer-";
const VEHICLES_SOURCE = "vehicles-source";

// Congestion-based colors for driving segments
const CONGESTION_COLORS: Record<string, string> = {
  low: "#10B981",      // Green
  moderate: "#F59E0B", // Yellow
  heavy: "#F97316",    // Orange
  severe: "#EF4444",   // Red
};

export function clearRoutes(map: mapboxgl.Map) {
  // Remove all route layers and sources
  const style = map.getStyle();
  if (!style || !style.layers) return;

  for (const layer of style.layers) {
    if (layer.id.startsWith(ROUTE_LAYER_PREFIX)) {
      map.removeLayer(layer.id);
    }
  }

  for (const sourceId of Object.keys(style.sources || {})) {
    if (sourceId.startsWith(ROUTE_SOURCE_PREFIX)) {
      map.removeSource(sourceId);
    }
  }
}

export function drawMultimodalRoute(
  map: mapboxgl.Map,
  route: RouteOption,
  isSelected: boolean = true
) {
  route.segments.forEach((segment, idx) => {
    const sourceId = `${ROUTE_SOURCE_PREFIX}${route.id}-${idx}`;
    const layerId = `${ROUTE_LAYER_PREFIX}${route.id}-${idx}`;

    // Remove existing
    if (map.getLayer(layerId)) map.removeLayer(layerId);
    if (map.getSource(sourceId)) map.removeSource(sourceId);

    // Use congestion-based color for driving/hybrid driving segments
    const color =
      segment.mode === "driving" && segment.congestion_level
        ? CONGESTION_COLORS[segment.congestion_level] || segment.color || MODE_COLORS[segment.mode] || "#3B82F6"
        : segment.color || MODE_COLORS[segment.mode] || "#FFFFFF";

    map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "Feature",
        properties: {},
        geometry: segment.geometry,
      },
    });

    map.addLayer({
      id: layerId,
      type: "line",
      source: sourceId,
      layout: {
        "line-join": "round",
        "line-cap": "round",
      },
      paint: {
        "line-color": color,
        "line-width": isSelected ? 5 : 3,
        "line-opacity": isSelected ? 0.9 : 0.4,
        ...(segment.mode === "walking"
          ? { "line-dasharray": [2, 2] }
          : {}),
      },
    });
  });
}

export function addMarkers(
  map: mapboxgl.Map,
  origin: { lat: number; lng: number },
  destination: { lat: number; lng: number },
  existingMarkers: mapboxgl.Marker[]
): mapboxgl.Marker[] {
  // Remove existing markers
  existingMarkers.forEach((m) => m.remove());

  const markers: mapboxgl.Marker[] = [];

  // Origin marker (green)
  const originEl = document.createElement("div");
  originEl.className = "origin-marker";
  originEl.style.cssText =
    "width:16px;height:16px;background:#10B981;border:3px solid white;border-radius:50%;box-shadow:0 0 8px rgba(16,185,129,0.5)";
  markers.push(
    new mapboxgl.Marker(originEl)
      .setLngLat([origin.lng, origin.lat])
      .setPopup(new mapboxgl.Popup().setText("Origin"))
      .addTo(map)
  );

  // Destination marker (red)
  const destEl = document.createElement("div");
  destEl.className = "dest-marker";
  destEl.style.cssText =
    "width:16px;height:16px;background:#EF4444;border:3px solid white;border-radius:50%;box-shadow:0 0 8px rgba(239,68,68,0.5)";
  markers.push(
    new mapboxgl.Marker(destEl)
      .setLngLat([destination.lng, destination.lat])
      .setPopup(new mapboxgl.Popup().setText("Destination"))
      .addTo(map)
  );

  return markers;
}

export function fitToRoute(
  map: mapboxgl.Map,
  route: RouteOption,
  padding: number = 80
) {
  const bounds = new mapboxgl.LngLatBounds();

  for (const segment of route.segments) {
    if (segment.geometry?.coordinates) {
      for (const coord of segment.geometry.coordinates) {
        bounds.extend(coord as [number, number]);
      }
    }
  }

  if (!bounds.isEmpty()) {
    map.fitBounds(bounds, { padding, duration: 1000 });
  }
}

export function updateVehicles(
  map: mapboxgl.Map,
  vehicles: VehiclePosition[]
) {
  const geojson: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: vehicles.map((v) => ({
      type: "Feature" as const,
      properties: {
        vehicle_id: v.vehicle_id,
        route_id: v.route_id,
        bearing: v.bearing || 0,
      },
      geometry: {
        type: "Point" as const,
        coordinates: [v.longitude, v.latitude],
      },
    })),
  };

  if (map.getSource(VEHICLES_SOURCE)) {
    (map.getSource(VEHICLES_SOURCE) as mapboxgl.GeoJSONSource).setData(geojson);
  } else {
    map.addSource(VEHICLES_SOURCE, { type: "geojson", data: geojson });
    map.addLayer({
      id: "vehicles-layer",
      type: "circle",
      source: VEHICLES_SOURCE,
      paint: {
        "circle-radius": 4,
        "circle-color": "#FFCC00",
        "circle-opacity": 0.8,
        "circle-stroke-width": 1,
        "circle-stroke-color": "#000",
      },
    });
  }
}
