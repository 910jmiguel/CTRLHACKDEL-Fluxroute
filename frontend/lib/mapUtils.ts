import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition } from "./types";
import { MODE_COLORS, MAPBOX_TOKEN } from "./constants";

async function reverseGeocode(lng: number, lat: number): Promise<string> {
  if (!MAPBOX_TOKEN) return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  try {
    const res = await fetch(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${MAPBOX_TOKEN}&limit=1`
    );
    const data = await res.json();
    return data.features?.[0]?.place_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  } catch {
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }
}

// Mapbox Standard style uses slot-based rendering; "top" renders above 3D buildings
type LayerWithSlot = mapboxgl.AnyLayer & { slot?: string };

const ROUTE_SOURCE_PREFIX = "route-";
const ROUTE_LAYER_PREFIX = "route-layer-";
const VEHICLES_SOURCE = "vehicles-source";

export function clearRoutes(map: mapboxgl.Map) {
  try {
    const style = map.getStyle();
    if (!style || !style.layers) return;

    for (const layer of style.layers) {
      if (layer.id.startsWith(ROUTE_LAYER_PREFIX)) {
        if (map.getLayer(layer.id)) {
          map.removeLayer(layer.id);
        }
      }
    }

    for (const sourceId of Object.keys(style.sources || {})) {
      if (sourceId.startsWith(ROUTE_SOURCE_PREFIX)) {
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }
      }
    }
  } catch (err) {
    console.error("clearRoutes failed:", err);
  }
}

export function drawMultimodalRoute(
  map: mapboxgl.Map,
  route: RouteOption,
  isSelected: boolean = true
) {
  route.segments.forEach((segment, idx) => {
    try {
      if (
        !segment.geometry?.coordinates?.length ||
        segment.geometry.coordinates.length < 2
      ) {
        console.warn(`Skipping segment ${idx}: invalid geometry`);
        return;
      }

      const sourceId = `${ROUTE_SOURCE_PREFIX}${route.id}-${idx}`;
      const layerId = `${ROUTE_LAYER_PREFIX}${route.id}-${idx}`;

      // Remove existing
      if (map.getLayer(layerId)) map.removeLayer(layerId);
      if (map.getSource(sourceId)) map.removeSource(sourceId);

      const color = segment.color || MODE_COLORS[segment.mode] || "#FFFFFF";

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
        slot: "top",
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
      } as LayerWithSlot);
    } catch (err) {
      console.error(`Failed to draw segment ${idx} of route ${route.id}:`, err);
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

  // Origin marker (green) - only when origin is set
  if (origin) {
    const originEl = document.createElement("div");
    originEl.className = "origin-marker";
    originEl.style.cssText =
      "width:16px;height:16px;background:#10B981;border:3px solid white;border-radius:50%;box-shadow:0 0 8px rgba(16,185,129,0.5)";
    const originPopup = new mapboxgl.Popup().setHTML(
      "<b>Origin</b><br><small>Loading address...</small>"
    );
    markers.push(
      new mapboxgl.Marker(originEl)
        .setLngLat([origin.lng, origin.lat])
        .setPopup(originPopup)
        .addTo(map)
    );
    reverseGeocode(origin.lng, origin.lat).then((addr) => {
      originPopup.setHTML(`<b>Origin</b><br><small>${addr}</small>`);
    });
  }

  // Destination marker (red) - only when destination is set
  if (destination) {
    const destEl = document.createElement("div");
    destEl.className = "dest-marker";
    destEl.style.cssText =
      "width:16px;height:16px;background:#EF4444;border:3px solid white;border-radius:50%;box-shadow:0 0 8px rgba(239,68,68,0.5)";
    const destPopup = new mapboxgl.Popup().setHTML(
      "<b>Destination</b><br><small>Loading address...</small>"
    );
    markers.push(
      new mapboxgl.Marker(destEl)
        .setLngLat([destination.lng, destination.lat])
        .setPopup(destPopup)
        .addTo(map)
    );
    reverseGeocode(destination.lng, destination.lat).then((addr) => {
      destPopup.setHTML(`<b>Destination</b><br><small>${addr}</small>`);
    });
  }

  return markers;
}

export function fitToRoute(
  map: mapboxgl.Map,
  route: RouteOption,
  padding: number = 80
) {
  try {
    const bounds = new mapboxgl.LngLatBounds();

    for (const segment of route.segments) {
      if (segment.geometry?.coordinates) {
        for (const coord of segment.geometry.coordinates) {
          if (Array.isArray(coord) && coord.length >= 2) {
            bounds.extend(coord as [number, number]);
          }
        }
      }
    }

    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding, duration: 1000 });
    }
  } catch (err) {
    console.error("fitToRoute failed:", err);
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
      slot: "top",
      paint: {
        "circle-radius": 4,
        "circle-color": "#FFCC00",
        "circle-opacity": 0.8,
        "circle-stroke-width": 1,
        "circle-stroke-color": "#000",
      },
    } as LayerWithSlot);
  }
}
