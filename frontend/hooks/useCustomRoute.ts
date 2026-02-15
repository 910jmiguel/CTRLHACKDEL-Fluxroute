"use client";

import { useState, useCallback } from "react";
import type {
  Coordinate,
  RouteOption,
  TransitRouteSuggestion,
  CustomSegmentV2,
  CustomSegmentRequestV2,
  CustomSegmentRequest,
  LineInfo,
} from "@/lib/types";
import { getTransitSuggestions, calculateCustomRouteV2, calculateCustomRoute, getLineStops } from "@/lib/api";

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
  { id: "1", name: "Line 1 Yonge-University", color: "#F0CC49" },
  { id: "2", name: "Line 2 Bloor-Danforth", color: "#549F4D" },
  { id: "4", name: "Line 4 Sheppard", color: "#9C246E" },
  { id: "5", name: "Line 5 Eglinton", color: "#DE7731" },
  { id: "6", name: "Line 6 Finch West", color: "#959595" },
];

let segIdCounter = 0;

export function useCustomRoute() {
  const [segments, setSegments] = useState<CustomSegmentV2[]>([]);
  const [suggestions, setSuggestions] = useState<TransitRouteSuggestion[]>([]);
  const [suggestionsSource, setSuggestionsSource] = useState<string>("");
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [calculatedRoute, setCalculatedRoute] = useState<RouteOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = useCallback(
    async (origin: Coordinate, destination: Coordinate) => {
      setSuggestionsLoading(true);
      try {
        const resp = await getTransitSuggestions(origin, destination);
        setSuggestions(resp.suggestions);
        setSuggestionsSource(resp.source);
      } catch (err) {
        console.error("Failed to fetch transit suggestions:", err);
        setSuggestions([]);
      } finally {
        setSuggestionsLoading(false);
      }
    },
    []
  );

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

  const updateSegmentMode = useCallback(
    (id: string, mode: "driving" | "walking" | "transit") => {
      setSegments((prev) =>
        prev.map((s) =>
          s.id === id ? { ...s, mode, selectedSuggestion: undefined } : s
        )
      );
      setCalculatedRoute(null);
    },
    []
  );

  const selectSuggestion = useCallback(
    (segId: string, suggestion: TransitRouteSuggestion) => {
      setSegments((prev) =>
        prev.map((s) =>
          s.id === segId ? { ...s, mode: "transit", selectedSuggestion: suggestion } : s
        )
      );
      setCalculatedRoute(null);
    },
    []
  );

  const clearSuggestion = useCallback((segId: string) => {
    setSegments((prev) =>
      prev.map((s) =>
        s.id === segId ? { ...s, selectedSuggestion: undefined } : s
      )
    );
    setCalculatedRoute(null);
  }, []);

  const selectTransferPair = useCallback(
    (segId: string, leg1: TransitRouteSuggestion, leg2: TransitRouteSuggestion) => {
      setSegments((prev) => {
        const idx = prev.findIndex((s) => s.id === segId);
        if (idx < 0) return prev;
        const updated = [...prev];
        // Replace current segment with leg 1
        updated[idx] = { ...updated[idx], mode: "transit", selectedSuggestion: leg1 };
        // Insert leg 2 as a new segment right after
        const newSeg: CustomSegmentV2 = {
          id: `seg_${++segIdCounter}`,
          mode: "transit",
          selectedSuggestion: leg2,
        };
        updated.splice(idx + 1, 0, newSeg);
        return updated;
      });
      setCalculatedRoute(null);
    },
    []
  );

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

  const calculate = useCallback(
    async (tripOrigin: Coordinate, tripDestination: Coordinate) => {
      if (segments.length === 0) {
        setError("Add at least one segment to calculate a route.");
        return null;
      }

      // Validate transit segments have a selected suggestion
      const invalidTransit = segments.find(
        (s) => s.mode === "transit" && !s.selectedSuggestion
      );
      if (invalidTransit) {
        setError("Select a transit route for each transit segment.");
        return null;
      }

      setLoading(true);
      setError(null);
      try {
        const apiSegments: CustomSegmentRequestV2[] = segments.map((s) => {
          if (s.mode === "transit" && s.selectedSuggestion) {
            const sg = s.selectedSuggestion;
            return {
              mode: "transit",
              suggestion_id: sg.suggestion_id,
              route_id: sg.route_id,
              board_coord: sg.board_coord,
              alight_coord: sg.alight_coord,
              board_stop_name: sg.board_stop_name,
              alight_stop_name: sg.alight_stop_name,
              board_stop_id: sg.board_stop_id,
              alight_stop_id: sg.alight_stop_id,
              transit_mode: sg.transit_mode,
              display_name: sg.display_name,
              color: sg.color,
            };
          }
          return { mode: s.mode };
        });

        const route = await calculateCustomRouteV2({
          segments: apiSegments,
          trip_origin: tripOrigin,
          trip_destination: tripDestination,
        });
        setCalculatedRoute(route);
        return route;
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to calculate custom route"
        );
        return null;
      } finally {
        setLoading(false);
      }
    },
    [segments]
  );

  const clearCalculatedRoute = useCallback(() => {
    setCalculatedRoute(null);
  }, []);

  const reset = useCallback(() => {
    setSegments([]);
    setCalculatedRoute(null);
    setError(null);
  }, []);

  return {
    segments,
    suggestions,
    suggestionsSource,
    suggestionsLoading,
    calculatedRoute,
    loading,
    error,
    addSegment,
    removeSegment,
    updateSegmentMode,
    selectSuggestion,
    selectTransferPair,
    clearSuggestion,
    clearCalculatedRoute,
    moveSegment,
    fetchSuggestions,
    calculate,
    reset,
  };
}
