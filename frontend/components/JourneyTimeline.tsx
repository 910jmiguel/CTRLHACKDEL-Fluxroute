"use client";

import { useState, useMemo } from "react";
import { Train, Bus, Car, Footprints, MapPin, ChevronDown, ChevronUp, ParkingCircle, ArrowRight } from "lucide-react";
import Image from "next/image";
import type { RouteOption, RouteSegment } from "@/lib/types";
import { TTC_LINE_LOGOS, MODE_COLORS } from "@/lib/constants";
import DelayIndicator from "./DelayIndicator";
import DirectionSteps from "./DirectionSteps";

interface JourneyTimelineProps {
  route: RouteOption;
  originLabel?: string;
  destinationLabel?: string;
}

const SEGMENT_ICON: Record<string, React.ReactNode> = {
  transit: <Train className="w-3.5 h-3.5" />,
  driving: <Car className="w-3.5 h-3.5" />,
  walking: <Footprints className="w-3.5 h-3.5" />,
};

/** Extract TTC line ID (1-6) from a segment, checking both transit_route_id and transit_line */
function getLineId(seg: RouteSegment): string | null {
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

/** Parse "HH:MM" to total minutes from midnight */
function parseTimeToMinutes(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}

/** Format total minutes to "HH:MM" */
function formatMinutesToTime(minutes: number): string {
  const m = ((minutes % 1440) + 1440) % 1440; // wrap around midnight
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(Math.round(m % 60)).padStart(2, "0")}`;
}

/** Build a friendly route label from segment data */
function getTransitLabel(seg: RouteSegment): { routeId: string | null; routeName: string } {
  const routeId = seg.transit_route_id?.replace(/^line/i, "").trim() || null;
  const lineName = seg.transit_line || "";

  // If transit_line already contains the route number (e.g., "Line 1 Yonge-University")
  if (lineName) return { routeId, routeName: lineName };

  // Fallback: extract from instructions
  if (seg.instructions) {
    const match = seg.instructions.match(/^Take\s+(.+?)\s+from\s+/i);
    if (match) return { routeId, routeName: match[1] };
  }

  return { routeId, routeName: routeId ? `Route ${routeId}` : "Transit" };
}

/** Determine if a transit segment is a bus (not subway/LRT) */
function isBusRoute(seg: RouteSegment): boolean {
  const lineId = getLineId(seg);
  if (lineId) return false; // Has a subway/LRT logo → not a bus
  return seg.mode === "transit";
}

function ScheduleSourceBadge({ source }: { source?: string }) {
  if (!source) return null;
  const styles: Record<string, string> = {
    "gtfs-rt": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    "gtfs-static": "bg-blue-500/20 text-blue-400 border-blue-500/30",
    "estimated": "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  };
  const labels: Record<string, string> = {
    "gtfs-rt": "Live",
    "gtfs-static": "Sched",
    "estimated": "Est.",
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${styles[source] || styles.estimated}`}>
      {labels[source] || source}
    </span>
  );
}

function CongestionBadge({ level }: { level?: string }) {
  if (!level || level === "low") return null;
  const colors: Record<string, string> = {
    moderate: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    heavy: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    severe: "bg-red-500/20 text-red-400 border-red-500/30",
  };
  const labels: Record<string, string> = {
    moderate: "Moderate Traffic",
    heavy: "Heavy Traffic",
    severe: "Severe Traffic",
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${colors[level] || ""}`}>
      {labels[level] || level}
    </span>
  );
}

export default function JourneyTimeline({
  route,
  originLabel,
  destinationLabel,
}: JourneyTimelineProps) {
  const [expandedSeg, setExpandedSeg] = useState<number | null>(null);

  const segments = route.segments;
  const totalDuration = route.total_duration_min;

  // Compute start/end times for every segment from route departure_time
  const segmentTimes = useMemo(() => {
    const departureMins = route.departure_time
      ? parseTimeToMinutes(route.departure_time)
      : null;
    if (departureMins === null) return null;

    let cumulative = departureMins;
    return segments.map((seg) => {
      const startMin = cumulative;
      // For transit, prefer actual schedule times if available
      const segStart = seg.mode === "transit" && seg.departure_time
        ? parseTimeToMinutes(seg.departure_time)
        : startMin;
      const segEnd = seg.mode === "transit" && seg.arrival_time
        ? parseTimeToMinutes(seg.arrival_time)
        : segStart + seg.duration_min;
      cumulative = segEnd;
      return {
        start: formatMinutesToTime(segStart),
        end: formatMinutesToTime(segEnd),
      };
    });
  }, [route.departure_time, segments]);

  // Find parking insert point for hybrid
  let parkingInsertAfter = -1;
  if (route.parking_info) {
    for (let i = 0; i < segments.length; i++) {
      if (segments[i].mode === "driving" && i + 1 < segments.length && segments[i + 1].mode === "transit") {
        parkingInsertAfter = i;
        break;
      }
    }
  }

  return (
    <div className="space-y-4">
      {/* Duration strip — proportional mode segments */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <span className="font-geist-mono font-semibold text-[var(--text-primary)] text-base">
            {Math.round(totalDuration)} min
          </span>
          <span>{route.total_distance_km.toFixed(1)} km</span>
          {route.traffic_summary && (
            <CongestionBadge level={
              route.traffic_summary.includes("Severe") ? "severe"
              : route.traffic_summary.includes("Heavy") ? "heavy"
              : route.traffic_summary.includes("Moderate") ? "moderate"
              : undefined
            } />
          )}
        </div>

        <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
          {segments.map((seg, i) => {
            const proportion = Math.max(seg.duration_min / totalDuration, 0.05);
            const color = seg.color || MODE_COLORS[seg.mode] || "#64748b";
            return (
              <div
                key={i}
                className="h-full rounded-full relative group"
                style={{ flex: proportion, backgroundColor: color }}
                title={`${seg.instructions || seg.mode} — ${Math.round(seg.duration_min)} min`}
              />
            );
          })}
        </div>

        {/* Mode icons under the strip */}
        <div className="flex items-center gap-1 text-[var(--text-muted)]">
          {segments.map((seg, i) => {
            const lineId = getLineId(seg);
            const busRoute = isBusRoute(seg);
            const routeNum = seg.transit_route_id?.replace(/^line/i, "").trim();
            return (
              <div key={i} className="flex items-center gap-1">
                {i > 0 && <ArrowRight className="w-3 h-3 text-[var(--text-muted)] opacity-40" />}
                {lineId ? (
                  <Image
                    src={TTC_LINE_LOGOS[lineId]}
                    alt={`Line ${lineId}`}
                    width={16}
                    height={16}
                    className="rounded-sm"
                  />
                ) : busRoute && routeNum ? (
                  <span className="flex items-center gap-0.5">
                    <Bus className="w-3 h-3" style={{ color: seg.color || MODE_COLORS[seg.mode] }} />
                    <span className="text-[9px] font-bold font-geist-mono" style={{ color: seg.color || MODE_COLORS[seg.mode] }}>
                      {routeNum}
                    </span>
                  </span>
                ) : (
                  <span style={{ color: seg.color || MODE_COLORS[seg.mode] }}>
                    {SEGMENT_ICON[seg.mode] || <MapPin className="w-3 h-3" />}
                  </span>
                )}
                <span className="text-[10px] font-geist-mono">{Math.round(seg.duration_min)}m</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Delay badge */}
      {route.delay_info.probability > 0 && (
        <DelayIndicator
          probability={route.delay_info.probability}
          expectedMinutes={route.delay_info.expected_minutes}
          confidence={route.delay_info.confidence}
          factors={route.delay_info.factors}
        />
      )}

      {/* Vertical journey timeline */}
      <div className="space-y-0">
        {/* Start marker */}
        <div className="flex gap-3 items-start">
          <div className="flex flex-col items-center">
            <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs font-bold ring-2 ring-emerald-500/20">
              O
            </div>
            <div className="w-0.5 flex-1 min-h-[12px] bg-[var(--border)]" />
          </div>
          <div className="pb-3">
            <div className="text-sm font-medium text-[var(--text-primary)]">
              {originLabel || "Origin"}
            </div>
            {route.departure_time && (
              <div className="text-xs text-[var(--text-muted)] font-geist-mono">
                {route.departure_time}
              </div>
            )}
          </div>
        </div>

        {/* Segments */}
        {segments.map((seg, i) => {
          const lineId = getLineId(seg);
          const color = seg.color || MODE_COLORS[seg.mode] || "#64748b";
          const isExpanded = expandedSeg === i;
          const hasSteps = seg.steps && seg.steps.length > 0;
          const isTransit = seg.mode === "transit";
          const isWalking = seg.mode === "walking";
          const busRoute = isBusRoute(seg);
          const transitLabel = isTransit ? getTransitLabel(seg) : null;
          const times = segmentTimes?.[i];

          return (
            <div key={i}>
              <div className="flex gap-3 items-start">
                {/* Timeline connector + icon */}
                <div className="flex flex-col items-center">
                  {lineId ? (
                    <Image
                      src={TTC_LINE_LOGOS[lineId]}
                      alt={`Line ${lineId}`}
                      width={24}
                      height={24}
                      className="rounded-full flex-shrink-0"
                    />
                  ) : busRoute && transitLabel?.routeId ? (
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-white"
                      style={{ backgroundColor: color }}
                    >
                      <Bus className="w-3.5 h-3.5" />
                    </div>
                  ) : (
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-white"
                      style={{ backgroundColor: color }}
                    >
                      {SEGMENT_ICON[seg.mode] || <MapPin className="w-3 h-3" />}
                    </div>
                  )}
                  {i < segments.length - 1 && (
                    <div
                      className={`w-0.5 flex-1 min-h-[20px] ${isWalking ? "border-l-2 border-dashed" : ""}`}
                      style={isWalking
                        ? { borderColor: `${color}66` }
                        : { backgroundColor: `${color}66` }
                      }
                    />
                  )}
                </div>

                {/* Segment details */}
                <div className="flex-1 pb-3 min-w-0">
                  {/* Transit route label with number + name */}
                  {isTransit && transitLabel ? (
                    <div className="flex items-center gap-2 flex-wrap">
                      {busRoute && transitLabel.routeId && (
                        <span
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-bold text-white"
                          style={{ backgroundColor: color }}
                        >
                          <Bus className="w-3 h-3" />
                          {transitLabel.routeId}
                        </span>
                      )}
                      <span className="text-sm font-medium text-[var(--text-primary)]">
                        {transitLabel.routeName}
                      </span>
                      {route.delay_info.probability < 0.3 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          On Time
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-[var(--text-primary)]">
                        {seg.instructions || `${seg.mode.charAt(0).toUpperCase() + seg.mode.slice(1)} segment`}
                      </span>
                    </div>
                  )}

                  {/* From → To for transit segments */}
                  {isTransit && seg.instructions && (
                    <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                      {seg.instructions.replace(/^Take\s+.+?\s+from\s+/i, "From ").replace(/\s+to\s+/i, " → ")}
                    </div>
                  )}

                  {/* Time breakdown for all segments */}
                  {times && (
                    <div className="flex items-center gap-2 mt-0.5 text-[11px]">
                      <span className="font-geist-mono text-[var(--text-primary)]">
                        {times.start} → {times.end}
                      </span>
                      {isTransit && <ScheduleSourceBadge source={seg.schedule_source} />}
                    </div>
                  )}

                  <div className="flex items-center gap-3 mt-0.5 text-[11px] text-[var(--text-muted)]">
                    <span className="font-geist-mono">{Math.round(seg.duration_min)} min</span>
                    <span className="font-geist-mono">
                      {seg.distance_km < 1
                        ? `${Math.round(seg.distance_km * 1000)}m`
                        : `${seg.distance_km.toFixed(1)} km`}
                    </span>
                    {seg.congestion_level && <CongestionBadge level={seg.congestion_level} />}
                  </div>

                  {/* Next departures for transit */}
                  {isTransit && seg.next_departures && seg.next_departures.length > 0 && (
                    <div className="mt-1 text-[10px] text-[var(--text-muted)]">
                      <span className="opacity-70">Next: </span>
                      <span className="font-geist-mono">
                        {seg.next_departures.slice(0, 3).map((d) => d.departure_time).join(", ")}
                      </span>
                      {seg.next_departures.length > 3 && (
                        <span className="opacity-50"> (+{seg.next_departures.length - 3} more)</span>
                      )}
                    </div>
                  )}

                  {/* Expandable directions */}
                  {hasSteps && (
                    <button
                      onClick={() => setExpandedSeg(isExpanded ? null : i)}
                      className="flex items-center gap-1 mt-1.5 text-[11px] text-[var(--accent)] hover:opacity-80"
                    >
                      {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      {isExpanded ? "Hide" : "Show"} {seg.steps!.length} directions
                    </button>
                  )}

                  {isExpanded && hasSteps && (
                    <div className="mt-1.5">
                      <DirectionSteps steps={seg.steps!} />
                    </div>
                  )}
                </div>
              </div>

              {/* Parking marker for hybrid */}
              {i === parkingInsertAfter && route.parking_info && (
                <div className="flex gap-3 items-start">
                  <div className="flex flex-col items-center">
                    <div className="w-6 h-6 rounded-full bg-cyan-500 flex items-center justify-center text-white">
                      <ParkingCircle className="w-3.5 h-3.5" />
                    </div>
                    <div className="w-0.5 flex-1 min-h-[12px] bg-cyan-500/40" />
                  </div>
                  <div className="pb-3">
                    <div className="text-sm font-medium text-cyan-400">
                      Park at {route.parking_info.station_name}
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)]">
                      {route.parking_info.daily_rate === 0 ? "Free" : `$${route.parking_info.daily_rate.toFixed(0)}/day`}
                      {route.parking_info.capacity > 0 && ` · ~${route.parking_info.capacity} spots`}
                    </div>
                  </div>
                </div>
              )}

              {/* Transfer marker between transit segments */}
              {i < segments.length - 1 &&
                seg.mode === "transit" &&
                segments[i + 1].mode === "transit" && (
                  <div className="flex gap-3 items-start">
                    <div className="flex flex-col items-center">
                      <div className="w-5 h-5 rounded-full border-2 border-[var(--text-muted)] flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-[var(--text-muted)]" />
                      </div>
                      <div className="w-0.5 flex-1 min-h-[8px] bg-[var(--border)]" />
                    </div>
                    <div className="pb-2">
                      <div className="text-xs font-medium text-[var(--text-secondary)]">
                        Transfer
                      </div>
                    </div>
                  </div>
                )}
            </div>
          );
        })}

        {/* End marker */}
        <div className="flex gap-3 items-start">
          <div className="flex flex-col items-center">
            <div className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center text-white text-xs font-bold ring-2 ring-red-500/20">
              X
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-[var(--text-primary)]">
              {destinationLabel || "Destination"}
            </div>
            {(route.arrival_time || (segmentTimes && segmentTimes.length > 0)) && (
              <div className="text-xs text-[var(--text-muted)] font-geist-mono">
                {route.arrival_time || segmentTimes?.[segmentTimes!.length - 1]?.end}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cost summary */}
      <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
        <div className="text-xs text-[var(--text-muted)]">Total cost</div>
        <div className="font-geist-mono font-semibold text-[var(--text-primary)]">
          ${route.cost.total.toFixed(2)}
          {route.cost.fare > 0 && (
            <span className="text-xs text-[var(--text-muted)] ml-1 font-normal">
              (fare ${route.cost.fare.toFixed(2)})
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
