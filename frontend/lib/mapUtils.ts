import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition, TransitLinesData } from "./types";
import { MODE_COLORS, CONGESTION_COLORS } from "./constants";

const ROUTE_SOURCE_PREFIX = "route-";
const ROUTE_LAYER_PREFIX = "route-layer-";
const VEHICLES_SOURCE = "vehicles-source";
const TRANSIT_LINES_SOURCE = "transit-lines-source";
const TRANSIT_STATIONS_SOURCE = "transit-stations-source";
const TRANSIT_LINES_CASING = "transit-lines-casing";
const TRANSIT_LINES_LAYER = "transit-lines-layer";
const TRANSIT_STATIONS_LAYER = "transit-stations-layer";
const TRANSIT_STATION_LABELS = "transit-station-labels";

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
  existingMarkers: mapboxgl.Marker[],
  onMarkerDrag?: (type: "origin" | "destination", coord: { lat: number; lng: number }) => void
): mapboxgl.Marker[] {
  // Remove existing markers
  existingMarkers.forEach((m) => m.remove());

  const markers: mapboxgl.Marker[] = [];

  // Origin marker (green) — draggable
  if (origin) {
    const originEl = document.createElement("div");
    originEl.className = "origin-marker";
    originEl.style.cssText =
      "width:16px;height:16px;background:#10B981;border:3px solid white;border-radius:50%;box-shadow:0 0 8px rgba(16,185,129,0.5);cursor:grab";
    const originMarker = new mapboxgl.Marker({ element: originEl, draggable: true })
      .setLngLat([origin.lng, origin.lat])
      .setPopup(new mapboxgl.Popup().setText("Origin"))
      .addTo(map);
    originMarker.on("dragend", () => {
      const lngLat = originMarker.getLngLat();
      onMarkerDrag?.("origin", { lat: lngLat.lat, lng: lngLat.lng });
    });
    markers.push(originMarker);
  }

  // Destination marker (red) — draggable
  if (destination) {
    const destEl = document.createElement("div");
    destEl.className = "dest-marker";
    destEl.style.cssText =
      "width:16px;height:16px;background:#EF4444;border:3px solid white;border-radius:50%;box-shadow:0 0 8px rgba(239,68,68,0.5);cursor:grab";
    const destMarker = new mapboxgl.Marker({ element: destEl, draggable: true })
      .setLngLat([destination.lng, destination.lat])
      .setPopup(new mapboxgl.Popup().setText("Destination"))
      .addTo(map);
    destMarker.on("dragend", () => {
      const lngLat = destMarker.getLngLat();
      onMarkerDrag?.("destination", { lat: lngLat.lat, lng: lngLat.lng });
    });
    markers.push(destMarker);
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

export function drawTransitOverlay(
  map: mapboxgl.Map,
  transitData: TransitLinesData
) {
  // Remove existing transit overlay if present
  removeTransitOverlay(map);

  // --- Lines source + layers ---
  map.addSource(TRANSIT_LINES_SOURCE, {
    type: "geojson",
    data: transitData.lines,
  });

  // Dark casing layer (outline) — fades in at higher zoom to avoid hiding color
  map.addLayer({
    id: TRANSIT_LINES_CASING,
    type: "line",
    source: TRANSIT_LINES_SOURCE,
    layout: { "line-join": "round", "line-cap": "round" },
    paint: {
      "line-color": "#0a0a1a",
      "line-width": [
        "interpolate", ["linear"], ["zoom"],
        8, 0,
        12, ["match", ["get", "mode"], "SUBWAY", 5, "RAIL", 4.5, "TRAM", 3.5, 4],
        16, ["match", ["get", "mode"], "SUBWAY", 7, "RAIL", 6, "TRAM", 5, 6],
      ],
      "line-opacity": [
        "interpolate", ["linear"], ["zoom"],
        8, 0,
        12, 0.3,
      ],
    },
  });

  // Colored line layer on top of casing
  map.addLayer({
    id: TRANSIT_LINES_LAYER,
    type: "line",
    source: TRANSIT_LINES_SOURCE,
    layout: { "line-join": "round", "line-cap": "round" },
    paint: {
      "line-color": ["get", "color"],
      "line-width": [
        "interpolate", ["linear"], ["zoom"],
        8, 1.5,
        12, ["match", ["get", "mode"], "SUBWAY", 3, "RAIL", 2.5, "TRAM", 2, 2.5],
        16, ["match", ["get", "mode"], "SUBWAY", 5, "RAIL", 4, "TRAM", 3, 4],
      ],
      "line-opacity": 0.85,
    },
  });

  // --- Stations source + layers ---
  map.addSource(TRANSIT_STATIONS_SOURCE, {
    type: "geojson",
    data: transitData.stations,
  });

  // Station circle markers
  map.addLayer({
    id: TRANSIT_STATIONS_LAYER,
    type: "circle",
    source: TRANSIT_STATIONS_SOURCE,
    paint: {
      "circle-radius": [
        "match",
        ["get", "mode"],
        "SUBWAY", 5,
        "RAIL", 5,
        "TRAM", 3.5,
        4,
      ],
      "circle-color": ["get", "color"],
      "circle-opacity": 0.85,
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-opacity": 0.7,
    },
  });

  // Station name labels
  map.addLayer({
    id: TRANSIT_STATION_LABELS,
    type: "symbol",
    source: TRANSIT_STATIONS_SOURCE,
    layout: {
      "text-field": ["get", "name"],
      "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
      "text-size": [
        "interpolate", ["linear"], ["zoom"],
        10, 0,     // hidden at low zoom
        12, 9,     // appear at zoom 12
        15, 12,
      ],
      "text-offset": [0, 1.2],
      "text-anchor": "top",
      "text-optional": true,
      "text-allow-overlap": false,
    },
    paint: {
      "text-color": "#e2e8f0",
      "text-halo-color": "#0f172a",
      "text-halo-width": 1.5,
      "text-opacity": [
        "interpolate", ["linear"], ["zoom"],
        11, 0,
        12, 1,
      ],
    },
  });
}

export function removeTransitOverlay(map: mapboxgl.Map) {
  for (const layerId of [
    TRANSIT_STATION_LABELS,
    TRANSIT_STATIONS_LAYER,
    TRANSIT_LINES_LAYER,
    TRANSIT_LINES_CASING,
  ]) {
    if (map.getLayer(layerId)) map.removeLayer(layerId);
  }
  if (map.getSource(TRANSIT_LINES_SOURCE)) map.removeSource(TRANSIT_LINES_SOURCE);
  if (map.getSource(TRANSIT_STATIONS_SOURCE)) map.removeSource(TRANSIT_STATIONS_SOURCE);
}
