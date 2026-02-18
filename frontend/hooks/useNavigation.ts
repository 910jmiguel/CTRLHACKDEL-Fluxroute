"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { API_URL } from "@/lib/constants";
import type {
  NavigationUpdate,
  NavigationPositionUpdate,
  NavigationRoute,
  NavigationInstruction,
  Coordinate,
  RouteOption,
} from "@/lib/types";
import { createNavigationSession, getNavigationRoute } from "@/lib/api";

interface UseNavigationOptions {
  onReroute?: (newRoute: NavigationUpdate["new_route"]) => void;
  onArrival?: () => void;
  onError?: (error: string) => void;
}

interface NavigationState {
  isNavigating: boolean;
  isConnected: boolean;
  sessionId: string | null;
  currentInstruction: string | null;
  voiceInstruction: string | null;
  stepIndex: number;
  totalSteps: number;
  remainingDistanceKm: number;
  remainingDurationMin: number;
  totalDistanceKm: number;
  eta: string | null;
  speedLimit: number | null;
  laneGuidance: NavigationUpdate["lane_guidance"];
  navigationRoute: NavigationRoute | null;
  nextInstruction: string | null;
  voiceMuted: boolean;
  currentPosition: { lat: number; lng: number; bearing: number | null } | null;
}

const INITIAL_STATE: NavigationState = {
  isNavigating: false,
  isConnected: false,
  sessionId: null,
  currentInstruction: null,
  voiceInstruction: null,
  stepIndex: 0,
  totalSteps: 0,
  remainingDistanceKm: 0,
  remainingDurationMin: 0,
  totalDistanceKm: 0,
  eta: null,
  speedLimit: null,
  laneGuidance: undefined,
  navigationRoute: null,
  nextInstruction: null,
  voiceMuted: false,
  currentPosition: null,
};

/**
 * Speak text using the Web Speech API.
 * Cancels any in-progress utterance before starting.
 */
function speak(text: string) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;
  utterance.lang = "en-US";
  window.speechSynthesis.speak(utterance);
}

function stopSpeaking() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

export function useNavigation(options: UseNavigationOptions = {}) {
  const [state, setState] = useState<NavigationState>(INITIAL_STATE);

  const wsRef = useRef<WebSocket | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const lastSpokenStepRef = useRef<number>(-1);
  const voiceMutedRef = useRef(false);

  // Store callbacks in refs to avoid stale closures
  const onRerouteRef = useRef(options.onReroute);
  const onArrivalRef = useRef(options.onArrival);
  const onErrorRef = useRef(options.onError);

  useEffect(() => {
    onRerouteRef.current = options.onReroute;
    onArrivalRef.current = options.onArrival;
    onErrorRef.current = options.onError;
  }, [options.onReroute, options.onArrival, options.onError]);

  const toggleVoice = useCallback(() => {
    setState((prev) => {
      const newMuted = !prev.voiceMuted;
      voiceMutedRef.current = newMuted;
      if (newMuted) stopSpeaking();
      return { ...prev, voiceMuted: newMuted };
    });
  }, []);

  const sendPosition = useCallback(
    (lat: number, lng: number, speed?: number, bearing?: number) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const msg: NavigationPositionUpdate = {
          type: "position_update",
          lat,
          lng,
          speed,
          bearing,
        };
        wsRef.current.send(JSON.stringify(msg));
      }
    },
    []
  );

  const stopNavigation = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_navigation" }));
    }
    wsRef.current?.close();
    wsRef.current = null;

    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }

    stopSpeaking();
    lastSpokenStepRef.current = -1;

    setState(INITIAL_STATE);
  }, []);

  const startNavigation = useCallback(
    async (origin: Coordinate, destination: Coordinate, waypoints?: Coordinate[], profile: string = "driving-traffic", existingRoute?: RouteOption) => {
      // Prevent double-start
      if (wsRef.current) {
        stopNavigation();
      }

      try {
        let navRoute: NavigationRoute;
        const isTransitMode = existingRoute && (existingRoute.mode === "transit" || existingRoute.mode === "hybrid");

        if (isTransitMode) {
          // For transit/hybrid: build navigation from existing route segments
          const navInstructions: NavigationInstruction[] = existingRoute.segments.map((seg) => ({
            instruction: seg.instructions || `${seg.mode} segment`,
            distance_km: seg.distance_km,
            duration_min: seg.duration_min,
            maneuver_type: seg.mode === "transit" ? "notification" : "depart",
            maneuver_modifier: "straight",
            voice_instruction: seg.instructions || `${seg.mode} segment`,
            banner_primary: seg.instructions || `${seg.mode} segment`,
            geometry: seg.geometry as GeoJSON.LineString | undefined,
          }));
          navRoute = {
            route: existingRoute,
            navigation_instructions: navInstructions,
            voice_locale: "en-US",
            alternatives: [],
          };
        } else {
          // For driving/walking/cycling: fetch from Mapbox
          navRoute = await getNavigationRoute({
            origin,
            destination,
            waypoints,
            profile,
            alternatives: true,
            voice_instructions: true,
            banner_instructions: true,
          });
        }

        // Create a server-side session for WebSocket tracking
        const session = await createNavigationSession({
          origin,
          destination,
          waypoints,
          profile: isTransitMode ? "walking" : profile,
          voice_instructions: true,
          banner_instructions: true,
        });

        // Connect WebSocket for real-time position tracking
        const wsUrl = API_URL.replace(/^http/, "ws");
        const ws = new WebSocket(`${wsUrl}/api/ws/navigation/${session.session_id}`);

        const instructions = navRoute.navigation_instructions || [];
        const totalSteps = instructions.length;

        ws.onopen = () => {
          const firstInstruction =
            instructions[0]?.banner_primary ||
            instructions[0]?.instruction ||
            "Start navigation";

          setState((prev) => ({
            ...prev,
            isConnected: true,
            isNavigating: true,
            sessionId: session.session_id,
            navigationRoute: navRoute,
            currentInstruction: firstInstruction,
            nextInstruction: instructions[1]?.banner_primary || instructions[1]?.instruction || null,
            remainingDistanceKm: navRoute.route.total_distance_km,
            remainingDurationMin: navRoute.route.total_duration_min,
            totalDistanceKm: navRoute.route.total_distance_km,
            totalSteps,
            voiceMuted: voiceMutedRef.current,
          }));

          // Speak the first instruction
          if (!voiceMutedRef.current) {
            const voiceText = instructions[0]?.voice_instruction || firstInstruction;
            speak(voiceText);
            lastSpokenStepRef.current = 0;
          }

          // Start browser GPS tracking (1Hz updates → WebSocket → backend)
          if ("geolocation" in navigator) {
            watchIdRef.current = navigator.geolocation.watchPosition(
              (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                const bearing = pos.coords.heading;
                sendPosition(
                  lat,
                  lng,
                  pos.coords.speed ?? undefined,
                  bearing ?? undefined
                );
                setState((prev) => ({
                  ...prev,
                  currentPosition: {
                    lat,
                    lng,
                    bearing: bearing !== null && !isNaN(bearing) ? bearing : null,
                  },
                }));
              },
              (err) => {
                console.warn("Geolocation error:", err.message);
                if (err.code === err.PERMISSION_DENIED) {
                  onErrorRef.current?.("Location permission denied. Enable location access to use navigation.");
                } else if (err.code === err.POSITION_UNAVAILABLE) {
                  onErrorRef.current?.("GPS position unavailable. Check your device location settings.");
                }
              },
              {
                enableHighAccuracy: true,
                maximumAge: 1000,
                timeout: 5000,
              }
            );
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === "navigation_update") {
              const stepIdx = data.step_index ?? 0;

              // Speak voice instruction when step changes
              if (
                !voiceMutedRef.current &&
                stepIdx !== lastSpokenStepRef.current &&
                data.voice_instruction
              ) {
                speak(data.voice_instruction);
                lastSpokenStepRef.current = stepIdx;
              }

              // Get next instruction preview
              const nextIdx = stepIdx + 1;
              const nextInstr =
                nextIdx < instructions.length
                  ? instructions[nextIdx].banner_primary || instructions[nextIdx].instruction
                  : null;

              setState((prev) => ({
                ...prev,
                currentInstruction: data.instruction ?? prev.currentInstruction,
                voiceInstruction: data.voice_instruction ?? null,
                stepIndex: stepIdx,
                remainingDistanceKm: data.remaining_distance_km ?? prev.remainingDistanceKm,
                remainingDurationMin: data.remaining_duration_min ?? prev.remainingDurationMin,
                eta: data.eta ?? prev.eta,
                speedLimit: data.speed_limit ?? null,
                laneGuidance: data.lane_guidance,
                nextInstruction: nextInstr ?? prev.nextInstruction,
              }));
            } else if (data.type === "reroute") {
              // Announce reroute
              if (!voiceMutedRef.current) {
                speak("Recalculating route.");
              }
              lastSpokenStepRef.current = -1;

              onRerouteRef.current?.(data.new_route);
              if (data.new_route) {
                setState((prev) => {
                  if (!prev.navigationRoute) return prev;
                  return {
                    ...prev,
                    navigationRoute: {
                      ...prev.navigationRoute,
                      route: {
                        ...prev.navigationRoute.route,
                        segments: [{
                          ...prev.navigationRoute.route.segments[0],
                          geometry: data.new_route.geometry,
                        }],
                        total_distance_km: data.new_route.distance_km,
                        total_duration_min: data.new_route.duration_min,
                      },
                    },
                    remainingDistanceKm: data.new_route.distance_km,
                    remainingDurationMin: data.new_route.duration_min,
                    totalDistanceKm: data.new_route.distance_km,
                  };
                });
              }
            } else if (data.type === "arrival" || data.destination_reached) {
              if (!voiceMutedRef.current) {
                speak("You have arrived at your destination.");
              }
              setState((prev) => ({
                ...prev,
                isNavigating: false,
                currentInstruction: "You have arrived at your destination",
                remainingDistanceKm: 0,
                remainingDurationMin: 0,
              }));
              onArrivalRef.current?.();
            }
          } catch (e) {
            console.warn("Failed to parse navigation message:", e);
          }
        };

        ws.onclose = () => {
          // Stop navigation UI when WebSocket disconnects
          if (watchIdRef.current !== null) {
            navigator.geolocation.clearWatch(watchIdRef.current);
            watchIdRef.current = null;
          }
          stopSpeaking();
          setState((prev) => ({
            ...prev,
            isConnected: false,
            isNavigating: false,
          }));
        };

        ws.onerror = () => {
          onErrorRef.current?.("WebSocket connection failed");
          setState((prev) => ({ ...prev, isConnected: false }));
        };

        wsRef.current = ws;
      } catch (err) {
        onErrorRef.current?.(
          err instanceof Error ? err.message : "Failed to start navigation"
        );
      }
    },
    [sendPosition, stopNavigation]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      stopSpeaking();
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, []);

  return {
    ...state,
    startNavigation,
    stopNavigation,
    sendPosition,
    toggleVoice,
  };
}
