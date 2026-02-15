"use client";

import { useEffect } from "react";
import { Car, Footprints, Train, X, ChevronUp, ChevronDown } from "lucide-react";
import type { LineInfo } from "@/lib/types";
import type { CustomSegment } from "@/hooks/useCustomRoute";
import { TTC_LINES } from "@/hooks/useCustomRoute";
import LineStripDiagram from "./LineStripDiagram";

interface SegmentEditorProps {
  segment: CustomSegment;
  index: number;
  total: number;
  onUpdate: (id: string, updates: Partial<CustomSegment>) => void;
  onRemove: (id: string) => void;
  onMove: (id: string, direction: "up" | "down") => void;
  onFetchLine: (lineId: string) => Promise<LineInfo | null>;
}

const MODE_OPTIONS = [
  { value: "driving" as const, label: "Drive", icon: <Car className="w-3.5 h-3.5" /> },
  { value: "walking" as const, label: "Walk", icon: <Footprints className="w-3.5 h-3.5" /> },
  { value: "transit" as const, label: "Transit", icon: <Train className="w-3.5 h-3.5" /> },
];

export default function SegmentEditor({
  segment,
  index,
  total,
  onUpdate,
  onRemove,
  onMove,
  onFetchLine,
}: SegmentEditorProps) {
  // Fetch line stops when line_id changes
  useEffect(() => {
    if (segment.mode === "transit" && segment.line_id && !segment.lineInfo) {
      onFetchLine(segment.line_id).then((info) => {
        if (info) onUpdate(segment.id, { lineInfo: info });
      });
    }
  }, [segment.mode, segment.line_id, segment.lineInfo, segment.id, onUpdate, onFetchLine]);

  const lineStops = segment.lineInfo?.stops || [];
  const lineColor = TTC_LINES.find((l) => l.id === segment.line_id)?.color || "#F0CC49";

  return (
    <div className="glass-card p-3 border border-slate-700/40">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs text-slate-400 font-medium">Segment {index + 1}</span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onMove(segment.id, "up")}
            disabled={index === 0}
            className="p-0.5 text-slate-500 hover:text-white disabled:opacity-30 transition-colors"
          >
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onMove(segment.id, "down")}
            disabled={index === total - 1}
            className="p-0.5 text-slate-500 hover:text-white disabled:opacity-30 transition-colors"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onRemove(segment.id)}
            className="p-0.5 text-red-400/60 hover:text-red-400 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Mode selector */}
      <div className="flex gap-1 mb-3">
        {MODE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() =>
              onUpdate(segment.id, {
                mode: opt.value,
                line_id: undefined,
                start_station_id: undefined,
                end_station_id: undefined,
                lineInfo: undefined,
              })
            }
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-all ${
              segment.mode === opt.value
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                : "bg-slate-800/50 text-slate-400 hover:bg-slate-700/50"
            }`}
          >
            {opt.icon}
            {opt.label}
          </button>
        ))}
      </div>

      {/* Transit options */}
      {segment.mode === "transit" && (
        <div className="space-y-2">
          {/* Line selector */}
          <select
            value={segment.line_id || ""}
            onChange={(e) =>
              onUpdate(segment.id, {
                line_id: e.target.value || undefined,
                start_station_id: undefined,
                end_station_id: undefined,
                lineInfo: undefined,
              })
            }
            className="w-full bg-slate-800/80 text-white text-xs px-3 py-2 rounded-lg border border-slate-700/50 focus:border-blue-500/50 focus:outline-none"
          >
            <option value="">Select a line...</option>
            {TTC_LINES.map((line) => (
              <option key={line.id} value={line.id}>
                {line.name}
              </option>
            ))}
          </select>

          {/* Station selectors */}
          {lineStops.length > 0 && (
            <>
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={segment.start_station_id || ""}
                  onChange={(e) =>
                    onUpdate(segment.id, { start_station_id: e.target.value || undefined })
                  }
                  className="bg-slate-800/80 text-white text-xs px-2 py-1.5 rounded-lg border border-slate-700/50 focus:border-blue-500/50 focus:outline-none"
                >
                  <option value="">Start station...</option>
                  {lineStops.map((s) => (
                    <option key={s.stop_id} value={s.stop_id}>
                      {s.stop_name}
                    </option>
                  ))}
                </select>
                <select
                  value={segment.end_station_id || ""}
                  onChange={(e) =>
                    onUpdate(segment.id, { end_station_id: e.target.value || undefined })
                  }
                  className="bg-slate-800/80 text-white text-xs px-2 py-1.5 rounded-lg border border-slate-700/50 focus:border-blue-500/50 focus:outline-none"
                >
                  <option value="">End station...</option>
                  {lineStops.map((s) => (
                    <option key={s.stop_id} value={s.stop_id}>
                      {s.stop_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Visual line strip */}
              <LineStripDiagram
                stops={lineStops}
                color={lineColor}
                startStopId={segment.start_station_id}
                endStopId={segment.end_station_id}
                onSelectStart={(id) => onUpdate(segment.id, { start_station_id: id })}
                onSelectEnd={(id) => onUpdate(segment.id, { end_station_id: id })}
              />
            </>
          )}
        </div>
      )}

      {/* Drive/Walk info */}
      {segment.mode !== "transit" && (
        <div className="text-xs text-slate-400">
          {segment.mode === "driving" ? "Drive" : "Walk"} — auto-routed from{" "}
          {index === 0 ? "origin" : "previous segment"} to{" "}
          {index === total - 1 ? "destination" : "next segment start"}
        </div>
      )}
    </div>
  );
}
