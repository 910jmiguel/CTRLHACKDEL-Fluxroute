import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition } from "./types";
import { MODE_COLORS, CONGESTION_COLORS } from "./constants";

const ROUTE_SOURCE_PREFIX = "route-";
const ROUTE_LAYER_PREFIX = "route-layer-";
const VEHICLES_SOURCE = "vehicles-source";

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
    const baseSourceId = `${ROUTE_SOURCE_PREFIX}${route.id}-${idx}`;
    const baseLayerId = `${ROUTE_LAYER_PREFIX}${route.id}-${idx}`;

    // Check if this driving segment has multi-colored congestion sub-segments
    if (
      segment.mode === "driving" &&
      segment.congestion_segments &&
      segment.congestion_segments.length > 0
    ) {
      // --- Dark outline layer (full geometry, underneath) ---
      const outlineSourceId = `${baseSourceId}-outline`;
      const outlineLayerId = `${baseLayerId}-outline`;

      if (map.getLayer(outlineLayerId)) map.removeLayer(outlineLayerId);
      if (map.getSource(outlineSourceId)) map.removeSource(outlineSourceId);

      map.addSource(outlineSourceId, {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: segment.geometry,
        },
      });

      map.addLayer({
        id: outlineLayerId,
        type: "line",
        source: outlineSourceId,
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#1a1a2e",
          "line-width": isSelected ? 8 : 5,
          "line-opacity": isSelected ? 0.9 : 0.4,
        },
      });

      // --- Colored sub-segment layers (on top) ---
      segment.congestion_segments.forEach((sub, subIdx) => {
        const subSourceId = `${baseSourceId}-cong-${subIdx}`;
        const subLayerId = `${baseLayerId}-cong-${subIdx}`;

        if (map.getLayer(subLayerId)) map.removeLayer(subLayerId);
        if (map.getSource(subSourceId)) map.removeSource(subSourceId);

        const subColor =
          CONGESTION_COLORS[sub.congestion] || CONGESTION_COLORS.unknown;

        map.addSource(subSourceId, {
          type: "geojson",
          data: {
            type: "Feature",
            properties: { congestion: sub.congestion },
            geometry: sub.geometry,
          },
        });

        map.addLayer({
          id: subLayerId,
          type: "line",
          source: subSourceId,
          layout: { "line-join": "round", "line-cap": "round" },
          paint: {
            "line-color": subColor,
            "line-width": isSelected ? 5 : 3,
            "line-opacity": isSelected ? 0.9 : 0.5,
          },
        });
      });
    } else {
      // --- Standard single-color segment (non-driving or no congestion data) ---
      if (map.getLayer(baseLayerId)) map.removeLayer(baseLayerId);
      if (map.getSource(baseSourceId)) map.removeSource(baseSourceId);

      const color =
        segment.color || MODE_COLORS[segment.mode] || "#FFFFFF";

      map.addSource(baseSourceId, {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: segment.geometry,
        },
      });

      map.addLayer({
        id: baseLayerId,
        type: "line",
        source: baseSourceId,
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": color,
          "line-width": isSelected ? 5 : 3,
          "line-opacity": isSelected ? 0.9 : 0.4,
          ...(segment.mode === "walking"
            ? { "line-dasharray": [2, 2] }
            : {}),
        },
      });
    }
  });
}

export function addMarkers(
  map: mapboxgl.Map,
  origin: { lat: number; lng: number } | null,
  destination: { lat: number; lng: number } | null,
  existingMarkers: mapboxgl.Marker[]
): mapboxgl.Marker[] {
  // Remove existing markers
  existingMarkers.forEach((m) => m.remove());

  const markers: mapboxgl.Marker[] = [];

  // Origin marker (green)
  if (origin) {
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
  }

  // Destination marker (red)
  if (destination) {
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
  }

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
