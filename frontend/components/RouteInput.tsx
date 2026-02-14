"use client";

import { useState, useCallback } from "react";
import { MapPin, Navigation, Search, X } from "lucide-react";
import type { Coordinate } from "@/lib/types";
import { MAPBOX_TOKEN, TORONTO_BOUNDS } from "@/lib/constants";

interface RouteInputProps {
  onSearch: (origin: Coordinate, destination: Coordinate) => void;
  loading: boolean;
}

interface GeocoderResult {
  place_name: string;
  center: [number, number];
}

export default function RouteInput({ onSearch, loading }: RouteInputProps) {
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

  const geocode = useCallback(
    async (query: string): Promise<GeocoderResult[]> => {
      if (!query || query.length < 3 || !MAPBOX_TOKEN) return [];

      try {
        const bbox = `${TORONTO_BOUNDS[0][0]},${TORONTO_BOUNDS[0][1]},${TORONTO_BOUNDS[1][0]},${TORONTO_BOUNDS[1][1]}`;
        const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
          query
        )}.json?access_token=${MAPBOX_TOKEN}&bbox=${bbox}&limit=5&country=CA`;

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
        className={`w-full py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-all ${
          canSearch
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
