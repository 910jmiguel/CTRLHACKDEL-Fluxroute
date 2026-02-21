"use client";

import { useState } from "react";
import { Layers, ChevronDown } from "lucide-react";
import Image from "next/image";
import { TTC_LINE_LOGOS } from "@/lib/constants";

export interface TransitLineVisibility {
  line1: boolean;
  line2: boolean;
  line4: boolean;
  line5: boolean;
  line6: boolean;
  streetcars: boolean;
  upExpress: boolean;
  goTransit: boolean;
}

interface MapLayersControlProps {
  transitLineVisibility: TransitLineVisibility;
  onToggleTransitLine: (key: keyof TransitLineVisibility) => void;
  showVehicles: boolean;
  onToggleVehicles: () => void;
  showTraffic: boolean;
  onToggleTraffic: () => void;
  showUnselectedRoutes: boolean;
  onToggleUnselectedRoutes: () => void;
  hasSelectedRoute: boolean;
}

const TTC_LINES: { key: keyof TransitLineVisibility; label: string; color: string; lineId?: string }[] = [
  { key: "line1", label: "Line 1 Yonge-University", color: "#FFCD00", lineId: "1" },
  { key: "line2", label: "Line 2 Bloor-Danforth", color: "#00A859", lineId: "2" },
  { key: "line4", label: "Line 4 Sheppard", color: "#A8518A", lineId: "4" },
  { key: "line5", label: "Line 5 Eglinton", color: "#FF8C00", lineId: "5" },
  { key: "line6", label: "Line 6 Finch West", color: "#6EC4E8", lineId: "6" },
  { key: "streetcars", label: "Streetcars", color: "#DD3333" },
];

const REGIONAL_LINES: { key: keyof TransitLineVisibility; label: string; color: string }[] = [
  { key: "goTransit", label: "GO Transit Rail", color: "#00853F" },
  { key: "upExpress", label: "UP Express", color: "#1E3A8A" },
];

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`relative w-8 h-[18px] rounded-full transition-colors flex-shrink-0 ${
        checked ? "bg-blue-500" : "bg-[var(--text-muted)]"
      }`}
      role="switch"
      aria-checked={checked}
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
  showUnselectedRoutes,
  onToggleUnselectedRoutes,
  hasSelectedRoute,
}: MapLayersControlProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      {!expanded ? (
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg panel-glass text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shadow-lg"
          aria-label="Open map layers control"
        >
          <Layers className="w-4 h-4" />
          <span className="text-sm font-medium">Layers</span>
        </button>
      ) : (
        <div className="w-64 rounded-lg panel-glass shadow-xl">
          {/* Header */}
          <button
            onClick={() => setExpanded(false)}
            className="w-full flex items-center justify-between px-3 py-2.5 text-[var(--text-primary)] hover:bg-[var(--surface-hover)] transition-colors rounded-t-lg"
          >
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4" />
              <span className="text-sm font-semibold">Layers</span>
            </div>
            <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
          </button>

          {/* TTC section */}
          <div className="px-3 pb-2">
            <div className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
              TTC
            </div>
            <div className="space-y-1">
              {TTC_LINES.map(({ key, label, color, lineId }) => (
                <div key={key} className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    {lineId && TTC_LINE_LOGOS[lineId] ? (
                      <Image
                        src={TTC_LINE_LOGOS[lineId]}
                        alt={label}
                        width={16}
                        height={16}
                        className="rounded-sm flex-shrink-0"
                      />
                    ) : (
                      <div
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }}
                      />
                    )}
                    <span className="text-xs text-[var(--text-secondary)]">{label}</span>
                  </div>
                  <Toggle
                    checked={transitLineVisibility[key]}
                    onChange={() => onToggleTransitLine(key)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Regional section */}
          <div className="border-t border-[var(--border)] mx-3" />
          <div className="px-3 py-2">
            <div className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
              Regional
            </div>
            <div className="space-y-1">
              {REGIONAL_LINES.map(({ key, label, color }) => (
                <div key={key} className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                    <span className="text-xs text-[var(--text-secondary)]">{label}</span>
                  </div>
                  <Toggle
                    checked={transitLineVisibility[key]}
                    onChange={() => onToggleTransitLine(key)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Routes section — only visible when a route is selected */}
          {hasSelectedRoute && (
            <>
              <div className="border-t border-[var(--border)] mx-3" />
              <div className="px-3 py-2">
                <div className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
                  Routes
                </div>
                <div className="flex items-center justify-between py-1">
                  <span className="text-xs text-[var(--text-secondary)]">Show other routes</span>
                  <Toggle checked={showUnselectedRoutes} onChange={onToggleUnselectedRoutes} />
                </div>
              </div>
            </>
          )}

          {/* Divider */}
          <div className="border-t border-[var(--border)] mx-3" />

          {/* Live data section */}
          <div className="px-3 py-2">
            <div className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
              Live Data
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between py-1">
                <span className="text-xs text-[var(--text-secondary)]">Vehicles</span>
                <Toggle checked={showVehicles} onChange={onToggleVehicles} />
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-xs text-[var(--text-secondary)]">Traffic</span>
                <Toggle checked={showTraffic} onChange={onToggleTraffic} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
