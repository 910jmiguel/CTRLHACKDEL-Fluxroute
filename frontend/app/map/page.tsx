"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Coordinate, VehiclePosition, TransitLinesData, RouteOption, IsochroneResponse } from "@/lib/types";
import { useRoutes } from "@/hooks/useRoutes";
import { useNavigation } from "@/hooks/useNavigation";
import { useTimeBasedTheme } from "@/hooks/useTimeBasedTheme";
import { getVehicles, getTransitLines } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FluxMap from "@/components/FluxMap";
import ChatAssistant from "@/components/ChatAssistant";
import LiveAlerts from "@/components/LiveAlerts";
import LoadingOverlay from "@/components/LoadingOverlay";
import NavigationView from "@/components/NavigationView";
import RouteBuilderModal from "@/components/RouteBuilderModal";

export default function MapPage() {
  const {
    routes,
    filteredRoutes,
    selectedRoute,
    loading,
    error,
    activeFilter,
    setActiveFilter,
    fetchRoutes,
    selectRoute,
    clearRoutes,
    addCustomRoute,
  } = useRoutes();

  const { theme } = useTimeBasedTheme();
  const [origin, setOrigin] = useState<Coordinate | null>(null);
  const [destination, setDestination] = useState<Coordinate | null>(null);
  const [vehicles, setVehicles] = useState<VehiclePosition[]>([]);
  const [showTraffic, setShowTraffic] = useState(true);
  const [transitLines, setTransitLines] = useState<TransitLinesData | null>(null);
  const [originLabel, setOriginLabel] = useState<string | null>(null);
  const [showRouteBuilder, setShowRouteBuilder] = useState(false);
  const [customizeBaseRoute, setCustomizeBaseRoute] = useState<RouteOption | null>(null);
  const [isochroneData, setIsochroneData] = useState<IsochroneResponse | null>(null);

  const navigation = useNavigation({
    onReroute: (newRoute) => {
      console.log("Navigation: rerouted", newRoute);
    },
    onArrival: () => {
      console.log("Navigation: arrived at destination");
    },
    onError: (err) => {
      console.error("Navigation error:", err);
    },
  });

  const handleStartNavigation = useCallback(() => {
    if (destination) {
      if (origin) {
        navigation.startNavigation(origin, destination);
      } else if ("geolocation" in navigator) {
        // Auto-geolocate if no origin set
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const geoOrigin = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            setOriginLabel("Current Location");
            setOrigin(geoOrigin);
            navigation.startNavigation(geoOrigin, destination);
          },
          (err) => {
            console.error("Geolocation failed:", err.message);
          },
          { enableHighAccuracy: true, timeout: 10000 }
        );
      }
    }
  }, [origin, destination, navigation.startNavigation]);

  const prevOriginRef = useRef<Coordinate | null>(null);
  const prevDestRef = useRef<Coordinate | null>(null);

  // Always keep UI in dark mode (map still uses time-based theme)
  useEffect(() => {
    document.documentElement.dataset.theme = "dark";
  }, []);

  // Fetch transit line overlay on mount (always-visible subway/rail/LRT)
  useEffect(() => {
    getTransitLines()
      .then(setTransitLines)
      .catch(() => {
        // Silent fail — transit overlay is non-critical
      });
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
      if (destination) {
        fetchRoutes(coord, destination);
      }
    } else {
      setDestination(coord);
      if (origin) {
        fetchRoutes(origin, coord);
      }
    }
  }, [origin, destination, fetchRoutes]);

  const handleCustomize = useCallback((route: RouteOption) => {
    setCustomizeBaseRoute(route);
    setShowRouteBuilder(true);
  }, []);

  const handleCustomRouteCalculated = useCallback((route: RouteOption) => {
    addCustomRoute(route);
    setShowRouteBuilder(false);
    setCustomizeBaseRoute(null);
  }, [addCustomRoute]);

  // Keep refs in sync (no auto-search — routes are fetched only via Find Routes or swap)
  useEffect(() => {
    prevOriginRef.current = origin;
  }, [origin]);

  useEffect(() => {
    prevDestRef.current = destination;
  }, [destination]);

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
      {/* Navigation HUD overlay */}
      <NavigationView
        isNavigating={navigation.isNavigating}
        currentInstruction={navigation.currentInstruction}
        nextInstruction={navigation.nextInstruction}
        stepIndex={navigation.stepIndex}
        totalSteps={navigation.totalSteps}
        remainingDistanceKm={navigation.remainingDistanceKm}
        totalDistanceKm={navigation.totalDistanceKm}
        remainingDurationMin={navigation.remainingDurationMin}
        eta={navigation.eta}
        speedLimit={navigation.speedLimit}
        voiceMuted={navigation.voiceMuted}
        laneGuidance={navigation.laneGuidance}
        onStopNavigation={navigation.stopNavigation}
        onToggleVoice={navigation.toggleVoice}
      />

      {/* Top alert banner */}
      <LiveAlerts />

      {/* Main content */}
      <div className="flex-1 flex relative">
        {/* Sidebar */}
        <Sidebar
          routes={routes}
          filteredRoutes={filteredRoutes}
          selectedRoute={selectedRoute}
          loading={loading}
          error={error}
          onSearch={handleSearch}
          onSelectRoute={selectRoute}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
          showTraffic={showTraffic}
          onToggleTraffic={() => setShowTraffic(!showTraffic)}
          originLabel={originLabel}
          origin={origin}
          destination={destination}
          onClearOrigin={handleClearOrigin}
          onClearDestination={handleClearDestination}
          onSwap={handleSwap}
          onClearRoutes={clearRoutes}
          onCustomize={handleCustomize}
          onStartNavigation={selectedRoute && origin && destination ? handleStartNavigation : undefined}
          isNavigating={navigation.isNavigating}
          isochroneData={isochroneData}
          onIsochroneLoaded={setIsochroneData}
          onClearIsochrone={() => setIsochroneData(null)}
        />

        {/* Map */}
        <div className="flex-1 relative">
          <FluxMap
            selectedRoute={navigation.isNavigating && navigation.navigationRoute
              ? navigation.navigationRoute.route
              : selectedRoute}
            routes={navigation.isNavigating && navigation.navigationRoute
              ? [navigation.navigationRoute.route]
              : routes}
            origin={origin}
            destination={destination}
            vehicles={vehicles}
            theme={theme}
            showTraffic={showTraffic}
            transitLines={transitLines}
            isochroneData={isochroneData}
            userPosition={navigation.currentPosition}
            isNavigating={navigation.isNavigating}
            onMapClick={navigation.isNavigating ? undefined : handleMapClick}
            onGeolocate={handleGeolocate}
            onMarkerDrag={navigation.isNavigating ? undefined : handleMarkerDrag}
          />

          {/* Loading overlay */}
          {loading && <LoadingOverlay />}
        </div>

        {/* Chat assistant */}
        <ChatAssistant />
      </div>

      {/* Route Builder Modal */}
      {showRouteBuilder && (
        <RouteBuilderModal
          baseRoute={customizeBaseRoute}
          origin={origin}
          destination={destination}
          onClose={() => { setShowRouteBuilder(false); setCustomizeBaseRoute(null); }}
          onRouteCalculated={handleCustomRouteCalculated}
        />
      )}
    </div>
  );
}
