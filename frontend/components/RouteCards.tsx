"use client";

import { useState } from "react";
import {
  Clock,
  MapPin,
  DollarSign,
  Train,
  Car,
  Footprints,
  Repeat,
  ParkingCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type { RouteOption, RouteSegment } from "@/lib/types";
import DelayIndicator from "./DelayIndicator";
import CostBreakdown from "./CostBreakdown";
import DirectionSteps from "./DirectionSteps";

interface RouteCardsProps {
  routes: RouteOption[];
  selectedRoute: RouteOption | null;
  onSelect: (route: RouteOption) => void;
  onCustomize?: (route: RouteOption) => void;
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

const SEGMENT_BAR_COLOR: Record<string, string> = {
  transit: "bg-yellow-500",
  driving: "bg-blue-500",
  walking: "bg-emerald-500",
  hybrid: "bg-purple-500",
};

const SEGMENT_ICON: Record<string, React.ReactNode> = {
  transit: <Train className="w-3.5 h-3.5" />,
  driving: <Car className="w-3.5 h-3.5" />,
  walking: <Footprints className="w-3.5 h-3.5" />,
};

function CongestionBadge({ level }: { level?: string }) {
  if (!level || level === "low") return null;
  const colors: Record<string, string> = {
    moderate: "bg-yellow-500/20 text-yellow-400",
    heavy: "bg-orange-500/20 text-orange-400",
    severe: "bg-red-500/20 text-red-400",
  };
  const labels: Record<string, string> = {
    moderate: "Moderate Traffic",
    heavy: "Heavy Traffic",
    severe: "Severe Traffic",
  };
  return (
    <span
      className={`text-[10px] px-1.5 py-0.5 rounded-full ${colors[level] || ""}`}
    >
      {labels[level] || level}
    </span>
  );
}

function SegmentTimeline({
  segments,
  parkingInfo,
}: {
  segments: RouteSegment[];
  parkingInfo?: RouteOption["parking_info"];
}) {
  // Auto-expand directions for single-segment routes (pure driving/walking)
  const [expandedSeg, setExpandedSeg] = useState<number | null>(
    segments.length === 1 ? 0 : null
  );

  // Find where to insert parking info (after driving segment in hybrid)
  let parkingInsertAfter = -1;
  if (parkingInfo) {
    for (let i = 0; i < segments.length; i++) {
      if (
        segments[i].mode === "driving" &&
        i + 1 < segments.length &&
        segments[i + 1].mode === "transit"
      ) {
        parkingInsertAfter = i;
        break;
      }
    }
  }

  const items: React.ReactNode[] = [];

  segments.forEach((seg, i) => {
    const isExpanded = expandedSeg === i;
    const hasSteps = seg.steps && seg.steps.length > 0;
    const barColor = seg.color
      ? `bg-[${seg.color}]`
      : SEGMENT_BAR_COLOR[seg.mode] || "bg-slate-500";

    items.push(
      <div key={`seg-${i}`} className="flex gap-2">
        {/* Timeline bar */}
        <div className="flex flex-col items-center">
          <div
            className={`w-5 h-5 rounded-full flex items-center justify-center text-white ${barColor}`}
            style={seg.color ? { backgroundColor: seg.color } : {}}
          >
            {SEGMENT_ICON[seg.mode] || <MapPin className="w-3 h-3" />}
          </div>
          {i < segments.length - 1 && (
            <div
              className="w-0.5 flex-1 min-h-[16px]"
              style={{
                backgroundColor: seg.color || "#64748b",
                opacity: 0.4,
              }}
            />
          )}
        </div>

        {/* Segment info */}
        <div className="flex-1 pb-2 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-white">
              {seg.instructions || `${seg.mode} segment`}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-[11px] text-slate-400">
            <span>{Math.round(seg.duration_min)} min</span>
            <span>
              {seg.distance_km < 1
                ? `${Math.round(seg.distance_km * 1000)}m`
                : `${seg.distance_km.toFixed(1)} km`}
            </span>
            {seg.congestion_level && (
              <CongestionBadge level={seg.congestion_level} />
            )}
          </div>

          {/* Expandable driving directions */}
          {hasSteps && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setExpandedSeg(isExpanded ? null : i);
              }}
              className="flex items-center gap-1 mt-1 text-[11px] text-blue-400 hover:text-blue-300"
            >
              {isExpanded ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
              {isExpanded ? "Hide" : "Show"} {seg.steps!.length} directions
            </button>
          )}

          {isExpanded && hasSteps && (
            <div
              className="mt-1"
              onClick={(e) => e.stopPropagation()}
            >
              <DirectionSteps steps={seg.steps!} />
            </div>
          )}
        </div>
      </div>
    );

    // Insert parking info after driving segment
    if (i === parkingInsertAfter && parkingInfo) {
      const rate =
        parkingInfo.daily_rate === 0
          ? "Free"
          : `$${parkingInfo.daily_rate.toFixed(0)}/day`;
      items.push(
        <div key="parking" className="flex gap-2">
          <div className="flex flex-col items-center">
            <div className="w-5 h-5 rounded-full flex items-center justify-center bg-cyan-600 text-white">
              <ParkingCircle className="w-3 h-3" />
            </div>
            <div className="w-0.5 flex-1 min-h-[16px] bg-cyan-600/40" />
          </div>
          <div className="flex-1 pb-2">
            <span className="text-xs font-medium text-cyan-400">
              Park at {parkingInfo.station_name}
            </span>
            <div className="flex items-center gap-3 mt-0.5 text-[11px] text-slate-400">
              <span>{rate}</span>
              {parkingInfo.capacity > 0 && (
                <span>~{parkingInfo.capacity} spots</span>
              )}
              {parkingInfo.parking_type && (
                <span className="capitalize">{parkingInfo.parking_type} lot</span>
              )}
            </div>
          </div>
        </div>
      );
    }
  });

  return <div className="mt-2 ml-0.5">{items}</div>;
}

export default function RouteCards({
  routes,
  selectedRoute,
  onSelect,
  onCustomize,
}: RouteCardsProps) {
  if (routes.length === 0) {
    return (
      <div className="text-center text-[var(--text-muted)] text-sm py-6">
        <p>No routes available for this mode.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wide px-1">
        Routes
      </h3>
      <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
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

              {route.traffic_summary && (
                <div className="text-xs mt-1.5 flex items-center gap-1">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${
                      route.traffic_summary.includes("Severe")
                        ? "bg-red-500"
                        : route.traffic_summary.includes("Heavy")
                          ? "bg-orange-500"
                          : route.traffic_summary.includes("Moderate")
                            ? "bg-yellow-500"
                            : "bg-emerald-500"
                    }`}
                  />
                  <span className="text-[var(--text-secondary)]">
                    {route.traffic_summary}
                  </span>
                </div>
              )}

              {/* Segment timeline — consistent for all route types */}
              {isSelected && route.segments.length > 0 && (
                <SegmentTimeline
                  segments={route.segments}
                  parkingInfo={route.parking_info}
                />
              )}

              {isSelected && onCustomize && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCustomize(route);
                  }}
                  className="mt-2 w-full text-xs font-medium text-purple-400 border border-purple-500/30 rounded-lg px-3 py-1.5 hover:bg-purple-500/10 transition-all"
                >
                  Customize Route
                </button>
              )}

              {!isSelected && route.summary && (
                <div className="text-xs text-[var(--text-muted)] mt-1.5 truncate">
                  {route.summary}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
