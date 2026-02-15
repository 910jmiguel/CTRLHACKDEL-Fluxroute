"use client";

import { useMemo } from "react";
import { Car, Train, Repeat, Layers, Clock, DollarSign, Smile } from "lucide-react";
import type { RouteOption } from "@/lib/types";
import type { ModeFilter } from "@/hooks/useRoutes";

interface DecisionMatrixProps {
  routes: RouteOption[];
  activeFilter: ModeFilter;
  onFilterChange: (filter: ModeFilter) => void;
  onSelect: (route: RouteOption) => void;
}

interface TabConfig {
  filter: ModeFilter;
  icon: React.ReactNode;
  label: string;
  color: string;
  activeColor: string;
  borderColor: string;
}

const TABS: TabConfig[] = [
  {
    filter: "all",
    icon: <Layers className="w-4 h-4" />,
    label: "All",
    color: "text-slate-400",
    activeColor: "text-white",
    borderColor: "border-white/60",
  },
  {
    filter: "driving",
    icon: <Car className="w-4 h-4" />,
    label: "Drive",
    color: "text-blue-400/60",
    activeColor: "text-blue-400",
    borderColor: "border-blue-500/60",
  },
  {
    filter: "transit",
    icon: <Train className="w-4 h-4" />,
    label: "Transit",
    color: "text-yellow-400/60",
    activeColor: "text-yellow-400",
    borderColor: "border-yellow-500/60",
  },
  {
    filter: "hybrid",
    icon: <Repeat className="w-4 h-4" />,
    label: "Hybrid",
    color: "text-purple-400/60",
    activeColor: "text-purple-400",
    borderColor: "border-purple-500/60",
  },
];

export default function DecisionMatrix({
  routes,
  activeFilter,
  onFilterChange,
  onSelect,
}: DecisionMatrixProps) {
  // Count routes per mode
  const counts = useMemo(() => {
    const c: Record<ModeFilter, number> = { all: routes.length, driving: 0, transit: 0, hybrid: 0 };
    for (const r of routes) {
      if (r.mode in c) c[r.mode as ModeFilter]++;
    }
    return c;
  }, [routes]);

  // Get best stats for the active filter
  const activeRoutes = useMemo(() => {
    if (activeFilter === "all") return routes;
    return routes.filter((r) => r.mode === activeFilter);
  }, [routes, activeFilter]);

  const fastest = useMemo(() => {
    if (activeRoutes.length === 0) return null;
    return activeRoutes.reduce((a, b) => a.total_duration_min < b.total_duration_min ? a : b);
  }, [activeRoutes]);

  const cheapest = useMemo(() => {
    if (activeRoutes.length === 0) return null;
    return activeRoutes.reduce((a, b) => a.cost.total < b.cost.total ? a : b);
  }, [activeRoutes]);

  const zenBest = useMemo(() => {
    if (activeRoutes.length === 0) return null;
    return activeRoutes.reduce((a, b) => a.stress_score < b.stress_score ? a : b);
  }, [activeRoutes]);

  if (routes.length === 0) return null;

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wide px-1 mb-2">
        Compare Modes
      </h3>

      {/* Tab bar */}
      <div className="flex gap-1 bg-slate-800/40 rounded-lg p-1">
        {TABS.map((tab) => {
          const count = counts[tab.filter];
          if (tab.filter !== "all" && count === 0) return null;

          const isActive = activeFilter === tab.filter;
          return (
            <button
              key={tab.filter}
              onClick={() => onFilterChange(tab.filter)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? `bg-slate-700/80 ${tab.activeColor} border-b-2 ${tab.borderColor}`
                  : `${tab.color} hover:bg-slate-700/40`
              }`}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
              <span className={`text-[10px] px-1 py-0.5 rounded-full ${
                isActive ? "bg-white/10" : "bg-slate-700/50"
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Summary row */}
      {activeRoutes.length > 0 && (
        <div className="flex gap-2 mt-2">
          {fastest && (
            <button
              onClick={() => onSelect(fastest)}
              className="flex-1 glass-card px-2 py-1.5 text-center hover:bg-[var(--surface-hover)] transition-all"
            >
              <div className="flex items-center justify-center gap-1 text-blue-400">
                <Clock className="w-3 h-3" />
                <span className="text-[10px] uppercase font-medium">Fastest</span>
              </div>
              <div className="text-sm font-bold text-white">
                {Math.round(fastest.total_duration_min)} min
              </div>
            </button>
          )}
          {cheapest && (
            <button
              onClick={() => onSelect(cheapest)}
              className="flex-1 glass-card px-2 py-1.5 text-center hover:bg-[var(--surface-hover)] transition-all"
            >
              <div className="flex items-center justify-center gap-1 text-emerald-400">
                <DollarSign className="w-3 h-3" />
                <span className="text-[10px] uppercase font-medium">Thrifty</span>
              </div>
              <div className="text-sm font-bold text-white">
                ${cheapest.cost.total.toFixed(2)}
              </div>
            </button>
          )}
          {zenBest && (
            <button
              onClick={() => onSelect(zenBest)}
              className="flex-1 glass-card px-2 py-1.5 text-center hover:bg-[var(--surface-hover)] transition-all"
            >
              <div className="flex items-center justify-center gap-1 text-purple-400">
                <Smile className="w-3 h-3" />
                <span className="text-[10px] uppercase font-medium">Zen</span>
              </div>
              <div className="text-sm font-bold text-white">
                {(zenBest.stress_score * 100).toFixed(0)}%
              </div>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
