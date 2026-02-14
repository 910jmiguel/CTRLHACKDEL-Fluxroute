"use client";

import { useState, useCallback } from "react";
import type { Coordinate, RouteOption, RouteResponse } from "@/lib/types";
import { getRoutes } from "@/lib/api";

export function useRoutes() {
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<RouteOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRoutes = useCallback(
    async (origin: Coordinate, destination: Coordinate) => {
      setLoading(true);
      setError(null);
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
  }, []);

  return {
    routes,
    selectedRoute,
    loading,
    error,
    fetchRoutes,
    selectRoute,
    clearRoutes,
  };
}
