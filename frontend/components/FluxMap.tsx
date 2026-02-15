"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import type { RouteOption, VehiclePosition, TransitLinesData, IsochroneResponse } from "@/lib/types";
import { MAPBOX_TOKEN, TORONTO_CENTER, TORONTO_ZOOM, MAP_STYLE, CONGESTION_COLORS } from "@/lib/constants";
import type { MapTheme } from "@/hooks/useTimeBasedTheme";
import type { TransitLineVisibility } from "./MapLayersControl";
import {
  clearRoutes,
  drawMultimodalRoute,
  addMarkers,
  fitToRoute,
  updateVehicles,
  drawTransitOverlay,
  setTransitOverlayDimmed,
  drawIsochrone,
  clearIsochrone,
} from "@/lib/mapUtils";

interface FluxMapProps {
  selectedRoute: RouteOption | null;
  routes: RouteOption[];
  origin: { lat: number; lng: number } | null;
  destination: { lat: number; lng: number } | null;
  vehicles: VehiclePosition[];
  theme: MapTheme;
  showTraffic: boolean;
  transitLines: TransitLinesData | null;
  transitLineVisibility?: TransitLineVisibility;
  showVehicles?: boolean;
  showUnselectedRoutes?: boolean;
  isochroneData?: IsochroneResponse | null;
  userPosition?: { lat: number; lng: number; bearing: number | null } | null;
  isNavigating?: boolean;
  onMapClick?: (coord: { lat: number; lng: number }) => void;
  onGeolocate?: (coord: { lat: number; lng: number }) => void;
  onMarkerDrag?: (type: "origin" | "destination", coord: { lat: number; lng: number }) => void;
}

export default function FluxMap({
  selectedRoute,
  routes,
  origin,
  destination,
  vehicles,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  theme,
  showTraffic,
  transitLines,
  transitLineVisibility,
  showVehicles = true,
  showUnselectedRoutes = true,
  isochroneData,
  userPosition,
  isNavigating,
  onMapClick,
  onGeolocate,
  onMarkerDrag,
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

    const geolocate = new mapboxgl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: false,
      showUserHeading: false,
    });

    geolocate.on("geolocate", (e: GeolocationPosition) => {
      const coord = { lat: e.coords.latitude, lng: e.coords.longitude };
      onGeolocate?.(coord);
    });

    map.current.addControl(geolocate, "top-right");

    map.current.on("load", () => {
      setMapLoaded(true);
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Resize map when container size changes (e.g. sidebar collapse/expand)
  useEffect(() => {
    if (!mapContainer.current || !map.current || !mapLoaded) return;

    const resize = () => map.current?.resize();
    const ro = new ResizeObserver(resize);
    ro.observe(mapContainer.current);
    return () => ro.disconnect();
  }, [mapLoaded]);

  // Apply light preset based on theme prop
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    try {
      const preset = theme === "day" ? "day" : theme === "dusk" ? "dusk" : theme === "night" ? "night" : "dawn";
      map.current.setConfigProperty("basemap", "lightPreset", preset);
    } catch {
      // setConfigProperty not supported on classic styles (dark-v11, etc.)
    }
  }, [mapLoaded, theme]);

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

  // Draw transit overlay (always-visible subway/rail/LRT lines + stations)
  useEffect(() => {
    if (!map.current || !mapLoaded || !transitLines) return;

    const m = map.current;
    drawTransitOverlay(m, transitLines);

    // Hover tooltip for transit lines and stations
    const popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "transit-overlay-tooltip",
    });

    const onLineEnter = (e: mapboxgl.MapMouseEvent) => {
      m.getCanvas().style.cursor = "pointer";
      if (e.features && e.features[0]) {
        const props = e.features[0].properties;
        if (props) {
          const name = props.shortName || props.longName || "Transit Line";
          const agency = props.agencyName || "";
          const mode = props.mode || "";
          popup
            .setLngLat(e.lngLat)
            .setHTML(
              `<div class="font-bold">${name}</div>` +
              `<div class="text-xs text-slate-300">${agency}${mode ? ` \u2022 ${mode}` : ""}</div>`
            )
            .addTo(m);
        }
      }
    };

    const onStationEnter = (e: mapboxgl.MapMouseEvent) => {
      m.getCanvas().style.cursor = "pointer";
      if (e.features && e.features[0]) {
        const props = e.features[0].properties;
        if (props) {
          const name = props.name || "Station";
          const route = props.routeName || "";
          const agency = props.agencyName || "";
          popup
            .setLngLat(e.lngLat)
            .setHTML(
              `<div class="font-bold">${name}</div>` +
              `<div class="text-xs text-slate-300">${route}${agency ? ` \u2022 ${agency}` : ""}</div>`
            )
            .addTo(m);
        }
      }
    };

    const onLeave = () => {
      m.getCanvas().style.cursor = "";
      popup.remove();
    };

    m.on("mouseenter", "transit-lines-layer", onLineEnter);
    m.on("mouseleave", "transit-lines-layer", onLeave);
    m.on("mouseenter", "transit-stations-layer", onStationEnter);
    m.on("mouseleave", "transit-stations-layer", onLeave);

    return () => {
      popup.remove();
      m.off("mouseenter", "transit-lines-layer", onLineEnter);
      m.off("mouseleave", "transit-lines-layer", onLeave);
      m.off("mouseenter", "transit-stations-layer", onStationEnter);
      m.off("mouseleave", "transit-stations-layer", onLeave);
    };
  }, [transitLines, mapLoaded]);

  // Apply transit line visibility filters
  useEffect(() => {
    if (!map.current || !mapLoaded || !transitLines || !transitLineVisibility) return;
    const m = map.current;

    // Build filter for lines
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const lineConditions: any[] = [];
    if (transitLineVisibility.line1) lineConditions.push(["all", ["==", ["get", "mode"], "SUBWAY"], ["==", ["get", "shortName"], "1"]]);
    if (transitLineVisibility.line2) lineConditions.push(["all", ["==", ["get", "mode"], "SUBWAY"], ["==", ["get", "shortName"], "2"]]);
    if (transitLineVisibility.line4) lineConditions.push(["all", ["==", ["get", "mode"], "SUBWAY"], ["==", ["get", "shortName"], "4"]]);
    if (transitLineVisibility.line5) lineConditions.push(["all", ["in", ["get", "mode"], ["literal", ["SUBWAY", "LRT"]]], ["==", ["get", "shortName"], "5"]]);
    if (transitLineVisibility.line6) lineConditions.push(["all", ["in", ["get", "mode"], ["literal", ["SUBWAY", "LRT"]]], ["==", ["get", "shortName"], "6"]]);
    if (transitLineVisibility.streetcars) lineConditions.push(["==", ["get", "mode"], "TRAM"]);

    // Also allow RAIL mode through (GO trains etc.) if any line is visible
    const anyVisible = Object.values(transitLineVisibility).some(Boolean);
    if (anyVisible) lineConditions.push(["==", ["get", "mode"], "RAIL"]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const filter: any = lineConditions.length > 0
      ? ["any", ...lineConditions]
      : ["==", "mode", "__none__"]; // Hide everything

    try {
      for (const layerId of ["transit-lines-casing", "transit-lines-layer"]) {
        if (m.getLayer(layerId)) m.setFilter(layerId, filter);
      }
      for (const layerId of ["transit-stations-layer", "transit-station-labels"]) {
        if (m.getLayer(layerId)) m.setFilter(layerId, filter);
      }
    } catch (err) {
      console.warn("Failed to apply transit filters:", err);
    }
  }, [transitLineVisibility, transitLines, mapLoaded]);

  // Dim transit overlay when a route is selected (focus mode)
  useEffect(() => {
    if (!map.current || !mapLoaded || !transitLines) return;
    setTransitOverlayDimmed(map.current, !!selectedRoute);
  }, [selectedRoute, mapLoaded, transitLines]);

  // Toggle vehicle layer visibility
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;
    try {
      if (m.getLayer("vehicles-layer")) {
        m.setLayoutProperty("vehicles-layer", "visibility", showVehicles ? "visible" : "none");
      }
    } catch {
      // Layer may not exist yet
    }
  }, [showVehicles, mapLoaded, vehicles]);

  // Draw routes when they change
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    clearRoutes(map.current);

    // Draw non-selected routes first (heavily faded, or hidden if toggle is off)
    if (showUnselectedRoutes || !selectedRoute) {
      routes.forEach((route) => {
        if (route.id !== selectedRoute?.id) {
          drawMultimodalRoute(map.current!, route, !selectedRoute);
        }
      });
    }

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

    // Track all registered listeners for cleanup
    const registeredListeners: Array<{ layerId: string; event: string; handler: (e: mapboxgl.MapMouseEvent) => void }> = [];

    const style = m.getStyle();
    if (style?.layers) {
      style.layers.forEach((layer) => {
        if (layer.id.startsWith("route-layer-congestion-")) {
          const onEnter = (e: mapboxgl.MapMouseEvent) => {
            m.getCanvas().style.cursor = "pointer";
            if (e.features && e.features[0]) {
              const congestion = e.features[0].properties?.congestion as string;
              const desc = congestionDescriptions[congestion] || congestion;
              popup.setLngLat(e.lngLat).setHTML(desc).addTo(m!);
            }
          };
          const onLeave = () => {
            m.getCanvas().style.cursor = "";
            popup.remove();
          };
          m.on("mouseenter", layer.id, onEnter);
          m.on("mouseleave", layer.id, onLeave);
          registeredListeners.push({ layerId: layer.id, event: "mouseenter", handler: onEnter });
          registeredListeners.push({ layerId: layer.id, event: "mouseleave", handler: onLeave });
        }
      });
    }

    // Road Closure Tooltips
    ["road-closure-line", "road-closure-symbol"].forEach((layerId) => {
      const onEnter = (e: mapboxgl.MapMouseEvent) => {
        m.getCanvas().style.cursor = "pointer";
        if (e.features && e.features[0]) {
          const props = e.features[0].properties;
          if (props) {
            const road = props.road || "Road Closure";
            const desc = props.description || props.reason || "No details available";
            const endDate = props.planned_end_date ? `<br><span class="text-[9px] text-slate-400">Ends: ${new Date(props.planned_end_date).toLocaleDateString()}</span>` : "";

            popup.setLngLat(e.lngLat).setHTML(
              `<div class="font-bold">${road}</div><div class="text-xs">${desc}</div>${endDate}`
            ).addTo(m!);
          }
        }
      };
      const onLeave = () => {
        m.getCanvas().style.cursor = "";
        popup.remove();
      };
      m.on("mouseenter", layerId, onEnter);
      m.on("mouseleave", layerId, onLeave);
      registeredListeners.push({ layerId, event: "mouseenter", handler: onEnter });
      registeredListeners.push({ layerId, event: "mouseleave", handler: onLeave });
    });

    return () => {
      popup.remove();
      // Clean up all registered listeners to prevent memory leaks
      for (const { layerId, event, handler } of registeredListeners) {
        m.off(event, layerId, handler);
      }
    };
  }, [routes, selectedRoute, showUnselectedRoutes, mapLoaded]);

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
      markers.current,
      onMarkerDrag
    );
  }, [origin, destination, mapLoaded, onMarkerDrag]);

  // Update vehicle positions
  useEffect(() => {
    if (!map.current || !mapLoaded || vehicles.length === 0) return;
    updateVehicles(map.current, vehicles);
  }, [vehicles, mapLoaded]);

  // Draw/clear isochrone polygons
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    if (isochroneData) {
      drawIsochrone(map.current, isochroneData);
    } else {
      clearIsochrone(map.current);
    }
  }, [isochroneData, mapLoaded]);

  const [showRecenter, setShowRecenter] = useState(false);

  // Track whether we were previously navigating (to detect stop → cleanup)
  const wasNavigatingRef = useRef(false);
  // Track whether user has manually interacted with map during navigation
  const userInteractedRef = useRef(false);
  // Store last known bearing for smooth rotation
  const lastBearingRef = useRef(0);
  // Pulse animation frame ID
  const pulseAnimRef = useRef<number | null>(null);

  // Set up / tear down user location layers when navigation starts/stops
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    if (isNavigating) {
      wasNavigatingRef.current = true;
      userInteractedRef.current = false;

      // Listen for user interaction to pause auto-follow
      const onInteraction = () => {
        userInteractedRef.current = true;
        setShowRecenter(true);
      };
      m.on("dragstart", onInteraction);

      // Create source + layers if they don't exist
      if (!m.getSource("user-location")) {
        m.addSource("user-location", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });

        // Pulsing outer ring (animated via paint transitions)
        m.addLayer({
          id: "user-location-pulse",
          type: "circle",
          source: "user-location",
          paint: {
            "circle-radius": 12,
            "circle-color": "#4285F4",
            "circle-opacity": 0.3,
            "circle-stroke-width": 0,
          },
        });

        // Solid blue dot with white border
        m.addLayer({
          id: "user-location-dot",
          type: "circle",
          source: "user-location",
          paint: {
            "circle-radius": 7,
            "circle-color": "#4285F4",
            "circle-opacity": 1,
            "circle-stroke-width": 2.5,
            "circle-stroke-color": "#ffffff",
          },
        });

        // Heading cone (directional indicator)
        m.addLayer({
          id: "user-location-heading",
          type: "circle",
          source: "user-location",
          paint: {
            "circle-radius": 28,
            "circle-color": "#4285F4",
            "circle-opacity": 0.08,
            "circle-stroke-width": 0,
          },
        });
      }

      // Start pulse animation using setInterval (cleaner than mixed RAF/setTimeout)
      let growing = true;
      const pulseInterval = window.setInterval(() => {
        if (!m.getLayer("user-location-pulse")) {
          clearInterval(pulseInterval);
          return;
        }
        m.setPaintProperty("user-location-pulse", "circle-radius", growing ? 20 : 12);
        m.setPaintProperty("user-location-pulse", "circle-opacity", growing ? 0.1 : 0.3);
        growing = !growing;
      }, 1200);
      pulseAnimRef.current = pulseInterval;

      return () => {
        m.off("dragstart", onInteraction);
        if (pulseAnimRef.current !== null) {
          clearInterval(pulseAnimRef.current);
          pulseAnimRef.current = null;
        }
      };
    } else if (wasNavigatingRef.current) {
      // Navigation just stopped — clean up
      wasNavigatingRef.current = false;
      userInteractedRef.current = false;
      lastBearingRef.current = 0;
      setShowRecenter(false);

      if (m.getLayer("user-location-heading")) m.removeLayer("user-location-heading");
      if (m.getLayer("user-location-dot")) m.removeLayer("user-location-dot");
      if (m.getLayer("user-location-pulse")) m.removeLayer("user-location-pulse");
      if (m.getSource("user-location")) m.removeSource("user-location");

      if (pulseAnimRef.current !== null) {
        clearInterval(pulseAnimRef.current);
        pulseAnimRef.current = null;
      }

      // Smoothly reset to flat top-down view
      m.easeTo({ pitch: 0, bearing: 0, duration: 800 });
    }
  }, [isNavigating, mapLoaded]);

  // Update user position on the map (separate effect to avoid re-creating layers)
  useEffect(() => {
    if (!map.current || !mapLoaded || !isNavigating || !userPosition) return;
    const m = map.current;

    const source = m.getSource("user-location") as mapboxgl.GeoJSONSource | undefined;
    if (!source) return;

    source.setData({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [userPosition.lng, userPosition.lat],
          },
          properties: {},
        },
      ],
    });

    // Update bearing smoothly — keep last bearing if GPS doesn't provide one
    if (userPosition.bearing !== null) {
      lastBearingRef.current = userPosition.bearing;
    }

    // Only auto-follow if user hasn't panned away
    if (!userInteractedRef.current) {
      m.easeTo({
        center: [userPosition.lng, userPosition.lat],
        bearing: lastBearingRef.current,
        pitch: 55,
        zoom: Math.max(m.getZoom(), 15.5),
        duration: 1000,
        easing: (t) => t * (2 - t), // ease-out quadratic
      });
    }
  }, [userPosition, isNavigating, mapLoaded]);

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
    <div ref={mapContainer} className="w-full h-full" data-theme={theme}>
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

      {/* Re-center button during navigation */}
      {isNavigating && showRecenter && (
        <button
          onClick={() => {
            userInteractedRef.current = false;
            setShowRecenter(false);
          }}
          className="absolute top-20 right-3 z-20 bg-blue-500 hover:bg-blue-600 text-white rounded-full p-3 shadow-lg transition-all duration-200 animate-pulse"
          title="Re-center on your location"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
          </svg>
        </button>
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
