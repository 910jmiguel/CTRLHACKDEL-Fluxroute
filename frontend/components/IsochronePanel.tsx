"use client";

import React, { useState, useCallback } from "react";
import { MapPin, Clock, Car, PersonStanding, Bike, Loader2 } from "lucide-react";
import { getIsochrone } from "@/lib/api";
import type { Coordinate, IsochroneResponse } from "@/lib/types";

interface IsochronePanelProps {
  center: Coordinate | null;
  onIsochroneLoaded: (data: IsochroneResponse) => void;
  onClear: () => void;
}

const PROFILES = [
  { id: "driving", label: "Drive", icon: Car },
  { id: "walking", label: "Walk", icon: PersonStanding },
  { id: "cycling", label: "Bike", icon: Bike },
] as const;

const PRESETS = [
  { minutes: [5, 10, 15], label: "5/10/15 min" },
  { minutes: [10, 20, 30], label: "10/20/30 min" },
  { minutes: [15, 30, 45], label: "15/30/45 min" },
];

export default function IsochronePanel({
  center,
  onIsochroneLoaded,
  onClear,
}: IsochronePanelProps) {
  const [profile, setProfile] = useState("driving");
  const [contours, setContours] = useState<number[]>([10, 20, 30]);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(false);

  const fetchIsochrone = useCallback(async () => {
    if (!center) return;

    setLoading(true);
    try {
      const data = await getIsochrone({
        center,
        profile,
        contours_minutes: contours,
        polygons: true,
      });
      onIsochroneLoaded(data);
      setActive(true);
    } catch (err) {
      console.error("Isochrone fetch failed:", err);
    } finally {
      setLoading(false);
    }
  }, [center, profile, contours, onIsochroneLoaded]);

  const handleClear = () => {
    setActive(false);
    onClear();
  };

  return (
    <div className="bg-white/5 backdrop-blur-md rounded-xl border border-white/10 p-4">
      <div className="flex items-center gap-2 mb-3">
        <MapPin className="w-4 h-4 text-emerald-400" />
        <h3 className="text-sm font-semibold text-slate-200">Reachability</h3>
      </div>

      {!center && (
        <p className="text-xs text-slate-400">
          Set an origin point to see how far you can travel.
        </p>
      )}

      {center && (
        <>
          {/* Profile selector */}
          <div className="flex gap-1 mb-3">
            {PROFILES.map((p) => (
              <button
                key={p.id}
                onClick={() => setProfile(p.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  profile === p.id
                    ? "bg-blue-500/30 text-blue-300 border border-blue-400/30"
                    : "bg-slate-700/40 text-slate-400 hover:bg-slate-700/60"
                }`}
              >
                <p.icon className="w-3.5 h-3.5" />
                {p.label}
              </button>
            ))}
          </div>

          {/* Time presets */}
          <div className="flex gap-1 mb-3">
            {PRESETS.map((preset) => (
              <button
                key={preset.label}
                onClick={() => setContours(preset.minutes)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                  JSON.stringify(contours) === JSON.stringify(preset.minutes)
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-400/30"
                    : "bg-slate-700/40 text-slate-400 hover:bg-slate-700/60"
                }`}
              >
                <Clock className="w-3 h-3" />
                {preset.label}
              </button>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              onClick={fetchIsochrone}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <MapPin className="w-4 h-4" />
              )}
              {loading ? "Loading..." : "Show Reachability"}
            </button>

            {active && (
              <button
                onClick={handleClear}
                className="px-3 py-2 bg-slate-700/60 hover:bg-slate-700/80 text-slate-300 text-sm rounded-lg transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
