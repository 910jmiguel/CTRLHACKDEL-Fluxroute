"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition } from "@/lib/types";
import { MAPBOX_TOKEN, TORONTO_CENTER, TORONTO_ZOOM, MAP_STYLE } from "@/lib/constants";
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
  onMapClick?: (coord: { lat: number; lng: number }) => void;
}

export default function FluxMap({
  selectedRoute,
  routes,
  origin,
  destination,
  vehicles,
  theme,
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

  // Click handler for setting origin/destination on map (always active when onMapClick provided)
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
    </div>
  );
}
