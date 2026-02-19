"use client";

import { useMemo } from "react";
import { Clock, DollarSign, Smile } from "lucide-react";
import type { RouteOption } from "@/lib/types";
import type { ModeFilter } from "@/hooks/useRoutes";
import RouteComparisonTable from "./RouteComparisonTable";

interface DashboardViewProps {
  routes: RouteOption[];
  filteredRoutes: RouteOption[];
  selectedRoute: RouteOption | null;
  onSelectRoute: (route: RouteOption) => void;
  activeFilter: ModeFilter;
  onFilterChange: (filter: ModeFilter) => void;
}

export default function DashboardView({
  routes,
  filteredRoutes,
  selectedRoute,
  onSelectRoute,
  activeFilter,
  onFilterChange,
}: DashboardViewProps) {
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

  const FILTER_CONFIG: { filter: ModeFilter; label: string }[] = [
    { filter: "all", label: "All" },
    { filter: "driving", label: "Driving" },
    { filter: "transit", label: "Transit" },
    { filter: "hybrid", label: "Hybrid" },
  ];

  return (
    <div className="min-h-full bg-[var(--background)]">
      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* Decision Matrix — expanded */}
        {filteredRoutes.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {fastest && (
              <button
                onClick={() => onSelectRoute(fastest)}
                className={`glass-card p-5 text-center transition-all hover:shadow-lg ${
                  selectedRoute?.id === fastest.id ? "ring-2 ring-blue-500/50" : ""
                }`}
                aria-label={`Select fastest route: ${Math.round(fastest.total_duration_min)} minutes`}
              >
                <Clock className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                <div className="text-xs text-[var(--text-muted)] uppercase font-medium tracking-wide">
                  Fastest
                </div>
                <div className="font-geist-mono text-2xl font-bold text-[var(--text-primary)] mt-1">
                  {Math.round(fastest.total_duration_min)} min
                </div>
                <div className="text-xs text-[var(--text-secondary)] mt-1">
                  {fastest.label} ({fastest.mode})
                </div>
              </button>
            )}
            {cheapest && (
              <button
                onClick={() => onSelectRoute(cheapest)}
                className={`glass-card p-5 text-center transition-all hover:shadow-lg ${
                  selectedRoute?.id === cheapest.id ? "ring-2 ring-emerald-500/50" : ""
                }`}
                aria-label={`Select cheapest route: $${cheapest.cost.total.toFixed(2)}`}
              >
                <DollarSign className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
                <div className="text-xs text-[var(--text-muted)] uppercase font-medium tracking-wide">
                  Thrifty
                </div>
                <div className="font-geist-mono text-2xl font-bold text-[var(--text-primary)] mt-1">
                  ${cheapest.cost.total.toFixed(2)}
                </div>
                <div className="text-xs text-[var(--text-secondary)] mt-1">
                  {cheapest.label} ({cheapest.mode})
                </div>
              </button>
            )}
            {zenBest && (
              <button
                onClick={() => onSelectRoute(zenBest)}
                className={`glass-card p-5 text-center transition-all hover:shadow-lg ${
                  selectedRoute?.id === zenBest.id ? "ring-2 ring-purple-500/50" : ""
                }`}
                aria-label={`Select lowest stress route: ${(zenBest.stress_score * 100).toFixed(0)}%`}
              >
                <Smile className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                <div className="text-xs text-[var(--text-muted)] uppercase font-medium tracking-wide">
                  Zen
                </div>
                <div className="font-geist-mono text-2xl font-bold text-[var(--text-primary)] mt-1">
                  {(zenBest.stress_score * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-[var(--text-secondary)] mt-1">
                  {zenBest.label} ({zenBest.mode})
                </div>
              </button>
            )}
          </div>
        )}

        {/* Mode filter tabs */}
        <div className="flex gap-2 flex-wrap">
          {FILTER_CONFIG.map(({ filter, label }) => {
            const count = filter === "all"
              ? routes.length
              : routes.filter((r) => r.mode === filter).length;
            if (filter !== "all" && count === 0) return null;
            const isActive = activeFilter === filter;
            return (
              <button
                key={filter}
                onClick={() => onFilterChange(filter)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-[var(--accent)] text-white"
                    : "bg-[var(--surface)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]"
                }`}
                aria-pressed={isActive}
              >
                {label} ({count})
              </button>
            );
          })}
        </div>

        {/* Comparison table */}
        <div className="glass-card overflow-hidden">
          <RouteComparisonTable
            routes={filteredRoutes}
            selectedRoute={selectedRoute}
            onSelect={onSelectRoute}
          />
        </div>

        {filteredRoutes.length === 0 && routes.length > 0 && (
          <div className="text-center text-[var(--text-muted)] text-sm py-8">
            No routes match this filter. Try selecting &quot;All&quot;.
          </div>
        )}
      </div>
    </div>
  );
}
