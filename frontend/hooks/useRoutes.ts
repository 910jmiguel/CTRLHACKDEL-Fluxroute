"use client";

import { useState, useCallback, useMemo } from "react";
import type { Coordinate, RouteOption, RouteResponse, RouteMode } from "@/lib/types";
import { getRoutes } from "@/lib/api";

export type ModeFilter = "all" | "driving" | "transit" | "hybrid";

export function useRoutes() {
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<RouteOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<ModeFilter>("all");

  const filteredRoutes = useMemo(() => {
    if (activeFilter === "all") return routes;
    return routes.filter((r) => r.mode === activeFilter);
  }, [routes, activeFilter]);

  const fetchRoutes = useCallback(
    async (origin: Coordinate, destination: Coordinate) => {
      setLoading(true);
      setError(null);
      setActiveFilter("all");
      try {
        const response: RouteResponse = await getRoutes({ origin, destination });
        setRoutes(response.routes);
        if (response.routes.length > 0) {
          setSelectedRoute(response.routes[0]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch routes");
        setRoutes([]);
        setSelectedRoute(null);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const selectRoute = useCallback((route: RouteOption) => {
    setSelectedRoute(route);
  }, []);

  const clearRoutes = useCallback(() => {
    setRoutes([]);
    setSelectedRoute(null);
    setError(null);
    setActiveFilter("all");
  }, []);

  const addCustomRoute = useCallback((route: RouteOption) => {
    setRoutes((prev) => [route, ...prev]);
    setSelectedRoute(route);
  }, []);

  return {
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
  };
}
