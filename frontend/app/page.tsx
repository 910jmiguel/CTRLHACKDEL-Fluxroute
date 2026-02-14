"use client";

import { useState, useEffect, useCallback } from "react";
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
  } = useRoutes();

  const { theme, isDark } = useTimeBasedTheme();
  const [origin, setOrigin] = useState<Coordinate | null>(null);
  const [destination, setDestination] = useState<Coordinate | null>(null);
  const [vehicles, setVehicles] = useState<VehiclePosition[]>([]);
  const [showTraffic, setShowTraffic] = useState(true);

  // Always keep UI in dark mode (map still uses time-based theme)
  useEffect(() => {
    document.documentElement.dataset.theme = "dark";
  }, []);

  const handleSearch = useCallback(
    (orig: Coordinate, dest: Coordinate) => {
      setOrigin(orig);
      setDestination(dest);
      fetchRoutes(orig, dest);
    },
    [fetchRoutes]
  );

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
