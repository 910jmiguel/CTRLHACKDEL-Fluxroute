"use client";

import { Car, Train, Repeat, Clock, DollarSign, MapPin } from "lucide-react";
import type { RouteOption, RouteMode } from "@/lib/types";

interface DecisionMatrixProps {
  routes: RouteOption[];
  onSelect: (route: RouteOption) => void;
}

interface ModeColumn {
  mode: RouteMode;
  icon: React.ReactNode;
  title: string;
  route: RouteOption | null;
  color: string;
  borderColor: string;
}

function getWinnerBadge(
  route: RouteOption,
  allRoutes: (RouteOption | null)[]
): { label: string; color: string } | null {
  const valid = allRoutes.filter((r): r is RouteOption => r !== null);
  if (valid.length < 2) return null;

  const isFastest =
    route.total_duration_min <=
    Math.min(...valid.map((r) => r.total_duration_min));
  const isCheapest =
    route.cost.total <= Math.min(...valid.map((r) => r.cost.total));

  if (isFastest && isCheapest)
    return { label: "Best Overall", color: "bg-amber-500/20 text-amber-400" };
  if (isFastest)
    return { label: "Fastest", color: "bg-blue-500/20 text-blue-400" };
  if (isCheapest)
    return { label: "Cheapest", color: "bg-emerald-500/20 text-emerald-400" };

  // Check if best balance (lowest stress or middle ground)
  const scores = valid.map((r) => r.stress_score);
  if (route.stress_score <= Math.min(...scores))
    return { label: "Best Balance", color: "bg-purple-500/20 text-purple-400" };

  return null;
}

function getKeyDetail(route: RouteOption): string {
  if (route.mode === "driving") {
    return route.traffic_summary || "Direct route";
  }
  if (route.mode === "transit") {
    const transitSegs = route.segments.filter((s) => s.mode === "transit");
    const transfers = Math.max(0, transitSegs.length - 1);
    return transfers > 0
      ? `${transfers} transfer${transfers > 1 ? "s" : ""}`
      : "Direct service";
  }
  if (route.mode === "hybrid") {
    if (route.parking_info) {
      const rate =
        route.parking_info.daily_rate === 0
          ? "Free"
          : `$${route.parking_info.daily_rate}`;
      return `Park @ ${route.parking_info.station_name} ${rate}`;
    }
    return "Park & Ride";
  }
  return "";
}

export default function DecisionMatrix({
  routes,
  onSelect,
}: DecisionMatrixProps) {
  if (routes.length < 2) return null;

  // Pick best route per mode category (shortest duration)
  const bestByMode = (mode: RouteMode): RouteOption | null => {
    const modeRoutes = routes.filter((r) => r.mode === mode);
    if (modeRoutes.length === 0) return null;
    return modeRoutes.reduce((best, r) =>
      r.total_duration_min < best.total_duration_min ? r : best
    );
  };

  const columns: ModeColumn[] = [
    {
      mode: "driving",
      icon: <Car className="w-5 h-5" />,
      title: "DRIVE",
      route: bestByMode("driving"),
      color: "text-blue-400",
      borderColor: "border-blue-500/30 hover:border-blue-500/60",
    },
    {
      mode: "transit",
      icon: <Train className="w-5 h-5" />,
      title: "TRANSIT",
      route: bestByMode("transit"),
      color: "text-yellow-400",
      borderColor: "border-yellow-500/30 hover:border-yellow-500/60",
    },
    {
      mode: "hybrid",
      icon: <Repeat className="w-5 h-5" />,
      title: "PARK & RIDE",
      route: bestByMode("hybrid"),
      color: "text-purple-400",
      borderColor: "border-purple-500/30 hover:border-purple-500/60",
    },
  ];

  const allBest = columns.map((c) => c.route);

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wide px-1 mb-2">
        Compare Modes
      </h3>
      <div className="grid grid-cols-3 gap-2">
        {columns.map((col) => {
          if (!col.route) {
            return (
              <div
                key={col.mode}
                className="glass-card p-3 text-center border border-slate-700/30 opacity-40"
              >
                <div className={`flex justify-center mb-1 ${col.color}`}>
                  {col.icon}
                </div>
                <div className="text-xs font-semibold text-slate-500">
                  {col.title}
                </div>
                <div className="text-xs text-slate-600 mt-2">N/A</div>
              </div>
            );
          }

          const badge = getWinnerBadge(col.route, allBest);
          const detail = getKeyDetail(col.route);

          return (
            <button
              key={col.mode}
              onClick={() => onSelect(col.route!)}
              className={`glass-card p-3 text-center border transition-all ${col.borderColor}`}
            >
              <div className={`flex justify-center mb-1 ${col.color}`}>
                {col.icon}
              </div>
              <div className="text-xs font-semibold text-white">
                {col.title}
              </div>

              {/* Time */}
              <div className="flex items-center justify-center gap-1 mt-2">
                <Clock className="w-3 h-3 text-slate-400" />
                <span className="text-sm font-bold text-white">
                  {Math.round(col.route.total_duration_min)} min
                </span>
              </div>

              {/* Cost */}
              <div className="flex items-center justify-center gap-1 mt-1">
                <DollarSign className="w-3 h-3 text-slate-400" />
                <span className="text-xs text-slate-300">
                  ${col.route.cost.total.toFixed(2)}
                </span>
              </div>

              {/* Distance */}
              <div className="flex items-center justify-center gap-1 mt-1">
                <MapPin className="w-3 h-3 text-slate-400" />
                <span className="text-xs text-slate-400">
                  {col.route.total_distance_km.toFixed(1)} km
                </span>
              </div>

              {/* Winner badge */}
              {badge && (
                <div
                  className={`text-[10px] mt-2 px-1.5 py-0.5 rounded-full inline-block ${badge.color}`}
                >
                  {badge.label}
                </div>
              )}

              {/* Key detail */}
              {detail && (
                <div className="text-[10px] text-slate-400 mt-1 truncate px-1">
                  {detail}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
