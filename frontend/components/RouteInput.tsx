"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { MapPin, Navigation, Search, X } from "lucide-react";
import type { Coordinate } from "@/lib/types";
import { MAPBOX_TOKEN } from "@/lib/constants";

interface RouteInputProps {
  onSearch: (origin: Coordinate, destination: Coordinate) => void;
  loading: boolean;
  origin?: Coordinate | null;
  destination?: Coordinate | null;
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

export default function RouteInput({ onSearch, loading, origin, destination }: RouteInputProps) {
  const [originText, setOriginText] = useState("");
  const [destText, setDestText] = useState("");
  const [originCoord, setOriginCoord] = useState<Coordinate | null>(null);
  const [destCoord, setDestCoord] = useState<Coordinate | null>(null);
  const [originSuggestions, setOriginSuggestions] = useState<GeocoderResult[]>(
    []
  );
  const [destSuggestions, setDestSuggestions] = useState<GeocoderResult[]>([]);
  const [focusedField, setFocusedField] = useState<
    "origin" | "dest" | null
  >(null);

  const lastExternalOrigin = useRef<Coordinate | null | undefined>(undefined);
  const lastExternalDest = useRef<Coordinate | null | undefined>(undefined);

  // Sync external origin (from map click) into text field
  useEffect(() => {
    if (
      origin &&
      (lastExternalOrigin.current?.lat !== origin.lat ||
        lastExternalOrigin.current?.lng !== origin.lng)
    ) {
      lastExternalOrigin.current = origin;
      setOriginCoord(origin);
      setOriginText(`${origin.lat.toFixed(4)}, ${origin.lng.toFixed(4)}`);
      reverseGeocode(origin).then((name) => setOriginText(name));
    }
  }, [origin]);

  // Sync external destination (from map click) into text field
  useEffect(() => {
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
        )}.json?access_token=${MAPBOX_TOKEN}&limit=10`;

        const res = await fetch(url);
        const data = await res.json();
        return data.features || [];
      } catch {
        return [];
      }
    },
    []
  );

  const handleOriginChange = async (value: string) => {
    setOriginText(value);
    setOriginCoord(null);
    if (value.length >= 3) {
      const results = await geocode(value);
      setOriginSuggestions(results);
    } else {
      setOriginSuggestions([]);
    }
  };

  const handleDestChange = async (value: string) => {
    setDestText(value);
    setDestCoord(null);
    if (value.length >= 3) {
      const results = await geocode(value);
      setDestSuggestions(results);
    } else {
      setDestSuggestions([]);
    }
  };

  const selectOrigin = (result: GeocoderResult) => {
    setOriginText(result.place_name);
    setOriginCoord({ lat: result.center[1], lng: result.center[0] });
    setOriginSuggestions([]);
    setFocusedField(null);
  };

  const selectDest = (result: GeocoderResult) => {
    setDestText(result.place_name);
    setDestCoord({ lat: result.center[1], lng: result.center[0] });
    setDestSuggestions([]);
    setFocusedField(null);
  };

  const handleSubmit = () => {
    if (originCoord && destCoord) {
      onSearch(originCoord, destCoord);
    }
  };

  const canSearch = originCoord && destCoord && !loading;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Navigation className="w-5 h-5 text-blue-400" />
        FluxRoute
      </h2>

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
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500"
          />
          {originText && (
            <button
              onClick={() => {
                setOriginText("");
                setOriginCoord(null);
                setOriginSuggestions([]);
              }}
            >
              <X className="w-3.5 h-3.5 text-slate-500" />
            </button>
          )}
        </div>
        {focusedField === "origin" && originSuggestions.length > 0 && (
          <div className="absolute z-20 w-full mt-1 glass-card overflow-hidden">
            {originSuggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => selectOrigin(s)}
                className="w-full text-left px-3 py-2 text-sm hover:bg-slate-700/50 truncate text-slate-200"
              >
                {s.place_name}
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
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500"
          />
          {destText && (
            <button
              onClick={() => {
                setDestText("");
                setDestCoord(null);
                setDestSuggestions([]);
              }}
            >
              <X className="w-3.5 h-3.5 text-slate-500" />
            </button>
          )}
        </div>
        {focusedField === "dest" && destSuggestions.length > 0 && (
          <div className="absolute z-20 w-full mt-1 glass-card overflow-hidden">
            {destSuggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => selectDest(s)}
                className="w-full text-left px-3 py-2 text-sm hover:bg-slate-700/50 truncate text-slate-200"
              >
                {s.place_name}
              </button>
            ))}
          </div>
        )}
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
