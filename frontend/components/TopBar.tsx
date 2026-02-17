"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { MapPin, Search, X, ArrowLeftRight, Train, LayoutDashboard, Navigation } from "lucide-react";
import type { Coordinate, SearchSuggestion, ThemeMode, ViewMode } from "@/lib/types";
import { MAPBOX_TOKEN } from "@/lib/constants";
import { searchStops } from "@/lib/api";
import ThemeToggle from "./ThemeToggle";
import AlertsBell from "./AlertsBell";
import { useIsMobile } from "@/hooks/useMediaQuery";

interface TopBarProps {
  onSearch: (origin: Coordinate, destination: Coordinate) => void;
  loading: boolean;
  origin?: Coordinate | null;
  destination?: Coordinate | null;
  originLabel?: string | null;
  onClearOrigin?: () => void;
  onClearDestination?: () => void;
  onSwap?: (newOrigin: Coordinate | null, newDest: Coordinate | null) => void;
  alertCount: number;
  onAlertsClick: () => void;
  theme: ThemeMode;
  onThemeToggle: () => void;
  viewMode: ViewMode;
  onViewModeToggle: () => void;
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

export default function TopBar({
  onSearch,
  loading,
  origin,
  destination,
  originLabel,
  onClearOrigin,
  onClearDestination,
  onSwap,
  alertCount,
  onAlertsClick,
  theme,
  onThemeToggle,
  viewMode,
  onViewModeToggle,
}: TopBarProps) {
  const isMobile = useIsMobile();
  const [mobileExpanded, setMobileExpanded] = useState(false);

  const [originText, setOriginText] = useState("");
  const [destText, setDestText] = useState("");
  const [originCoord, setOriginCoord] = useState<Coordinate | null>(null);
  const [destCoord, setDestCoord] = useState<Coordinate | null>(null);
  const [originSuggestions, setOriginSuggestions] = useState<SearchSuggestion[]>([]);
  const [destSuggestions, setDestSuggestions] = useState<SearchSuggestion[]>([]);
  const [focusedField, setFocusedField] = useState<"origin" | "dest" | null>(null);

  const lastExternalOrigin = useRef<Coordinate | null | undefined>(undefined);
  const lastExternalDest = useRef<Coordinate | null | undefined>(undefined);
  const debounceOriginRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debounceDestRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchIdRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync external origin
  useEffect(() => {
    if (origin === null && lastExternalOrigin.current !== null && lastExternalOrigin.current !== undefined) {
      lastExternalOrigin.current = null;
      setOriginCoord(null);
      setOriginText("");
      setOriginSuggestions([]);
      return;
    }
    if (origin && (lastExternalOrigin.current?.lat !== origin.lat || lastExternalOrigin.current?.lng !== origin.lng)) {
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

  // Sync external destination
  useEffect(() => {
    if (destination === null && lastExternalDest.current !== null && lastExternalDest.current !== undefined) {
      lastExternalDest.current = null;
      setDestCoord(null);
      setDestText("");
      setDestSuggestions([]);
      return;
    }
    if (destination && (lastExternalDest.current?.lat !== destination.lat || lastExternalDest.current?.lng !== destination.lng)) {
      lastExternalDest.current = destination;
      setDestCoord(destination);
      setDestText(`${destination.lat.toFixed(4)}, ${destination.lng.toFixed(4)}`);
      reverseGeocode(destination).then((name) => setDestText(name));
    }
  }, [destination]);

  const geocode = useCallback(async (query: string): Promise<GeocoderResult[]> => {
    if (!query || query.length < 3 || !MAPBOX_TOKEN) return [];
    try {
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${MAPBOX_TOKEN}&limit=10&country=ca`;
      const res = await fetch(url);
      const data = await res.json();
      return data.features || [];
    } catch {
      return [];
    }
  }, []);

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
    if (value.length < 2) { setOriginSuggestions([]); return; }
    debounceOriginRef.current = setTimeout(() => federatedSearch(value, setOriginSuggestions), 250);
  };

  const handleDestChange = (value: string) => {
    setDestText(value);
    setDestCoord(null);
    if (debounceDestRef.current) clearTimeout(debounceDestRef.current);
    if (value.length < 2) { setDestSuggestions([]); return; }
    debounceDestRef.current = setTimeout(() => federatedSearch(value, setDestSuggestions), 250);
  };

  useEffect(() => {
    return () => {
      if (debounceOriginRef.current) clearTimeout(debounceOriginRef.current);
      if (debounceDestRef.current) clearTimeout(debounceDestRef.current);
    };
  }, []);

  const selectSuggestion = (field: "origin" | "dest", suggestion: SearchSuggestion) => {
    const coord = suggestion.type === "station"
      ? { lat: suggestion.data.lat, lng: suggestion.data.lng }
      : { lat: suggestion.data.center[1], lng: suggestion.data.center[0] };
    const text = suggestion.type === "station" ? suggestion.data.stop_name : suggestion.data.place_name;

    if (field === "origin") {
      setOriginText(text);
      setOriginCoord(coord);
      setOriginSuggestions([]);
    } else {
      setDestText(text);
      setDestCoord(coord);
      setDestSuggestions([]);
    }
    setFocusedField(null);
  };

  const handleSubmit = () => {
    if (originCoord && destCoord) {
      onSearch(originCoord, destCoord);
      setMobileExpanded(false);
    }
  };

  const handleSwap = () => {
    const prevOT = originText, prevOC = originCoord;
    const prevDT = destText, prevDC = destCoord;
    setOriginText(prevDT);
    setOriginCoord(prevDC);
    setDestText(prevOT);
    setDestCoord(prevOC);
    setOriginSuggestions([]);
    setDestSuggestions([]);
    lastExternalOrigin.current = prevDC;
    lastExternalDest.current = prevOC;
    onSwap?.(prevDC, prevOC);
  };

  // Close suggestions on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setFocusedField(null);
        setOriginSuggestions([]);
        setDestSuggestions([]);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const canSearch = originCoord && destCoord && !loading;

  const renderSuggestionList = (
    suggestions: SearchSuggestion[],
    field: "origin" | "dest"
  ) => {
    if (suggestions.length === 0) return null;
    return (
      <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-64 overflow-y-auto rounded-lg panel-glass shadow-xl border border-[var(--glass-border)]">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => selectSuggestion(field, s)}
            className="w-full text-left px-3 py-2.5 text-sm hover:bg-[var(--surface-hover)] flex items-center gap-2 transition-colors"
          >
            {s.type === "station" ? (
              <Train className="w-4 h-4 text-yellow-500 flex-shrink-0" />
            ) : (
              <MapPin className="w-4 h-4 text-[var(--text-muted)] flex-shrink-0" />
            )}
            <div className="min-w-0 flex-1">
              <div className="truncate text-[var(--text-primary)] font-medium">
                {s.type === "station" ? s.data.stop_name : s.data.place_name}
              </div>
              {s.type === "station" && s.data.line && (
                <div className="text-xs text-yellow-500/70 truncate">{s.data.line}</div>
              )}
            </div>
          </button>
        ))}
      </div>
    );
  };

  // Mobile: compact search bar
  if (isMobile && !mobileExpanded) {
    return (
      <div className="fixed top-3 left-3 right-3 z-30 flex items-center gap-2">
        <button
          onClick={() => setMobileExpanded(true)}
          className="flex-1 flex items-center gap-2 px-4 py-3 rounded-xl topbar-glass shadow-lg"
        >
          <Search className="w-4 h-4 text-[var(--text-muted)]" />
          <span className="text-sm text-[var(--text-muted)] truncate">
            {originText && destText
              ? `${originText.split(",")[0]} → ${destText.split(",")[0]}`
              : "Where to?"}
          </span>
        </button>
        <div className="flex items-center gap-1 topbar-glass rounded-xl px-1 shadow-lg">
          <AlertsBell count={alertCount} onClick={onAlertsClick} />
          <ThemeToggle theme={theme} onToggle={onThemeToggle} />
        </div>
      </div>
    );
  }

  // Mobile expanded or Desktop: full input bar
  return (
    <div
      ref={containerRef}
      className={`fixed z-30 ${
        isMobile
          ? "inset-0 bg-[var(--background)]/95 backdrop-blur-md flex flex-col p-4"
          : "top-3 left-1/2 -translate-x-1/2 w-full max-w-[960px] px-3"
      }`}
    >
      {/* Mobile: close expanded view */}
      {isMobile && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-[var(--accent)]" />
            <span className="font-heading font-bold text-lg text-[var(--text-primary)]">FluxRoute</span>
          </div>
          <button
            onClick={() => setMobileExpanded(false)}
            className="p-2 rounded-lg hover:bg-[var(--surface-hover)] text-[var(--text-secondary)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      <div className={`topbar-glass rounded-xl shadow-lg ${isMobile ? "" : "flex items-center gap-2 px-3 py-2"}`}>
        {/* Desktop: Logo */}
        {!isMobile && (
          <div className="flex items-center gap-1.5 pr-3 border-r border-[var(--border)] mr-1 flex-shrink-0">
            <Navigation className="w-4 h-4 text-[var(--accent)]" />
            <span className="font-serif font-bold text-sm text-[var(--text-primary)]">FluxRoute</span>
          </div>
        )}

        {/* Inputs */}
        <div className={`flex-1 ${isMobile ? "space-y-3 p-3" : "flex items-center gap-2"}`}>
          {/* Origin */}
          <div className={`relative ${isMobile ? "" : "flex-1"}`}>
            <div className="flex items-center gap-2 bg-[var(--input-bg)] rounded-lg border border-[var(--border)] px-3 py-2">
              <MapPin className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              <input
                type="text"
                value={originText}
                onChange={(e) => handleOriginChange(e.target.value)}
                onFocus={() => setFocusedField("origin")}
                placeholder="Origin"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--text-muted)] text-[var(--text-primary)] min-w-0"
                aria-label="Origin location"
              />
              {originText && (
                <button onClick={() => { setOriginText(""); setOriginCoord(null); setOriginSuggestions([]); lastExternalOrigin.current = undefined; onClearOrigin?.(); }}>
                  <X className="w-3.5 h-3.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors" />
                </button>
              )}
            </div>
            {focusedField === "origin" && renderSuggestionList(originSuggestions, "origin")}
          </div>

          {/* Swap */}
          <button
            onClick={handleSwap}
            className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] transition-colors text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex-shrink-0 self-center"
            title="Swap origin and destination"
            aria-label="Swap origin and destination"
          >
            <ArrowLeftRight className="w-4 h-4" />
          </button>

          {/* Destination */}
          <div className={`relative ${isMobile ? "" : "flex-1"}`}>
            <div className="flex items-center gap-2 bg-[var(--input-bg)] rounded-lg border border-[var(--border)] px-3 py-2">
              <MapPin className="w-4 h-4 text-red-500 flex-shrink-0" />
              <input
                type="text"
                value={destText}
                onChange={(e) => handleDestChange(e.target.value)}
                onFocus={() => setFocusedField("dest")}
                placeholder="Destination"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--text-muted)] text-[var(--text-primary)] min-w-0"
                aria-label="Destination location"
              />
              {destText && (
                <button onClick={() => { setDestText(""); setDestCoord(null); setDestSuggestions([]); lastExternalDest.current = undefined; onClearDestination?.(); }}>
                  <X className="w-3.5 h-3.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors" />
                </button>
              )}
            </div>
            {focusedField === "dest" && renderSuggestionList(destSuggestions, "dest")}
          </div>

          {/* Search button */}
          <button
            onClick={handleSubmit}
            disabled={!canSearch}
            className={`flex items-center justify-center gap-2 rounded-lg font-medium text-sm transition-all flex-shrink-0 ${
              isMobile ? "w-full py-3 mt-1" : "px-4 py-2"
            } ${
              canSearch
                ? "bg-[var(--accent)] hover:opacity-90 text-white"
                : "bg-[var(--surface)] text-[var(--text-muted)] cursor-not-allowed"
            }`}
            aria-label="Search routes"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            {isMobile && (loading ? "Calculating..." : "Find Routes")}
          </button>
        </div>

        {/* Desktop: right actions */}
        {!isMobile && (
          <div className="flex items-center gap-0.5 pl-2 border-l border-[var(--actions-border)] ml-1 flex-shrink-0">
            <AlertsBell count={alertCount} onClick={onAlertsClick} />
            <ThemeToggle theme={theme} onToggle={onThemeToggle} />
            <button
              onClick={onViewModeToggle}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === "dashboard"
                  ? "bg-[var(--accent)] text-white"
                  : "hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
              title={viewMode === "dashboard" ? "Switch to map view" : "Switch to dashboard view"}
              aria-label={viewMode === "dashboard" ? "Switch to map view" : "Switch to dashboard view"}
            >
              <LayoutDashboard className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
