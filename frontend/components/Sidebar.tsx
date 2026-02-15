"use client";

import { useState } from "react";
import { PanelLeftClose, PanelLeft, Navigation, Play, Square } from "lucide-react";
import type { Coordinate, RouteOption, IsochroneResponse } from "@/lib/types";
import type { ModeFilter } from "@/hooks/useRoutes";
import RouteInput from "./RouteInput";
import RouteCards from "./RouteCards";
import DecisionMatrix from "./DecisionMatrix";
import IsochronePanel from "./IsochronePanel";

interface SidebarProps {
  routes: RouteOption[];
  filteredRoutes: RouteOption[];
  selectedRoute: RouteOption | null;
  loading: boolean;
  error: string | null;
  onSearch: (origin: Coordinate, destination: Coordinate) => void;
  onSelectRoute: (route: RouteOption) => void;
  activeFilter: ModeFilter;
  onFilterChange: (filter: ModeFilter) => void;
  showTraffic: boolean;
  onToggleTraffic: () => void;
  originLabel?: string | null;
  origin?: Coordinate | null;
  destination?: Coordinate | null;
  onClearOrigin?: () => void;
  onClearDestination?: () => void;
  onSwap?: (newOrigin: Coordinate | null, newDest: Coordinate | null) => void;
  onClearRoutes?: () => void;
  onCustomize?: (route: RouteOption) => void;
  onStartNavigation?: () => void;
  isNavigating?: boolean;
  isochroneData?: IsochroneResponse | null;
  onIsochroneLoaded?: (data: IsochroneResponse) => void;
  onClearIsochrone?: () => void;
}

export default function Sidebar({
  routes,
  filteredRoutes,
  selectedRoute,
  loading,
  error,
  onSearch,
  onSelectRoute,
  activeFilter,
  onFilterChange,
  showTraffic,
  onToggleTraffic,
  originLabel,
  origin,
  destination,
  onClearOrigin,
  onClearDestination,
  onSwap,
  onClearRoutes,
  onCustomize,
  onStartNavigation,
  isNavigating,
  isochroneData,
  onIsochroneLoaded,
  onClearIsochrone,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="absolute top-4 left-4 z-30 glass-card p-2 hover:bg-[var(--surface-hover)] transition-colors"
      >
        <PanelLeft className="w-5 h-5" />
      </button>
    );
  }

  return (
    <div className="w-[420px] h-full glass-card flex flex-col z-20 relative">
      {/* Header with collapse */}
      <div className="flex items-center justify-between p-4 pb-0">
        <div /> {/* Spacer for alignment */}
        <button
          onClick={() => setCollapsed(true)}
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <RouteInput
          onSearch={onSearch}
          loading={loading}
          originLabel={originLabel}
          origin={origin}
          destination={destination}
          onClearOrigin={() => { onClearOrigin?.(); onClearRoutes?.(); }}
          onClearDestination={() => { onClearDestination?.(); onClearRoutes?.(); }}
          onSwap={onSwap}
        />

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Isochrone Panel — available when origin is set */}
        {origin && onIsochroneLoaded && onClearIsochrone && (
          <IsochronePanel
            center={origin}
            onIsochroneLoaded={onIsochroneLoaded}
            onClear={onClearIsochrone}
          />
        )}

        {routes.length > 0 && (
          <>
            {/* Navigation button */}
            {isNavigating ? (
              <div className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Navigation Active
              </div>
            ) : onStartNavigation ? (
              <button
                onClick={onStartNavigation}
                className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-900/30"
              >
                <Play className="w-4 h-4" />
                Start Navigation
              </button>
            ) : null}

            {/* Traffic toggle */}
            <button
              onClick={onToggleTraffic}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${showTraffic
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                : "bg-slate-800/60 text-slate-400 border border-slate-700/50 hover:bg-slate-700/50"
                }`}
            >
              <Navigation className="w-4 h-4" />
              Traffic Layer
              <span className={`ml-auto text-xs px-1.5 py-0.5 rounded ${showTraffic ? "bg-blue-500/30 text-blue-300" : "bg-slate-700 text-slate-500"
                }`}>
                {showTraffic ? "ON" : "OFF"}
              </span>
            </button>

            <DecisionMatrix
              routes={routes}
              activeFilter={activeFilter}
              onFilterChange={onFilterChange}
              onSelect={onSelectRoute}
            />

            <RouteCards
              routes={filteredRoutes}
              selectedRoute={selectedRoute}
              onSelect={onSelectRoute}
              onCustomize={onCustomize}
            />
          </>
        )}

        {!loading && routes.length === 0 && !error && (
          <div className="text-center text-[var(--text-muted)] text-sm mt-8">
            <p>Enter origin and destination to compare routes across transit, driving, walking, and hybrid options.</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-[var(--border)] text-center">
        <span className="text-xs text-[var(--text-muted)]">
          FluxRoute MVP — AI-Powered GTA Transit
        </span>
      </div>
    </div>
  );
}
