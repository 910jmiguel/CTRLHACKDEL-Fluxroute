"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition } from "@/lib/types";
import { MAPBOX_TOKEN, TORONTO_CENTER, TORONTO_ZOOM, MAP_STYLE } from "@/lib/constants";
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
}

export default function FluxMap({
  selectedRoute,
  routes,
  origin,
  destination,
  vehicles,
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
