"use client";

import { Clock, MapPin, DollarSign, Train, Car, Footprints, Repeat } from "lucide-react";
import type { RouteOption } from "@/lib/types";
import DelayIndicator from "./DelayIndicator";
import CostBreakdown from "./CostBreakdown";
import DirectionSteps from "./DirectionSteps";

interface RouteCardsProps {
  routes: RouteOption[];
  selectedRoute: RouteOption | null;
  onSelect: (route: RouteOption) => void;
}

const MODE_ICON: Record<string, React.ReactNode> = {
  transit: <Train className="w-4 h-4" />,
  driving: <Car className="w-4 h-4" />,
  walking: <Footprints className="w-4 h-4" />,
  hybrid: <Repeat className="w-4 h-4" />,
  cycling: <Repeat className="w-4 h-4" />,
};

const MODE_COLOR: Record<string, string> = {
  transit: "border-yellow-500/40",
  driving: "border-blue-500/40",
  walking: "border-emerald-500/40",
  hybrid: "border-purple-500/40",
  cycling: "border-orange-500/40",
};

export default function RouteCards({
  routes,
  selectedRoute,
  onSelect,
}: RouteCardsProps) {
  if (routes.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wide px-1">
        Routes
      </h3>
      <div className="space-y-2 max-h-[40vh] overflow-y-auto pr-1">
        {routes.map((route) => {
          const isSelected = selectedRoute?.id === route.id;
          return (
            <button
              key={route.id}
              onClick={() => onSelect(route)}
              className={`w-full text-left glass-card p-3 transition-all border-l-4 ${
                MODE_COLOR[route.mode]
              } ${
                isSelected
                  ? "ring-1 ring-blue-500/50 bg-[var(--surface)]"
                  : "hover:bg-[var(--surface-hover)]"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[var(--text-secondary)]">
                    {MODE_ICON[route.mode]}
                  </span>
                  <div>
                    <div className="text-sm font-semibold">{route.label}</div>
                    <div className="text-xs text-[var(--text-secondary)] capitalize">
                      {route.mode}
                    </div>
                  </div>
                </div>
                {route.delay_info.probability > 0 && (
                  <DelayIndicator
                    probability={route.delay_info.probability}
                    expectedMinutes={route.delay_info.expected_minutes}
                    compact
                  />
                )}
              </div>

              <div className="flex items-center gap-4 mt-2 text-xs text-[var(--text-secondary)]">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {Math.round(route.total_duration_min)} min
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {route.total_distance_km.toFixed(1)} km
                </span>
                <span className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />
                  <CostBreakdown cost={route.cost} />
                </span>
              </div>

              {route.summary && (
                <div className="text-xs text-[var(--text-muted)] mt-1.5 truncate">
                  {route.summary}
                </div>
              )}

              {(() => {
                const allSteps = route.segments.flatMap(s => s.steps || []);
                return allSteps.length > 0 ? <DirectionSteps steps={allSteps} /> : null;
              })()}
            </button>
          );
        })}
      </div>
    </div>
  );
}
