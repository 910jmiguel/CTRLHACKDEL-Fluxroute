"use client";

import type { LineStop } from "@/lib/types";

interface LineStripDiagramProps {
  stops: LineStop[];
  color: string;
  startStopId?: string;
  endStopId?: string;
  onSelectStart: (stopId: string) => void;
  onSelectEnd: (stopId: string) => void;
}

export default function LineStripDiagram({
  stops,
  color,
  startStopId,
  endStopId,
  onSelectStart,
  onSelectEnd,
}: LineStripDiagramProps) {
  if (stops.length === 0) return null;

  const startIdx = stops.findIndex((s) => s.stop_id === startStopId);
  const endIdx = stops.findIndex((s) => s.stop_id === endStopId);
  const minIdx = Math.min(startIdx, endIdx);
  const maxIdx = Math.max(startIdx, endIdx);

  const isInRange = (i: number) =>
    startIdx >= 0 && endIdx >= 0 && i >= minIdx && i <= maxIdx;

  return (
    <div className="overflow-x-auto py-2">
      <div className="flex items-center min-w-max px-1">
        {stops.map((stop, i) => {
          const inRange = isInRange(i);
          const isStart = stop.stop_id === startStopId;
          const isEnd = stop.stop_id === endStopId;
          const isSelected = isStart || isEnd;

          return (
            <div key={stop.stop_id} className="flex items-center">
              {/* Station dot */}
              <button
                onClick={() => {
                  if (!startStopId || (startStopId && endStopId)) {
                    onSelectStart(stop.stop_id);
                    onSelectEnd("");
                  } else {
                    onSelectEnd(stop.stop_id);
                  }
                }}
                className="flex flex-col items-center group relative"
                title={stop.stop_name}
              >
                <div
                  className={`w-3 h-3 rounded-full border-2 transition-all ${
                    isSelected
                      ? "scale-125"
                      : inRange
                        ? "opacity-100"
                        : "opacity-40"
                  }`}
                  style={{
                    backgroundColor: inRange || isSelected ? color : "transparent",
                    borderColor: color,
                  }}
                />
                <span
                  className={`text-[9px] mt-1 max-w-[50px] text-center leading-tight truncate ${
                    isSelected
                      ? "text-white font-medium"
                      : inRange
                        ? "text-slate-300"
                        : "text-slate-500"
                  }`}
                >
                  {stop.stop_name}
                </span>
              </button>

              {/* Connecting line */}
              {i < stops.length - 1 && (
                <div
                  className="h-0.5 w-6 mx-0.5"
                  style={{
                    backgroundColor: color,
                    opacity: isInRange(i) && isInRange(i + 1) ? 1 : 0.2,
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
