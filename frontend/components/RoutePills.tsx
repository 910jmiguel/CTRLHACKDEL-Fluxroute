"use client";

import { useMemo } from "react";
import { Car, Train, Repeat, Footprints, Clock, DollarSign, Smile, LayoutGrid } from "lucide-react";
import Image from "next/image";
import type { RouteOption, RouteSegment } from "@/lib/types";
import type { ModeFilter } from "@/hooks/useRoutes";
import { TTC_LINE_LOGOS, MODE_COLORS } from "@/lib/constants";

interface RoutePillsProps {
  routes: RouteOption[];
  selectedRoute: RouteOption | null;
  onSelect: (route: RouteOption) => void;
  activeFilter: ModeFilter;
  onFilterChange: (filter: ModeFilter) => void;
}

const MODE_ICON: Record<string, React.ReactNode> = {
  transit: <Train className="w-3.5 h-3.5" />,
  driving: <Car className="w-3.5 h-3.5" />,
  walking: <Footprints className="w-3.5 h-3.5" />,
  hybrid: <Repeat className="w-3.5 h-3.5" />,
};

const FILTER_ICON: Record<string, React.ReactNode> = {
  all: <LayoutGrid className="w-4 h-4" />,
  driving: <Car className="w-4 h-4" />,
  transit: <Train className="w-4 h-4" />,
  hybrid: <Repeat className="w-4 h-4" />,
};

const FILTER_CONFIG: { filter: ModeFilter; label: string }[] = [
  { filter: "all", label: "All" },
  { filter: "driving", label: "Drive" },
  { filter: "transit", label: "Transit" },
  { filter: "hybrid", label: "Hybrid" },
];

/** Extract TTC line ID (1-6) from a segment, checking both transit_route_id and transit_line */
function extractLineId(seg: RouteSegment): string | null {
  if (seg.mode !== "transit") return null;
  // Try transit_route_id first
  if (seg.transit_route_id) {
    const id = seg.transit_route_id.replace(/^line/i, "").trim();
    if (TTC_LINE_LOGOS[id]) return id;
  }
  // Fallback: extract line number from transit_line (e.g., "Line 5 Eglinton", "TTC Eglinton Line")
  const lineName = seg.transit_line || seg.instructions || "";
  const match = lineName.match(/Line\s*(\d+)/i);
  if (match && TTC_LINE_LOGOS[match[1]]) return match[1];
  return null;
}

function getTransitLineId(route: RouteOption): string | null {
  for (const seg of route.segments) {
    const id = extractLineId(seg);
    if (id) return id;
  }
  return null;
}

export default function RoutePills({
  routes,
  selectedRoute,
  onSelect,
  activeFilter,
  onFilterChange,
}: RoutePillsProps) {
  const filteredRoutes = useMemo(() => {
    if (activeFilter === "all") return routes;
    return routes.filter((r) => r.mode === activeFilter);
  }, [routes, activeFilter]);

  const counts = useMemo(() => {
    const c: Record<ModeFilter, number> = { all: routes.length, driving: 0, transit: 0, hybrid: 0 };
    for (const r of routes) {
      if (r.mode in c) c[r.mode as ModeFilter]++;
    }
    return c;
  }, [routes]);

  // Quick-select winners
  const fastest = useMemo(() => {
    if (filteredRoutes.length === 0) return null;
    return filteredRoutes.reduce((a, b) => a.total_duration_min < b.total_duration_min ? a : b);
  }, [filteredRoutes]);

  const cheapest = useMemo(() => {
    if (filteredRoutes.length === 0) return null;
    return filteredRoutes.reduce((a, b) => a.cost.total < b.cost.total ? a : b);
  }, [filteredRoutes]);

  const zenBest = useMemo(() => {
    if (filteredRoutes.length === 0) return null;
    return filteredRoutes.reduce((a, b) => a.stress_score < b.stress_score ? a : b);
  }, [filteredRoutes]);

  if (routes.length === 0) return null;

  return (
    <div className="space-y-3">
      {/* Mode filter chips */}
      <div className="flex gap-2">
        {FILTER_CONFIG.map(({ filter, label }) => {
          if (filter !== "all" && counts[filter] === 0) return null;
          const isActive = activeFilter === filter;
          return (
            <button
              key={filter}
              onClick={() => onFilterChange(filter)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-sm font-medium transition-all ${
                isActive
                  ? "bg-[var(--accent)] text-white"
                  : "bg-[var(--surface)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]"
              }`}
              aria-pressed={isActive}
            >
              {FILTER_ICON[filter]}
              {label}
              <span className="ml-0.5 opacity-60">{counts[filter]}</span>
            </button>
          );
        })}
      </div>

      {/* Quick-select: Fastest | Thrifty | Zen */}
      <div className="flex gap-2">
        {fastest && (
          <button
            onClick={() => onSelect(fastest)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-lg transition-all text-xs font-medium border ${
              selectedRoute?.id === fastest.id
                ? "border-blue-500/50 bg-blue-500/10 text-blue-400"
                : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <Clock className="w-3 h-3" />
            <span className="font-geist-mono">{Math.round(fastest.total_duration_min)}m</span>
          </button>
        )}
        {cheapest && (
          <button
            onClick={() => onSelect(cheapest)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-lg transition-all text-xs font-medium border ${
              selectedRoute?.id === cheapest.id
                ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
                : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <DollarSign className="w-3 h-3" />
            <span className="font-geist-mono">${cheapest.cost.total.toFixed(2)}</span>
          </button>
        )}
        {zenBest && (
          <button
            onClick={() => onSelect(zenBest)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-lg transition-all text-xs font-medium border ${
              selectedRoute?.id === zenBest.id
                ? "border-purple-500/50 bg-purple-500/10 text-purple-400"
                : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <Smile className="w-3 h-3" />
            <span>Zen</span>
          </button>
        )}
      </div>

      {/* Route pills */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {filteredRoutes.map((route) => {
          const isSelected = selectedRoute?.id === route.id;
          const modeColor = MODE_COLORS[route.mode] || "#3B82F6";
          const lineId = getTransitLineId(route);

          return (
            <button
              key={route.id}
              onClick={() => onSelect(route)}
              className={`flex-shrink-0 flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl transition-all border-b-2 ${
                isSelected
                  ? "bg-[var(--surface)] shadow-md"
                  : "bg-transparent hover:bg-[var(--surface-hover)]"
              }`}
              style={{ borderBottomColor: isSelected ? modeColor : "transparent" }}
              aria-selected={isSelected}
              role="tab"
            >
              {/* Mode icon or TTC line logo */}
              <div className="flex-shrink-0">
                {lineId ? (
                  <Image
                    src={TTC_LINE_LOGOS[lineId]}
                    alt={`Line ${lineId}`}
                    width={20}
                    height={20}
                    className="rounded-sm"
                  />
                ) : (
                  <span style={{ color: modeColor }}>{MODE_ICON[route.mode]}</span>
                )}
              </div>

              <div className="text-left">
                <div className="font-geist-mono text-sm font-semibold text-[var(--text-primary)]">
                  {Math.round(route.total_duration_min)} min
                </div>
                <div className="text-[11px] text-[var(--text-muted)]">
                  ${route.cost.total.toFixed(2)}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
