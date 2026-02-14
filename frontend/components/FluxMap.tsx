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
  onMapClick?: (coord: { lat: number; lng: number }) => void;
}

export default function FluxMap({
  selectedRoute,
  routes,
  origin,
  destination,
  vehicles,
  theme,
  showTraffic,
  onMapClick,
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
      new mapboxgl.NavigationControl({ showCompass: true }),
      "top-right"
    );

    map.current.addControl(
      new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: false,
        showUserHeading: false,
      }),
      "top-right"
    );

    map.current.on("load", () => {
      setMapLoaded(true);
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Resize map when container size changes (e.g. sidebar collapse/expand)
  useEffect(() => {
    if (!mapContainer.current || !map.current || !mapLoaded) return;

    const resize = () => map.current?.resize();
    const ro = new ResizeObserver(resize);
    ro.observe(mapContainer.current);
    return () => ro.disconnect();
  }, [mapLoaded]);

  // Apply theme when it changes
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    map.current.setConfigProperty("basemap", "lightPreset", theme);
  }, [theme, mapLoaded]);

  // Click handler for setting origin/destination on map
  useEffect(() => {
    if (!map.current || !mapLoaded || !onMapClick) return;

    const handler = (e: mapboxgl.MapMouseEvent) => {
      const coord = { lat: e.lngLat.lat, lng: e.lngLat.lng };
      onMapClick(coord);
    };

    map.current.on("click", handler);
    return () => {
      map.current?.off("click", handler);
    };
  }, [mapLoaded, onMapClick]);

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
      for (const layer of style.layers) {
        if (layer.id.includes("-cong-")) {
          m.on("mouseenter", layer.id, (e) => {
            m.getCanvas().style.cursor = "pointer";
            const feature = e.features?.[0];
            if (feature) {
              const congestion = feature.properties?.congestion || "unknown";
              const description = congestionDescriptions[congestion] || congestion;
              popup
                .setLngLat(e.lngLat)
                .setHTML(`<div style="font-size:12px;font-weight:500;padding:2px 4px">${description}</div>`)
                .addTo(m);
            }
          });

          m.on("mousemove", layer.id, (e) => {
            popup.setLngLat(e.lngLat);
          });

          m.on("mouseleave", layer.id, () => {
            m.getCanvas().style.cursor = "";
            popup.remove();
          });
        }
      }
    }

    return () => {
      popup.remove();
    };
  }, [routes, selectedRoute, mapLoaded]);

  // Update markers (show origin and/or destination when at least one is set)
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    if (!origin && !destination) {
      markers.current.forEach((m) => m.remove());
      markers.current = [];
      return;
    }

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

    try {
      if (showTraffic && routes.length > 0) {
        // Add traffic source if not present
        if (!m.getSource("mapbox-traffic")) {
          m.addSource("mapbox-traffic", {
            type: "vector",
            url: "mapbox://mapbox.mapbox-traffic-v1",
          });
        }
        // Add traffic layer if not present
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
            // Place before route layers so routes render on top
            m.getStyle()?.layers?.find((l) => l.id.startsWith("route-layer-"))?.id
          );
        }
        if (m.getLayer("traffic-flow-layer")) {
          m.setLayoutProperty("traffic-flow-layer", "visibility", "visible");
        }
      } else {
        // Hide traffic layer
        if (m.getLayer("traffic-flow-layer")) {
          m.setLayoutProperty("traffic-flow-layer", "visibility", "none");
        }
      }
    } catch (err) {
      console.warn("Failed to update traffic layer:", err);
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
