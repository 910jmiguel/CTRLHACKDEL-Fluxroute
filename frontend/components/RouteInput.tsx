"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { MapPin, Navigation, Search, X, ArrowUpDown, Train } from "lucide-react";
import type { Coordinate, SearchSuggestion } from "@/lib/types";
import { MAPBOX_TOKEN } from "@/lib/constants";
import { searchStops } from "@/lib/api";

interface RouteInputProps {
  onSearch: (origin: Coordinate, destination: Coordinate) => void;
  loading: boolean;
  origin?: Coordinate | null;
  destination?: Coordinate | null;
  originLabel?: string | null;
  onClearOrigin?: () => void;
  onClearDestination?: () => void;
  onSwap?: (newOrigin: Coordinate | null, newDest: Coordinate | null) => void;
}

interface GeocoderResult {
  place_name: string;
  center: [number, number];
}

async function reverseGeocode(coord: Coordinate): Promise<string> {
  if (!MAPBOX_TOKEN) return `${coord.lat.toFixed(4)}, ${coord.lng.toFixed(4)}`;
  try {
    const res = await fetch(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${coord.lng},${coord.lat}.json?access_token=${MAPBOX_TOKEN}&limit=1`
    );
    const data = await res.json();
    return data.features?.[0]?.place_name || `${coord.lat.toFixed(4)}, ${coord.lng.toFixed(4)}`;
  } catch {
    return `${coord.lat.toFixed(4)}, ${coord.lng.toFixed(4)}`;
  }
}

export default function RouteInput({ onSearch, loading, origin, destination, originLabel, onClearOrigin, onClearDestination, onSwap }: RouteInputProps) {
  const [originText, setOriginText] = useState("");
  const [destText, setDestText] = useState("");
  const [originCoord, setOriginCoord] = useState<Coordinate | null>(null);
  const [destCoord, setDestCoord] = useState<Coordinate | null>(null);
  const [originSuggestions, setOriginSuggestions] = useState<SearchSuggestion[]>([]);
  const [destSuggestions, setDestSuggestions] = useState<SearchSuggestion[]>([]);
  const [focusedField, setFocusedField] = useState<
    "origin" | "dest" | null
  >(null);

  const lastExternalOrigin = useRef<Coordinate | null | undefined>(undefined);
  const lastExternalDest = useRef<Coordinate | null | undefined>(undefined);
  const debounceOriginRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debounceDestRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchIdRef = useRef(0);

  // Sync external origin (from map click or geolocation) into text field
  useEffect(() => {
    if (origin === null && lastExternalOrigin.current !== null && lastExternalOrigin.current !== undefined) {
      lastExternalOrigin.current = null;
      setOriginCoord(null);
      setOriginText("");
      setOriginSuggestions([]);
      return;
    }
    if (
      origin &&
      (lastExternalOrigin.current?.lat !== origin.lat ||
        lastExternalOrigin.current?.lng !== origin.lng)
    ) {
      lastExternalOrigin.current = origin;
      setOriginCoord(origin);
      if (originLabel) {
        setOriginText(originLabel);
      } else {
        setOriginText(`${origin.lat.toFixed(4)}, ${origin.lng.toFixed(4)}`);
        reverseGeocode(origin).then((name) => setOriginText(name));
      }
    }
  }, [origin, originLabel]);

  // Sync external destination (from map click) into text field
  useEffect(() => {
    if (destination === null && lastExternalDest.current !== null && lastExternalDest.current !== undefined) {
      lastExternalDest.current = null;
      setDestCoord(null);
      setDestText("");
      setDestSuggestions([]);
      return;
    }
    if (
      destination &&
      (lastExternalDest.current?.lat !== destination.lat ||
        lastExternalDest.current?.lng !== destination.lng)
    ) {
      lastExternalDest.current = destination;
      setDestCoord(destination);
      setDestText(`${destination.lat.toFixed(4)}, ${destination.lng.toFixed(4)}`);
      reverseGeocode(destination).then((name) => setDestText(name));
    }
  }, [destination]);

  const geocode = useCallback(
    async (query: string): Promise<GeocoderResult[]> => {
      if (!query || query.length < 3 || !MAPBOX_TOKEN) return [];

      try {
        const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
          query
        )}.json?access_token=${MAPBOX_TOKEN}&limit=10&country=ca`;

        const res = await fetch(url);
        const data = await res.json();
        return data.features || [];
      } catch {
        return [];
      }
    },
    []
  );

  const federatedSearch = useCallback(
    async (query: string, setSuggestions: (s: SearchSuggestion[]) => void) => {
      if (query.length < 2) {
        setSuggestions([]);
        return;
      }

      const requestId = ++searchIdRef.current;

      const [stopsResult, geocodeResult] = await Promise.allSettled([
        query.length >= 2 ? searchStops(query) : Promise.resolve({ stops: [] }),
        query.length >= 3 ? geocode(query) : Promise.resolve([]),
      ]);

      // Guard against stale responses
      if (searchIdRef.current !== requestId) return;

      const stationSuggestions: SearchSuggestion[] =
        stopsResult.status === "fulfilled"
          ? stopsResult.value.stops.map((s) => ({ type: "station" as const, data: s }))
          : [];

      const addressSuggestions: SearchSuggestion[] =
        geocodeResult.status === "fulfilled"
          ? (geocodeResult.value as GeocoderResult[]).map((r) => ({ type: "address" as const, data: r }))
          : [];

      setSuggestions([...stationSuggestions, ...addressSuggestions]);
    },
    [geocode]
  );

  const handleOriginChange = (value: string) => {
    setOriginText(value);
    setOriginCoord(null);
    if (debounceOriginRef.current) clearTimeout(debounceOriginRef.current);
    if (value.length < 2) {
      setOriginSuggestions([]);
      return;
    }
    debounceOriginRef.current = setTimeout(() => {
      federatedSearch(value, setOriginSuggestions);
    }, 250);
  };

  const handleDestChange = (value: string) => {
    setDestText(value);
    setDestCoord(null);
    if (debounceDestRef.current) clearTimeout(debounceDestRef.current);
    if (value.length < 2) {
      setDestSuggestions([]);
      return;
    }
    debounceDestRef.current = setTimeout(() => {
      federatedSearch(value, setDestSuggestions);
    }, 250);
  };

  // Cleanup debounce timers on unmount
  useEffect(() => {
    return () => {
      if (debounceOriginRef.current) clearTimeout(debounceOriginRef.current);
      if (debounceDestRef.current) clearTimeout(debounceDestRef.current);
    };
  }, []);

  const selectOrigin = (suggestion: SearchSuggestion) => {
    if (suggestion.type === "station") {
      setOriginText(suggestion.data.stop_name);
      setOriginCoord({ lat: suggestion.data.lat, lng: suggestion.data.lng });
    } else {
      setOriginText(suggestion.data.place_name);
      setOriginCoord({ lat: suggestion.data.center[1], lng: suggestion.data.center[0] });
    }
    setOriginSuggestions([]);
    setFocusedField(null);
  };

  const selectDest = (suggestion: SearchSuggestion) => {
    if (suggestion.type === "station") {
      setDestText(suggestion.data.stop_name);
      setDestCoord({ lat: suggestion.data.lat, lng: suggestion.data.lng });
    } else {
      setDestText(suggestion.data.place_name);
      setDestCoord({ lat: suggestion.data.center[1], lng: suggestion.data.center[0] });
    }
    setDestSuggestions([]);
    setFocusedField(null);
  };

  const handleSubmit = () => {
    if (originCoord && destCoord) {
      onSearch(originCoord, destCoord);
    }
  };

  const handleSwap = () => {
    const prevOriginText = originText;
    const prevOriginCoord = originCoord;
    const prevDestText = destText;
    const prevDestCoord = destCoord;
    setOriginText(prevDestText);
    setOriginCoord(prevDestCoord);
    setDestText(prevOriginText);
    setDestCoord(prevOriginCoord);
    setOriginSuggestions([]);
    setDestSuggestions([]);
    lastExternalOrigin.current = prevDestCoord;
    lastExternalDest.current = prevOriginCoord;
    onSwap?.(prevDestCoord, prevOriginCoord);
  };

  const canSearch = originCoord && destCoord && !loading;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Navigation className="w-5 h-5 text-blue-400" />
        FluxRoute
      </h2>

      {/* Origin + Destination inputs with swap button on the side */}
      <div className="flex items-stretch gap-2">
        {/* Input fields column */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Origin input */}
          <div className="relative">
            <div className="flex items-center gap-2 bg-slate-800/60 rounded-lg border border-slate-700/50 px-3 py-2">
              <MapPin className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <input
                type="text"
                value={originText}
                onChange={(e) => handleOriginChange(e.target.value)}
                onFocus={() => setFocusedField("origin")}
                placeholder="Origin — e.g. Finch Station"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500 min-w-0"
              />
              {originText && (
                <button
                  onClick={() => {
                    setOriginText("");
                    setOriginCoord(null);
                    setOriginSuggestions([]);
                    lastExternalOrigin.current = undefined;
                    onClearOrigin?.();
                  }}
                >
                  <X className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300 transition-colors" />
                </button>
              )}
            </div>
            {focusedField === "origin" && originSuggestions.length > 0 && (
              <div className="absolute z-20 w-full mt-1 glass-card overflow-hidden">
                {originSuggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => selectOrigin(s)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-slate-700/50 flex items-center gap-2"
                  >
                    {s.type === "station" ? (
                      <Train className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                    ) : (
                      <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="truncate text-white font-medium">
                        {s.type === "station" ? s.data.stop_name : s.data.place_name}
                      </div>
                      {s.type === "station" && s.data.line && (
                        <div className="text-xs text-yellow-400/70 truncate">{s.data.line}</div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Destination input */}
          <div className="relative">
            <div className="flex items-center gap-2 bg-slate-800/60 rounded-lg border border-slate-700/50 px-3 py-2">
              <MapPin className="w-4 h-4 text-red-400 flex-shrink-0" />
              <input
                type="text"
                value={destText}
                onChange={(e) => handleDestChange(e.target.value)}
                onFocus={() => setFocusedField("dest")}
                placeholder="Destination — e.g. Union Station"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500 min-w-0"
              />
              {destText && (
                <button
                  onClick={() => {
                    setDestText("");
                    setDestCoord(null);
                    setDestSuggestions([]);
                    lastExternalDest.current = undefined;
                    onClearDestination?.();
                  }}
                >
                  <X className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300 transition-colors" />
                </button>
              )}
            </div>
            {focusedField === "dest" && destSuggestions.length > 0 && (
              <div className="absolute z-20 w-full mt-1 glass-card overflow-hidden">
                {destSuggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => selectDest(s)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-slate-700/50 flex items-center gap-2"
                  >
                    {s.type === "station" ? (
                      <Train className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                    ) : (
                      <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="truncate text-white font-medium">
                        {s.type === "station" ? s.data.stop_name : s.data.place_name}
                      </div>
                      {s.type === "station" && s.data.line && (
                        <div className="text-xs text-yellow-400/70 truncate">{s.data.line}</div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Swap button — right side, vertically centered */}
        <div className="flex items-center">
          <button
            onClick={handleSwap}
            className="p-2 rounded-full bg-slate-800/60 border border-slate-700/50 hover:bg-slate-700/80 hover:border-slate-600 transition-all text-slate-400 hover:text-white"
            title="Swap origin and destination"
          >
            <ArrowUpDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search button */}
      <button
        onClick={handleSubmit}
        disabled={!canSearch}
        className={`w-full py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-all ${canSearch
          ? "bg-blue-600 hover:bg-blue-500 text-white"
          : "bg-slate-700/50 text-slate-500 cursor-not-allowed"
          }`}
      >
        {loading ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Calculating...
          </>
        ) : (
          <>
            <Search className="w-4 h-4" />
            Find Routes
          </>
        )}
      </button>
    </div>
  );
}
