"use client";

import { useState, useCallback } from "react";
import type { Coordinate, RouteOption, CustomSegmentRequest, LineInfo } from "@/lib/types";
import { calculateCustomRoute, getLineStops } from "@/lib/api";

export interface CustomSegment {
  id: string;
  mode: "driving" | "walking" | "transit";
  line_id?: string;
  start_station_id?: string;
  end_station_id?: string;
  origin?: Coordinate;
  destination?: Coordinate;
  lineInfo?: LineInfo;
}

export const TTC_LINES = [
  { id: "1", name: "Line 1 Yonge-University", color: "#FFCC00" },
  { id: "2", name: "Line 2 Bloor-Danforth", color: "#00A651" },
  { id: "4", name: "Line 4 Sheppard", color: "#A8518A" },
  { id: "5", name: "Line 5 Eglinton", color: "#FF6600" },
  { id: "6", name: "Line 6 Finch West", color: "#8B4513" },
];

let segIdCounter = 0;

export function useCustomRoute() {
  const [segments, setSegments] = useState<CustomSegment[]>([]);
  const [calculatedRoute, setCalculatedRoute] = useState<RouteOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lineCache, setLineCache] = useState<Record<string, LineInfo>>({});

  const addSegment = useCallback(() => {
    setSegments((prev) => [
      ...prev,
      { id: `seg_${++segIdCounter}`, mode: "transit" },
    ]);
    setCalculatedRoute(null);
  }, []);

  const removeSegment = useCallback((id: string) => {
    setSegments((prev) => prev.filter((s) => s.id !== id));
    setCalculatedRoute(null);
  }, []);

  const updateSegment = useCallback((id: string, updates: Partial<CustomSegment>) => {
    setSegments((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...updates } : s))
    );
    setCalculatedRoute(null);
  }, []);

  const moveSegment = useCallback((id: string, direction: "up" | "down") => {
    setSegments((prev) => {
      const idx = prev.findIndex((s) => s.id === id);
      if (idx < 0) return prev;
      const next = [...prev];
      const swapIdx = direction === "up" ? idx - 1 : idx + 1;
      if (swapIdx < 0 || swapIdx >= next.length) return prev;
      [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
      return next;
    });
    setCalculatedRoute(null);
  }, []);

  const fetchLineStops = useCallback(async (lineId: string): Promise<LineInfo | null> => {
    if (lineCache[lineId]) return lineCache[lineId];
    try {
      const info = await getLineStops(lineId);
      setLineCache((prev) => ({ ...prev, [lineId]: info }));
      return info;
    } catch {
      return null;
    }
  }, [lineCache]);

  const calculate = useCallback(
    async (tripOrigin: Coordinate, tripDestination: Coordinate) => {
      setLoading(true);
      setError(null);
      try {
        const apiSegments: CustomSegmentRequest[] = segments.map((s) => ({
          mode: s.mode,
          line_id: s.line_id,
          start_station_id: s.start_station_id,
          end_station_id: s.end_station_id,
          origin: s.origin,
          destination: s.destination,
        }));

        const route = await calculateCustomRoute({
          segments: apiSegments,
          trip_origin: tripOrigin,
          trip_destination: tripDestination,
        });
        setCalculatedRoute(route);
        return route;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to calculate custom route");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [segments]
  );

  const reset = useCallback(() => {
    setSegments([]);
    setCalculatedRoute(null);
    setError(null);
  }, []);

  return {
    segments,
    calculatedRoute,
    loading,
    error,
    addSegment,
    removeSegment,
    updateSegment,
    moveSegment,
    fetchLineStops,
    calculate,
    reset,
  };
}
