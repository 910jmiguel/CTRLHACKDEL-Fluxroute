"use client";

import { useState } from "react";
import { Layers, ChevronDown } from "lucide-react";

export interface TransitLineVisibility {
  line1: boolean;
  line2: boolean;
  line4: boolean;
  line5: boolean;
  line6: boolean;
  streetcars: boolean;
}

interface MapLayersControlProps {
  transitLineVisibility: TransitLineVisibility;
  onToggleTransitLine: (key: keyof TransitLineVisibility) => void;
  showVehicles: boolean;
  onToggleVehicles: () => void;
  showTraffic: boolean;
  onToggleTraffic: () => void;
}

const TTC_LINES: { key: keyof TransitLineVisibility; label: string; color: string }[] = [
  { key: "line1", label: "Line 1 Yonge-University", color: "#FFCD00" },
  { key: "line2", label: "Line 2 Bloor-Danforth", color: "#00A859" },
  { key: "line4", label: "Line 4 Sheppard", color: "#A8518A" },
  { key: "line5", label: "Line 5 Eglinton", color: "#FF8C00" },
  { key: "line6", label: "Line 6 Finch West", color: "#6EC4E8" },
  { key: "streetcars", label: "Streetcars", color: "#DD3333" },
];

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`relative w-8 h-[18px] rounded-full transition-colors flex-shrink-0 ${
        checked ? "bg-blue-500" : "bg-slate-600"
      }`}
    >
      <div
        className={`absolute top-[2px] w-[14px] h-[14px] rounded-full bg-white shadow-sm transition-transform ${
          checked ? "translate-x-[16px]" : "translate-x-[2px]"
        }`}
      />
    </button>
  );
}

export default function MapLayersControl({
  transitLineVisibility,
  onToggleTransitLine,
  showVehicles,
  onToggleVehicles,
  showTraffic,
  onToggleTraffic,
}: MapLayersControlProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="absolute top-4 left-4 z-20">
      {!expanded ? (
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-black/70 backdrop-blur-md border border-white/10 text-slate-200 hover:bg-black/80 transition-colors shadow-lg"
        >
          <Layers className="w-4 h-4" />
          <span className="text-sm font-medium">Layers</span>
        </button>
      ) : (
        <div className="w-64 rounded-lg bg-black/70 backdrop-blur-md border border-white/10 shadow-xl">
          {/* Header */}
          <button
            onClick={() => setExpanded(false)}
            className="w-full flex items-center justify-between px-3 py-2.5 text-slate-200 hover:bg-white/5 transition-colors rounded-t-lg"
          >
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4" />
              <span className="text-sm font-semibold">Layers</span>
            </div>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </button>

          {/* Transit section */}
          <div className="px-3 pb-2">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Transit
            </div>
            <div className="space-y-1">
              {TTC_LINES.map(({ key, label, color }) => (
                <div key={key} className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs text-slate-300">{label}</span>
                  </div>
                  <Toggle
                    checked={transitLineVisibility[key]}
                    onChange={() => onToggleTransitLine(key)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-white/5 mx-3" />

          {/* Live data section */}
          <div className="px-3 py-2">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Live Data
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between py-1">
                <span className="text-xs text-slate-300">Vehicles</span>
                <Toggle checked={showVehicles} onChange={onToggleVehicles} />
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-xs text-slate-300">Traffic</span>
                <Toggle checked={showTraffic} onChange={onToggleTraffic} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
