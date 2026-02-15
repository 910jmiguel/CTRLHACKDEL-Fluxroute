"use client";

import { Car, Train, Footprints, Repeat, Check } from "lucide-react";
import Image from "next/image";
import type { RouteOption } from "@/lib/types";
import { TTC_LINE_LOGOS, MODE_COLORS } from "@/lib/constants";
import DelayIndicator from "./DelayIndicator";
import { useIsMobile } from "@/hooks/useMediaQuery";

interface RouteComparisonTableProps {
  routes: RouteOption[];
  selectedRoute: RouteOption | null;
  onSelect: (route: RouteOption) => void;
}

const MODE_ICON: Record<string, React.ReactNode> = {
  transit: <Train className="w-4 h-4" />,
  driving: <Car className="w-4 h-4" />,
  walking: <Footprints className="w-4 h-4" />,
  hybrid: <Repeat className="w-4 h-4" />,
};

function getTransitLineId(route: RouteOption): string | null {
  for (const seg of route.segments) {
    if (seg.mode === "transit" && seg.transit_route_id) {
      const id = seg.transit_route_id.replace(/^line/i, "").trim();
      if (TTC_LINE_LOGOS[id]) return id;
    }
  }
  return null;
}

export default function RouteComparisonTable({
  routes,
  selectedRoute,
  onSelect,
}: RouteComparisonTableProps) {
  const isMobile = useIsMobile();

  if (routes.length === 0) {
    return (
      <div className="text-center text-[var(--text-muted)] text-sm py-12">
        No routes to compare. Enter origin and destination above.
      </div>
    );
  }

  // Mobile: stacked cards
  if (isMobile) {
    return (
      <div className="space-y-3">
        {routes.map((route) => {
          const isSelected = selectedRoute?.id === route.id;
          const lineId = getTransitLineId(route);
          return (
            <button
              key={route.id}
              onClick={() => onSelect(route)}
              className={`w-full text-left glass-card p-4 transition-all ${
                isSelected ? "ring-2 ring-[var(--accent)]/50" : ""
              }`}
              aria-pressed={isSelected}
            >
              <div className="flex items-center gap-3 mb-3">
                {lineId ? (
                  <Image src={TTC_LINE_LOGOS[lineId]} alt={`Line ${lineId}`} width={24} height={24} className="rounded-sm" />
                ) : (
                  <span style={{ color: MODE_COLORS[route.mode] }}>{MODE_ICON[route.mode]}</span>
                )}
                <div>
                  <div className="font-medium text-[var(--text-primary)]">{route.label}</div>
                  <div className="text-xs text-[var(--text-muted)] capitalize">{route.mode}</div>
                </div>
                {isSelected && <Check className="w-4 h-4 text-[var(--accent)] ml-auto" />}
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-[var(--text-muted)]">Duration</div>
                  <div className="font-geist-mono font-semibold text-[var(--text-primary)]">{Math.round(route.total_duration_min)} min</div>
                </div>
                <div>
                  <div className="text-[var(--text-muted)]">Distance</div>
                  <div className="font-geist-mono font-semibold text-[var(--text-primary)]">{route.total_distance_km.toFixed(1)} km</div>
                </div>
                <div>
                  <div className="text-[var(--text-muted)]">Cost</div>
                  <div className="font-geist-mono font-semibold text-[var(--text-primary)]">${route.cost.total.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[var(--text-muted)]">Stress</div>
                  <div className="font-geist-mono font-semibold text-[var(--text-primary)]">{(route.stress_score * 100).toFixed(0)}%</div>
                </div>
              </div>
              {route.delay_info.probability > 0 && (
                <div className="mt-3">
                  <DelayIndicator
                    probability={route.delay_info.probability}
                    expectedMinutes={route.delay_info.expected_minutes}
                    compact
                  />
                </div>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  // Desktop: table view
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" role="grid" aria-label="Route comparison">
        <thead>
          <tr className="border-b border-[var(--border)] text-xs text-[var(--text-muted)] uppercase tracking-wider">
            <th className="text-left py-3 px-4 font-medium">Route</th>
            <th className="text-left py-3 px-4 font-medium">Mode</th>
            <th className="text-right py-3 px-4 font-medium">Duration</th>
            <th className="text-right py-3 px-4 font-medium">Distance</th>
            <th className="text-right py-3 px-4 font-medium">Cost</th>
            <th className="text-center py-3 px-4 font-medium">Delay Risk</th>
            <th className="text-right py-3 px-4 font-medium">Stress</th>
            <th className="text-center py-3 px-4 font-medium">Select</th>
          </tr>
        </thead>
        <tbody>
          {routes.map((route) => {
            const isSelected = selectedRoute?.id === route.id;
            const lineId = getTransitLineId(route);
            return (
              <tr
                key={route.id}
                onClick={() => onSelect(route)}
                className={`border-b border-[var(--border)] cursor-pointer transition-colors ${
                  isSelected
                    ? "bg-[var(--accent)]/5"
                    : "hover:bg-[var(--surface-hover)]"
                }`}
                role="row"
                aria-selected={isSelected}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(route);
                  }
                }}
              >
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {lineId ? (
                      <Image src={TTC_LINE_LOGOS[lineId]} alt={`Line ${lineId}`} width={20} height={20} className="rounded-sm" />
                    ) : (
                      <span style={{ color: MODE_COLORS[route.mode] }}>{MODE_ICON[route.mode]}</span>
                    )}
                    <span className="font-medium text-[var(--text-primary)]">{route.label}</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-[var(--text-secondary)] capitalize">{route.mode}</td>
                <td className="py-3 px-4 text-right font-geist-mono text-[var(--text-primary)]">
                  {Math.round(route.total_duration_min)} min
                </td>
                <td className="py-3 px-4 text-right font-geist-mono text-[var(--text-secondary)]">
                  {route.total_distance_km.toFixed(1)} km
                </td>
                <td className="py-3 px-4 text-right font-geist-mono text-[var(--text-primary)]">
                  ${route.cost.total.toFixed(2)}
                </td>
                <td className="py-3 px-4 text-center">
                  {route.delay_info.probability > 0 ? (
                    <DelayIndicator
                      probability={route.delay_info.probability}
                      expectedMinutes={route.delay_info.expected_minutes}
                      compact
                    />
                  ) : (
                    <span className="text-xs text-[var(--text-muted)]">N/A</span>
                  )}
                </td>
                <td className="py-3 px-4 text-right font-geist-mono text-[var(--text-secondary)]">
                  {(route.stress_score * 100).toFixed(0)}%
                </td>
                <td className="py-3 px-4 text-center">
                  {isSelected ? (
                    <Check className="w-4 h-4 text-[var(--accent)] mx-auto" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-[var(--border)] mx-auto" />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
