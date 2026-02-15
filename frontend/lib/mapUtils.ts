import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition, TransitLinesData, IsochroneResponse } from "./types";
import { MODE_COLORS, CONGESTION_COLORS, ISOCHRONE_COLORS, ISOCHRONE_BORDER_COLORS } from "./constants";

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
          "line-width": isSelected ? 8 : 3,
          "line-opacity": isSelected ? 0.9 : 0.12,
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
            "line-width": isSelected ? 5 : 2,
            "line-opacity": isSelected ? 0.9 : 0.12,
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
          "line-width": isSelected ? 5 : 2,
          "line-opacity": isSelected ? 0.9 : 0.12,
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

const BUS_MARKER_IMAGE = "bus-marker-icon";

function _ensureBusMarkerImage(map: mapboxgl.Map, callback: () => void) {
  if (map.hasImage(BUS_MARKER_IMAGE)) {
    callback();
    return;
  }
  map.loadImage("/images/bus-marker.svg", (error, image) => {
    if (error || !image) {
      // Fallback: add a simple colored square so the symbol layer doesn't break
      // This shouldn't normally happen since the SVG is a local static asset
      callback();
      return;
    }
    if (!map.hasImage(BUS_MARKER_IMAGE)) {
      map.addImage(BUS_MARKER_IMAGE, image, { sdf: false });
    }
    callback();
  });
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

    _ensureBusMarkerImage(map, () => {
      if (map.hasImage(BUS_MARKER_IMAGE)) {
        map.addLayer({
          id: "vehicles-layer",
          type: "symbol",
          source: VEHICLES_SOURCE,
          layout: {
            "icon-image": BUS_MARKER_IMAGE,
            "icon-size": 0.55,
            "icon-rotate": ["get", "bearing"],
            "icon-rotation-alignment": "map",
            "icon-allow-overlap": true,
            "icon-ignore-placement": true,
          },
        });
      } else {
        // Fallback to circle layer if image failed to load
        map.addLayer({
          id: "vehicles-layer",
          type: "circle",
          source: VEHICLES_SOURCE,
          paint: {
            "circle-radius": 5,
            "circle-color": "#E53935",
            "circle-opacity": 0.9,
            "circle-stroke-width": 2,
            "circle-stroke-color": "#fff",
          },
        });
      }
    });
  }
}

export function clearVehicles(map: mapboxgl.Map) {
  if (map.getLayer("vehicles-layer")) map.removeLayer("vehicles-layer");
  if (map.getSource(VEHICLES_SOURCE)) map.removeSource(VEHICLES_SOURCE);
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

export function setTransitOverlayDimmed(map: mapboxgl.Map, dimmed: boolean) {
  try {
    if (map.getLayer(TRANSIT_LINES_LAYER)) {
      map.setPaintProperty(TRANSIT_LINES_LAYER, "line-opacity", dimmed ? 0.15 : 0.6);
    }
    if (map.getLayer(TRANSIT_LINES_CASING)) {
      map.setPaintProperty(TRANSIT_LINES_CASING, "line-opacity", dimmed ? 0.1 : 0.3);
    }
    if (map.getLayer(TRANSIT_STATIONS_LAYER)) {
      map.setPaintProperty(TRANSIT_STATIONS_LAYER, "circle-opacity", dimmed ? 0.25 : 0.85);
      map.setPaintProperty(TRANSIT_STATIONS_LAYER, "circle-stroke-opacity", dimmed ? 0.15 : 0.7);
    }
    if (map.getLayer(TRANSIT_STATION_LABELS)) {
      map.setPaintProperty(
        TRANSIT_STATION_LABELS,
        "text-opacity",
        dimmed
          ? 0.3
          : ["interpolate", ["linear"], ["zoom"], 11, 0, 12, 1]
      );
    }
  } catch {
    // Layers may not exist yet
  }
}

// --- Navigation Map Utils (Phase 1 & 2) ---

const ISOCHRONE_SOURCE_PREFIX = "isochrone-";
const ISOCHRONE_FILL_PREFIX = "isochrone-fill-";
const ISOCHRONE_BORDER_PREFIX = "isochrone-border-";
const ALT_ROUTE_SOURCE_PREFIX = "alt-route-";
const ALT_ROUTE_LAYER_PREFIX = "alt-route-layer-";

export function drawIsochrone(map: mapboxgl.Map, data: IsochroneResponse) {
  clearIsochrone(map);

  const features = data.geojson.features || [];

  features.forEach((feature, idx) => {
    const sourceId = `${ISOCHRONE_SOURCE_PREFIX}${idx}`;
    const fillId = `${ISOCHRONE_FILL_PREFIX}${idx}`;
    const borderId = `${ISOCHRONE_BORDER_PREFIX}${idx}`;

    const fillColor = ISOCHRONE_COLORS[idx] || ISOCHRONE_COLORS[ISOCHRONE_COLORS.length - 1];
    const borderColor = ISOCHRONE_BORDER_COLORS[idx] || ISOCHRONE_BORDER_COLORS[ISOCHRONE_BORDER_COLORS.length - 1];

    map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "Feature",
        properties: feature.properties || {},
        geometry: feature.geometry,
      },
    });

    // Fill layer
    map.addLayer({
      id: fillId,
      type: "fill",
      source: sourceId,
      paint: {
        "fill-color": fillColor,
        "fill-opacity": 0.15 - idx * 0.03,
      },
    });

    // Border layer
    map.addLayer({
      id: borderId,
      type: "line",
      source: sourceId,
      paint: {
        "line-color": borderColor,
        "line-width": 2,
        "line-opacity": 0.7,
        "line-dasharray": [3, 2],
      },
    });
  });
}

export function clearIsochrone(map: mapboxgl.Map) {
  const style = map.getStyle();
  if (!style?.layers) return;

  for (const layer of style.layers) {
    if (
      layer.id.startsWith(ISOCHRONE_FILL_PREFIX) ||
      layer.id.startsWith(ISOCHRONE_BORDER_PREFIX)
    ) {
      map.removeLayer(layer.id);
    }
  }

  for (const sourceId of Object.keys(style.sources || {})) {
    if (sourceId.startsWith(ISOCHRONE_SOURCE_PREFIX)) {
      map.removeSource(sourceId);
    }
  }
}

export function drawAlternativeRoutes(
  map: mapboxgl.Map,
  alternatives: RouteOption[]
) {
  clearAlternativeRoutes(map);

  alternatives.forEach((alt, idx) => {
    alt.segments.forEach((segment, segIdx) => {
      const sourceId = `${ALT_ROUTE_SOURCE_PREFIX}${idx}-${segIdx}`;
      const layerId = `${ALT_ROUTE_LAYER_PREFIX}${idx}-${segIdx}`;

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
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#6B7280",
          "line-width": 4,
          "line-opacity": 0.4,
          "line-dasharray": [4, 3],
        },
      });
    });
  });
}

export function clearAlternativeRoutes(map: mapboxgl.Map) {
  const style = map.getStyle();
  if (!style?.layers) return;

  for (const layer of style.layers) {
    if (layer.id.startsWith(ALT_ROUTE_LAYER_PREFIX)) {
      map.removeLayer(layer.id);
    }
  }

  for (const sourceId of Object.keys(style.sources || {})) {
    if (sourceId.startsWith(ALT_ROUTE_SOURCE_PREFIX)) {
      map.removeSource(sourceId);
    }
  }
}
