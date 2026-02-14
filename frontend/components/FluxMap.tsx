"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition } from "@/lib/types";
import { MAPBOX_TOKEN, TORONTO_CENTER, TORONTO_ZOOM, MAP_STYLE, CONGESTION_COLORS } from "@/lib/constants";
import type { MapTheme } from "@/hooks/useTimeBasedTheme";
import {
  clearRoutes,
  drawMultimodalRoute,
  addMarkers,
  fitToRoute,
  updateVehicles,
} from "@/lib/mapUtils";

interface FluxMapProps {
  selectedRoute: RouteOption | null;
  routes: RouteOption[];
  origin: { lat: number; lng: number } | null;
  destination: { lat: number; lng: number } | null;
  vehicles: VehiclePosition[];
  theme: MapTheme;
  showTraffic: boolean;
}

export default function FluxMap({
  selectedRoute,
  routes,
  origin,
  destination,
  vehicles,
  theme,
  showTraffic,
}: FluxMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markers = useRef<mapboxgl.Marker[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: MAP_STYLE,
      center: TORONTO_CENTER,
      zoom: TORONTO_ZOOM,
      attributionControl: false,
    });

    map.current.addControl(
      new mapboxgl.NavigationControl({ showCompass: false }),
      "bottom-right"
    );

    map.current.on("load", () => {
      setMapLoaded(true);
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Apply theme when it changes
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    map.current.setConfigProperty("basemap", "lightPreset", theme);
  }, [theme, mapLoaded]);

  // Draw routes when they change
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    clearRoutes(map.current);

    // Draw non-selected routes first (dimmer)
    routes.forEach((route) => {
      if (route.id !== selectedRoute?.id) {
        drawMultimodalRoute(map.current!, route, false);
      }
    });

    // Draw selected route on top
    if (selectedRoute) {
      drawMultimodalRoute(map.current, selectedRoute, true);
      fitToRoute(map.current, selectedRoute);
    }

    // Register congestion tooltips on sub-segment layers
    const m = map.current;
    const popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "congestion-tooltip",
    });

    const congestionDescriptions: Record<string, string> = {
      low: "Light Traffic — flowing smoothly",
      moderate: "Moderate Traffic — some slowdowns",
      heavy: "Heavy Traffic — expect delays",
      severe: "Severe Traffic — significant delays",
    };

    const style = m.getStyle();
    if (style?.layers) {
      style.layers.forEach((layer) => {
        if (layer.id.startsWith("route-layer-congestion-")) {
          // ... (existing congestion logic) ...
          m.on("mouseenter", layer.id, (e) => {
            m.getCanvas().style.cursor = "pointer";
            if (e.features && e.features[0]) {
              const congestion = e.features[0].properties?.congestion as string;
              const desc = congestionDescriptions[congestion] || congestion;
              popup.setLngLat(e.lngLat).setHTML(desc).addTo(m!);
            }
          });
          m.on("mouseleave", layer.id, () => {
            m.getCanvas().style.cursor = "";
            popup.remove();
          });
        }
      });
    }

    // Road Closure Tooltips
    ["road-closure-line", "road-closure-symbol"].forEach((layerId) => {
      // Only register if layer exists (might be added async, but we are in useEffect depending on showTraffic)
      // Actually, these events bind even if layer doesn't exist yet? No.
      // But we just added them in the same render cycle (effectively).
      // Safer to check if getLayer returns something, but 'on' listener doesn't throw.
      m.on("mouseenter", layerId, (e) => {
        m.getCanvas().style.cursor = "pointer";
        if (e.features && e.features[0]) {
          const props = e.features[0].properties;
          if (props) {
            const road = props.road || "Road Closure";
            const desc = props.description || props.reason || "No details available";
            const time = props.planned_end_date ? `<br><span class="text-[9px] text-slate-400">Ends: ${new Date(props.planned_end_date).toLocaleDateString()}</span>` : "";

            popup.setLngLat(e.lngLat).setHTML(
              `<div class="font-bold">${road}</div><div class="text-xs">${desc}</div>${time}`
            ).addTo(m!);
          }
        }
      });
      m.on("mouseleave", layerId, () => {
        m.getCanvas().style.cursor = "";
        popup.remove();
      });
    });



    return () => {
      popup.remove();
    };
  }, [routes, selectedRoute, mapLoaded]);

  // Update markers
  useEffect(() => {
    if (!map.current || !mapLoaded || !origin || !destination) return;

    markers.current = addMarkers(
      map.current,
      origin,
      destination,
      markers.current
    );
  }, [origin, destination, mapLoaded]);

  // Update vehicle positions
  useEffect(() => {
    if (!map.current || !mapLoaded || vehicles.length === 0) return;
    updateVehicles(map.current, vehicles);
  }, [vehicles, mapLoaded]);

  // Manage traffic tileset layer
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    // Manage traffic tileset & road closures
    try {
      if (showTraffic) { // Show if toggle is ON (regardless of route presence)
        // 1. Mapbox Traffic Flow
        if (!m.getSource("mapbox-traffic")) {
          m.addSource("mapbox-traffic", {
            type: "vector",
            url: "mapbox://mapbox.mapbox-traffic-v1",
          });
        }
        if (!m.getLayer("traffic-flow-layer")) {
          m.addLayer(
            {
              id: "traffic-flow-layer",
              type: "line",
              source: "mapbox-traffic",
              "source-layer": "traffic",
              paint: {
                "line-color": [
                  "match",
                  ["get", "congestion"],
                  "low", CONGESTION_COLORS.low,
                  "moderate", CONGESTION_COLORS.moderate,
                  "heavy", CONGESTION_COLORS.heavy,
                  "severe", CONGESTION_COLORS.severe,
                  CONGESTION_COLORS.unknown,
                ],
                "line-width": 1.5,
                "line-opacity": 0.4,
              },
            },
            m.getStyle()?.layers?.find((l) => l.id.startsWith("route-layer-"))?.id
          );
        }
        if (m.getLayer("traffic-flow-layer")) {
          m.setLayoutProperty("traffic-flow-layer", "visibility", "visible");
        }

        // 2. Road Closures (Toronto Open Data)
        if (!m.getSource("road-closures")) {
          m.addSource("road-closures", {
            type: "geojson",
            data: "/api/road-closures", // Proxy to backend
          });
        }

        // Closure Lines (Red Dashed)
        if (!m.getLayer("road-closure-line")) {
          m.addLayer({
            id: "road-closure-line",
            type: "line",
            source: "road-closures",
            paint: {
              "line-color": "#EF4444", // Red
              "line-width": 3,
              "line-dasharray": [2, 2], // Dashed
              "line-opacity": 0.8,
            },
          });
        }
        if (m.getLayer("road-closure-line")) {
          m.setLayoutProperty("road-closure-line", "visibility", "visible");
        }

        // Closure Icons (Warning Symbol)
        if (!m.getLayer("road-closure-symbol")) {
          m.addLayer({
            id: "road-closure-symbol",
            type: "symbol",
            source: "road-closures",
            layout: {
              "icon-image": "road-closure", // Maki icon
              "icon-size": 1.2,
              "icon-allow-overlap": true,
              "text-field": "{road}", // Show road name
              "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
              "text-size": 10,
              "text-offset": [0, 1.5],
              "text-anchor": "top",
              "text-optional": true,
            },
            paint: {
              "text-color": "#FECaca", // Light red text
              "text-halo-color": "#000000",
              "text-halo-width": 1,
            },
          });
        }
        if (m.getLayer("road-closure-symbol")) {
          m.setLayoutProperty("road-closure-symbol", "visibility", "visible");
        }

      } else {
        // Hide all traffic layers
        if (m.getLayer("traffic-flow-layer")) m.setLayoutProperty("traffic-flow-layer", "visibility", "none");
        if (m.getLayer("road-closure-line")) m.setLayoutProperty("road-closure-line", "visibility", "none");
        if (m.getLayer("road-closure-symbol")) m.setLayoutProperty("road-closure-symbol", "visibility", "none");
      }
    } catch (err) {
      console.warn("Failed to update traffic/closure layers:", err);
    }
  }, [showTraffic, routes, mapLoaded]);

  return (
    <div ref={mapContainer} className="w-full h-full">
      {!MAPBOX_TOKEN && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900 z-10">
          <div className="glass-card p-6 text-center max-w-md">
            <h3 className="text-lg font-semibold mb-2">Map Not Configured</h3>
            <p className="text-sm text-slate-400">
              Set <code className="text-blue-400">NEXT_PUBLIC_MAPBOX_TOKEN</code> in{" "}
              <code className="text-blue-400">frontend/.env.local</code> to enable
              the map view.
            </p>
          </div>
        </div>
      )}

      {/* Traffic Legend - Positioned bottom-right to avoid Mapbox logo */}
      {showTraffic && routes.length > 0 && (
        <div className="absolute bottom-8 right-12 z-10 glass-card p-3 rounded-lg backdrop-blur-md bg-black/60 border border-slate-700/50 shadow-xl">
          <div className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Traffic Conditions
          </div>
          {["low", "moderate", "heavy", "severe"].map((level) => (
            <div key={level} className="flex items-center gap-2 py-0.5">
              <div
                className="w-3 h-3 rounded-full shadow-sm"
                style={{ backgroundColor: CONGESTION_COLORS[level] }}
              />
              <span className="text-xs text-slate-300 capitalize">{level}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
