"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import type { Coordinate, VehiclePosition, TransitLinesData, RouteOption, IsochroneResponse, ServiceAlert, ThemeMode, ViewMode } from "@/lib/types";
import { useRoutes } from "@/hooks/useRoutes";
import { useNavigation } from "@/hooks/useNavigation";
import { getVehicles, getTransitLines, getAlerts } from "@/lib/api";
import FluxMap from "@/components/FluxMap";
import ChatAssistant from "@/components/ChatAssistant";
import LoadingOverlay from "@/components/LoadingOverlay";
import NavigationView from "@/components/NavigationView";
import RouteBuilderModal from "@/components/RouteBuilderModal";
import MapLayersControl from "@/components/MapLayersControl";
import type { TransitLineVisibility } from "@/components/MapLayersControl";
import TopBar from "@/components/TopBar";
import RoutePanel from "@/components/RoutePanel";
import AlertsPanel from "@/components/AlertsPanel";
import DashboardView from "@/components/DashboardView";
import IsochronePanel from "@/components/IsochronePanel";

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

  // View & theme state
  const [viewMode, setViewMode] = useState<ViewMode>("map");
  const [theme, setTheme] = useState<ThemeMode>("dark");

  const [origin, setOrigin] = useState<Coordinate | null>(null);
  const [destination, setDestination] = useState<Coordinate | null>(null);
  const [vehicles, setVehicles] = useState<VehiclePosition[]>([]);
  const [showTraffic, setShowTraffic] = useState(true);
  const [transitLines, setTransitLines] = useState<TransitLinesData | null>(null);
  const [originLabel, setOriginLabel] = useState<string | null>(null);
  const [destinationLabel, setDestinationLabel] = useState<string | null>(null);
  const [showRouteBuilder, setShowRouteBuilder] = useState(false);
  const [customizeBaseRoute, setCustomizeBaseRoute] = useState<RouteOption | null>(null);
  const [isochroneData, setIsochroneData] = useState<IsochroneResponse | null>(null);

  // Panel states
  const [routePanelOpen, setRoutePanelOpen] = useState(false);
  const [alertsPanelOpen, setAlertsPanelOpen] = useState(false);
  const [alerts, setAlerts] = useState<ServiceAlert[]>([]);

  // Layer visibility state
  const [transitLineVisibility, setTransitLineVisibility] = useState<TransitLineVisibility>({
    line1: true,
    line2: true,
    line4: true,
    line5: true,
    line6: true,
    streetcars: true,
  });
  const [showVehicles, setShowVehicles] = useState(true);
  const [showUnselectedRoutes, setShowUnselectedRoutes] = useState(true);

  const handleToggleTransitLine = useCallback((key: keyof TransitLineVisibility) => {
    setTransitLineVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

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

  // Theme management
  useEffect(() => {
    const saved = localStorage.getItem("fluxroute-theme") as ThemeMode | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.dataset.theme = saved;
    } else {
      // Auto-detect from system preference
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      const initial = prefersDark ? "dark" : "dark"; // Default to dark
      setTheme(initial);
      document.documentElement.dataset.theme = initial;
    }
  }, []);

  const handleThemeToggle = useCallback(() => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("fluxroute-theme", next);
      return next;
    });
  }, []);

  const handleViewModeToggle = useCallback(() => {
    setViewMode((prev) => (prev === "dashboard" ? "map" : "dashboard"));
  }, []);

  // Fetch transit line overlay on mount
  useEffect(() => {
    getTransitLines()
      .then(setTransitLines)
      .catch(() => {});
  }, []);

  // Fetch alerts
  useEffect(() => {
    const fetchAlertsData = async () => {
      try {
        const data = await getAlerts();
        setAlerts(data.alerts || []);
      } catch {}
    };
    fetchAlertsData();
    const interval = setInterval(fetchAlertsData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = useCallback(
    (orig: Coordinate, dest: Coordinate) => {
      setOrigin(orig);
      setDestination(dest);
      prevOriginRef.current = orig;
      prevDestRef.current = dest;
      fetchRoutes(orig, dest);
      setRoutePanelOpen(true);
    },
    [fetchRoutes]
  );

  // Auto-open route panel when routes arrive
  useEffect(() => {
    if (routes.length > 0) {
      setRoutePanelOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routes.length]);

  const handleMapClick = useCallback((coord: { lat: number; lng: number }) => {
    if (!origin) {
      setOriginLabel(null);
      setOrigin(coord);
    } else {
      setDestination(coord);
      setDestinationLabel(null);
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
    clearRoutes();
  }, [clearRoutes]);

  const handleClearDestination = useCallback(() => {
    setDestination(null);
    setDestinationLabel(null);
    prevDestRef.current = null;
    clearRoutes();
  }, [clearRoutes]);

  const handleSwap = useCallback((newOrigin: Coordinate | null, newDest: Coordinate | null) => {
    setOrigin(newOrigin);
    setDestination(newDest);
    setOriginLabel(null);
    setDestinationLabel(null);
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
      if (destination) fetchRoutes(coord, destination);
    } else {
      setDestinationLabel(null);
      setDestination(coord);
      if (origin) fetchRoutes(origin, coord);
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

  // Keep refs in sync
  useEffect(() => { prevOriginRef.current = origin; }, [origin]);
  useEffect(() => { prevDestRef.current = destination; }, [destination]);

  // Poll vehicles every 15 seconds
  useEffect(() => {
    const fetchVehiclesData = async () => {
      try {
        const data = await getVehicles();
        setVehicles(data.vehicles || []);
      } catch {}
    };
    fetchVehiclesData();
    const interval = setInterval(fetchVehiclesData, 15000);
    return () => clearInterval(interval);
  }, []);

  // Filter vehicles to only show lines used by the selected route
  const filteredVehicles = useMemo(() => {
    if (!selectedRoute) return vehicles;
    const lineIds = new Set(
      selectedRoute.segments
        .filter((s) => s.mode === "transit" && s.transit_route_id)
        .map((s) => s.transit_route_id!)
    );
    if (lineIds.size === 0) return vehicles;
    return vehicles.filter((v) => v.route_id && lineIds.has(v.route_id));
  }, [vehicles, selectedRoute]);

  // Map theme preset
  const mapTheme = theme === "light" ? "day" as const : "dawn" as const;

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

      {/* TopBar — floating navigation bar */}
      <TopBar
        onSearch={handleSearch}
        loading={loading}
        origin={origin}
        destination={destination}
        originLabel={originLabel}
        onClearOrigin={handleClearOrigin}
        onClearDestination={handleClearDestination}
        onSwap={handleSwap}
        alertCount={alerts.length}
        onAlertsClick={() => setAlertsPanelOpen(true)}
        theme={theme}
        onThemeToggle={handleThemeToggle}
        viewMode={viewMode}
        onViewModeToggle={handleViewModeToggle}
      />

      {/* Main content area */}
      <div className="flex-1 relative">
        {viewMode === "dashboard" ? (
          /* Dashboard mode: full-width comparison */
          <div className="h-full pt-16">
            <DashboardView
              routes={routes}
              filteredRoutes={filteredRoutes}
              selectedRoute={selectedRoute}
              onSelectRoute={selectRoute}
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
            />
          </div>
        ) : (
          /* Map mode: full-screen map with overlays */
          <>
            <FluxMap
              selectedRoute={navigation.isNavigating && navigation.navigationRoute
                ? navigation.navigationRoute.route
                : selectedRoute}
              routes={navigation.isNavigating && navigation.navigationRoute
                ? [navigation.navigationRoute.route]
                : routes}
              origin={origin}
              destination={destination}
              vehicles={filteredVehicles}
              theme={mapTheme}
              showTraffic={showTraffic}
              transitLines={transitLines}
              transitLineVisibility={transitLineVisibility}
              showVehicles={showVehicles}
              showUnselectedRoutes={showUnselectedRoutes}
              isochroneData={isochroneData}
              userPosition={navigation.currentPosition}
              isNavigating={navigation.isNavigating}
              onMapClick={navigation.isNavigating ? undefined : handleMapClick}
              onGeolocate={handleGeolocate}
              onMarkerDrag={navigation.isNavigating ? undefined : handleMarkerDrag}
            />

            {/* Map Layers + Isochrone — stacked top-left */}
            <div className="absolute top-16 left-4 z-20 flex flex-col gap-2">
              <MapLayersControl
                transitLineVisibility={transitLineVisibility}
                onToggleTransitLine={handleToggleTransitLine}
                showVehicles={showVehicles}
                onToggleVehicles={() => setShowVehicles((v) => !v)}
                showTraffic={showTraffic}
                onToggleTraffic={() => setShowTraffic((v) => !v)}
                showUnselectedRoutes={showUnselectedRoutes}
                onToggleUnselectedRoutes={() => setShowUnselectedRoutes((v) => !v)}
                hasSelectedRoute={!!selectedRoute}
              />

              {origin && (
                <IsochronePanel
                  center={origin}
                  onIsochroneLoaded={setIsochroneData}
                  onClear={() => setIsochroneData(null)}
                  isochroneActive={!!isochroneData}
                />
              )}
            </div>

            {/* Route Panel — right slide-over / mobile bottom sheet */}
            <RoutePanel
              open={routePanelOpen}
              onClose={() => setRoutePanelOpen(false)}
              onOpen={() => setRoutePanelOpen(true)}
              routes={routes}
              filteredRoutes={filteredRoutes}
              selectedRoute={selectedRoute}
              onSelectRoute={selectRoute}
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
              onCustomize={handleCustomize}
              onStartNavigation={selectedRoute && origin && destination ? handleStartNavigation : undefined}
              isNavigating={navigation.isNavigating}
              originLabel={originLabel || undefined}
              destinationLabel={destinationLabel || undefined}
              error={error}
            />

            {/* Loading overlay */}
            {loading && <LoadingOverlay />}
          </>
        )}

        {/* Chat assistant — always available */}
        <ChatAssistant />
      </div>

      {/* Alerts Panel — slide-out */}
      <AlertsPanel
        open={alertsPanelOpen}
        onClose={() => setAlertsPanelOpen(false)}
        alerts={alerts}
      />

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
