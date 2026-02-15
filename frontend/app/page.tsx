"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Coordinate, VehiclePosition } from "@/lib/types";
import { useRoutes } from "@/hooks/useRoutes";
import { useTimeBasedTheme } from "@/hooks/useTimeBasedTheme";
import { getVehicles } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FluxMap from "@/components/FluxMap";
import ChatAssistant from "@/components/ChatAssistant";
import LiveAlerts from "@/components/LiveAlerts";
import LoadingOverlay from "@/components/LoadingOverlay";

export default function Home() {
  const {
    routes,
    selectedRoute,
    loading,
    error,
    fetchRoutes,
    selectRoute,
    clearRoutes,
  } = useRoutes();

  const { theme } = useTimeBasedTheme();
  const [origin, setOrigin] = useState<Coordinate | null>(null);
  const [destination, setDestination] = useState<Coordinate | null>(null);
  const [vehicles, setVehicles] = useState<VehiclePosition[]>([]);
  const [showTraffic, setShowTraffic] = useState(true);
  const [originLabel, setOriginLabel] = useState<string | null>(null);

  const prevOriginRef = useRef<Coordinate | null>(null);
  const prevDestRef = useRef<Coordinate | null>(null);

  // Always keep UI in dark mode (map still uses time-based theme)
  useEffect(() => {
    document.documentElement.dataset.theme = "dark";
  }, []);

  const handleSearch = useCallback(
    (orig: Coordinate, dest: Coordinate) => {
      setOrigin(orig);
      setDestination(dest);
      // Update refs so auto-search effect doesn't double-fire
      prevOriginRef.current = orig;
      prevDestRef.current = dest;
      fetchRoutes(orig, dest);
    },
    [fetchRoutes]
  );

  const handleMapClick = useCallback((coord: { lat: number; lng: number }) => {
    if (!origin) {
      setOriginLabel(null);
      setOrigin(coord);
    } else {
      setDestination(coord);
    }
  }, [origin]);

  const handleGeolocate = useCallback((coord: { lat: number; lng: number }) => {
    setOriginLabel("Current Location");
    setOrigin(coord);
  }, []);

  const handleClearOrigin = useCallback(() => {
    setOrigin(null);
    setOriginLabel(null);
    prevOriginRef.current = null;
  }, []);

  const handleClearDestination = useCallback(() => {
    setDestination(null);
    prevDestRef.current = null;
  }, []);

  const handleSwap = useCallback((newOrigin: Coordinate | null, newDest: Coordinate | null) => {
    setOrigin(newOrigin);
    setDestination(newDest);
    setOriginLabel(null);
    prevOriginRef.current = newOrigin;
    prevDestRef.current = newDest;
    if (newOrigin && newDest) {
      fetchRoutes(newOrigin, newDest);
    }
  }, [fetchRoutes]);

  const handleMarkerDrag = useCallback((type: "origin" | "destination", coord: { lat: number; lng: number }) => {
    if (type === "origin") {
      setOriginLabel(null);
      setOrigin(coord);
    } else {
      setDestination(coord);
    }
  }, []);

  // Auto-search when both origin and destination are set via map clicks
  useEffect(() => {
    if (!origin || !destination) return;
    const originChanged =
      prevOriginRef.current?.lat !== origin.lat ||
      prevOriginRef.current?.lng !== origin.lng;
    const destChanged =
      prevDestRef.current?.lat !== destination.lat ||
      prevDestRef.current?.lng !== destination.lng;

    prevOriginRef.current = origin;
    prevDestRef.current = destination;

    if (originChanged || destChanged) {
      fetchRoutes(origin, destination);
    }
  }, [origin, destination, fetchRoutes]);

  // Poll vehicles every 15 seconds
  useEffect(() => {
    const fetchVehicles = async () => {
      try {
        const data = await getVehicles();
        setVehicles(data.vehicles || []);
      } catch {
        // Silent fail
      }
    };

    fetchVehicles();
    const interval = setInterval(fetchVehicles, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      {/* Top alert banner */}
      <LiveAlerts />

      {/* Main content */}
      <div className="flex-1 flex relative">
        {/* Sidebar */}
        <Sidebar
          routes={routes}
          selectedRoute={selectedRoute}
          loading={loading}
          error={error}
          onSearch={handleSearch}
          onSelectRoute={selectRoute}
          showTraffic={showTraffic}
          onToggleTraffic={() => setShowTraffic(!showTraffic)}
          originLabel={originLabel}
          origin={origin}
          destination={destination}
          onClearOrigin={handleClearOrigin}
          onClearDestination={handleClearDestination}
          onSwap={handleSwap}
          onClearRoutes={clearRoutes}
        />

        {/* Map */}
        <div className="flex-1 relative">
          <FluxMap
            selectedRoute={selectedRoute}
            routes={routes}
            origin={origin}
            destination={destination}
            vehicles={vehicles}
            theme={theme}
            showTraffic={showTraffic}
            onMapClick={handleMapClick}
            onGeolocate={handleGeolocate}
            onMarkerDrag={handleMarkerDrag}
          />

          {/* Loading overlay */}
          {loading && <LoadingOverlay />}
        </div>

        {/* Chat assistant */}
        <ChatAssistant />
      </div>
    </div>
  );
}
