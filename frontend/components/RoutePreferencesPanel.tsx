"use client";

import { useState } from "react";
import { SlidersHorizontal, ChevronDown } from "lucide-react";

export interface RoutePreferencesState {
  allowedAgencies: Record<string, boolean>;
  maxDriveRadiusKm: number;
}

interface RoutePreferencesPanelProps {
  preferences: RoutePreferencesState;
  onChange: (prefs: RoutePreferencesState) => void;
}

const AGENCIES: { key: string; label: string; color: string }[] = [
  { key: "TTC", label: "TTC", color: "#DA291C" },
  { key: "GO Transit", label: "GO Transit", color: "#3D8B37" },
  { key: "YRT", label: "YRT", color: "#0072CE" },
  { key: "MiWay", label: "MiWay", color: "#F7941D" },
];

export default function RoutePreferencesPanel({
  preferences,
  onChange,
}: RoutePreferencesPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const enabledCount = Object.values(preferences.allowedAgencies).filter(Boolean).length;

  const handleToggleAgency = (key: string) => {
    const current = preferences.allowedAgencies[key];
    // Prevent unchecking the last agency
    if (current && enabledCount <= 1) return;

    onChange({
      ...preferences,
      allowedAgencies: {
        ...preferences.allowedAgencies,
        [key]: !current,
      },
    });
  };

  const handleRadiusChange = (value: number) => {
    onChange({
      ...preferences,
      maxDriveRadiusKm: value,
    });
  };

  return (
    <div>
      {!expanded ? (
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg panel-glass text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shadow-lg"
          aria-label="Open route preferences"
        >
          <SlidersHorizontal className="w-4 h-4" />
          <span className="text-sm font-medium">Preferences</span>
        </button>
      ) : (
        <div className="w-64 rounded-lg panel-glass shadow-xl">
          {/* Header */}
          <button
            onClick={() => setExpanded(false)}
            className="w-full flex items-center justify-between px-3 py-2.5 text-[var(--text-primary)] hover:bg-[var(--surface-hover)] transition-colors rounded-t-lg"
          >
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4" />
              <span className="text-sm font-semibold">Preferences</span>
            </div>
            <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
          </button>

          {/* Agencies section */}
          <div className="px-3 pb-2">
            <div className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
              Transit Agencies
            </div>
            <div className="space-y-1">
              {AGENCIES.map(({ key, label, color }) => (
                <label
                  key={key}
                  className="flex items-center justify-between py-1 cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs text-[var(--text-secondary)]">{label}</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.allowedAgencies[key] ?? true}
                    onChange={() => handleToggleAgency(key)}
                    className="w-4 h-4 rounded border-[var(--border)] text-blue-500 focus:ring-blue-500 focus:ring-offset-0 bg-transparent cursor-pointer accent-blue-500"
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-[var(--border)] mx-3" />

          {/* Driving radius section */}
          <div className="px-3 py-2">
            <div className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
              Park &amp; Ride Radius
            </div>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={5}
                max={25}
                step={1}
                value={preferences.maxDriveRadiusKm}
                onChange={(e) => handleRadiusChange(Number(e.target.value))}
                className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer accent-blue-500"
                style={{
                  background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${((preferences.maxDriveRadiusKm - 5) / 20) * 100}%, var(--text-muted) ${((preferences.maxDriveRadiusKm - 5) / 20) * 100}%, var(--text-muted) 100%)`,
                }}
              />
              <span className="text-xs text-[var(--text-secondary)] w-10 text-right tabular-nums">
                {preferences.maxDriveRadiusKm} km
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-[var(--text-muted)] mt-0.5">
              <span>5 km</span>
              <span>25 km</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
