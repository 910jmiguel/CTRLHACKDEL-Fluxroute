"use client";

import { useState } from "react";
import { PanelLeftClose, PanelLeft, Navigation } from "lucide-react";
import type { Coordinate, RouteOption } from "@/lib/types";
import RouteInput from "./RouteInput";
import RouteCards from "./RouteCards";
import DecisionMatrix from "./DecisionMatrix";

interface SidebarProps {
  routes: RouteOption[];
  selectedRoute: RouteOption | null;
  loading: boolean;
  error: string | null;
  onSearch: (origin: Coordinate, destination: Coordinate) => void;
  onSelectRoute: (route: RouteOption) => void;
  showTraffic: boolean;
  onToggleTraffic: () => void;
}

export default function Sidebar({
  routes,
  selectedRoute,
  loading,
  error,
  onSearch,
  onSelectRoute,
  showTraffic,
  onToggleTraffic,
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
    <div className="w-[380px] h-full glass-card flex flex-col z-20 relative">
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
        <RouteInput onSearch={onSearch} loading={loading} />

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        {routes.length > 0 && (
          <>
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

            <DecisionMatrix routes={routes} onSelect={onSelectRoute} />
            <RouteCards
              routes={routes}
              selectedRoute={selectedRoute}
              onSelect={onSelectRoute}
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
