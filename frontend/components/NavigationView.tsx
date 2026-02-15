"use client";

import React from "react";
import {
  Navigation,
  Clock,
  Gauge,
  X,
  ArrowUp,
  ArrowUpRight,
  ArrowRight,
  ArrowDownRight,
  RotateCcw,
  ArrowUpLeft,
  ArrowLeft,
  ArrowDownLeft,
  Volume2,
  VolumeX,
  MapPin,
} from "lucide-react";

interface NavigationViewProps {
  isNavigating: boolean;
  currentInstruction: string | null;
  nextInstruction: string | null;
  stepIndex: number;
  totalSteps: number;
  remainingDistanceKm: number;
  totalDistanceKm: number;
  remainingDurationMin: number;
  eta: string | null;
  speedLimit: number | null;
  voiceMuted: boolean;
  laneGuidance?: Array<{
    indications: string[];
    valid: boolean;
    active?: boolean;
  }>;
  onStopNavigation: () => void;
  onToggleVoice: () => void;
}

const MANEUVER_ICONS: Record<string, React.ReactNode> = {
  "turn right": <ArrowRight className="w-8 h-8" />,
  "turn left": <ArrowLeft className="w-8 h-8" />,
  "slight right": <ArrowUpRight className="w-8 h-8" />,
  "slight left": <ArrowUpLeft className="w-8 h-8" />,
  "sharp right": <ArrowDownRight className="w-8 h-8" />,
  "sharp left": <ArrowDownLeft className="w-8 h-8" />,
  "u-turn": <RotateCcw className="w-8 h-8" />,
  straight: <ArrowUp className="w-8 h-8" />,
  arrive: <MapPin className="w-8 h-8" />,
  destination: <MapPin className="w-8 h-8" />,
};

const LANE_ICONS: Record<string, React.ReactNode> = {
  left: <ArrowLeft className="w-4 h-4" />,
  "slight left": <ArrowUpLeft className="w-4 h-4" />,
  straight: <ArrowUp className="w-4 h-4" />,
  right: <ArrowRight className="w-4 h-4" />,
  "slight right": <ArrowUpRight className="w-4 h-4" />,
  "sharp left": <ArrowDownLeft className="w-4 h-4" />,
  "sharp right": <ArrowDownRight className="w-4 h-4" />,
  uturn: <RotateCcw className="w-4 h-4" />,
};

function getManeuverIcon(instruction: string): React.ReactNode {
  const lower = instruction.toLowerCase();
  for (const [key, icon] of Object.entries(MANEUVER_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return <ArrowUp className="w-8 h-8" />;
}

function getLaneIcon(indication: string): React.ReactNode {
  return LANE_ICONS[indication] || <ArrowUp className="w-4 h-4" />;
}

function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(1)} km`;
}

function formatDuration(min: number): string {
  if (min < 1) return "< 1 min";
  if (min < 60) return `${Math.round(min)} min`;
  const hours = Math.floor(min / 60);
  const mins = Math.round(min % 60);
  return `${hours}h ${mins}m`;
}

export default function NavigationView({
  isNavigating,
  currentInstruction,
  nextInstruction,
  stepIndex,
  totalSteps,
  remainingDistanceKm,
  totalDistanceKm,
  remainingDurationMin,
  eta,
  speedLimit,
  voiceMuted,
  laneGuidance,
  onStopNavigation,
  onToggleVoice,
}: NavigationViewProps) {
  if (!isNavigating) return null;

  const progressPct = totalDistanceKm > 0
    ? Math.min(100, Math.max(0, ((totalDistanceKm - remainingDistanceKm) / totalDistanceKm) * 100))
    : 0;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 pointer-events-none">
      <div className="pointer-events-auto mx-auto max-w-lg mt-4 px-2">
        <div className="bg-slate-900/95 backdrop-blur-md rounded-xl shadow-2xl border border-slate-700/50 overflow-hidden">

          {/* Progress bar */}
          <div className="h-1 bg-slate-800">
            <div
              className="h-full bg-emerald-500 transition-all duration-700 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Main instruction */}
          <div className="flex items-center gap-4 p-4">
            <div className="flex-shrink-0 w-14 h-14 bg-blue-600 rounded-lg flex items-center justify-center text-white">
              {currentInstruction
                ? getManeuverIcon(currentInstruction)
                : <Navigation className="w-8 h-8" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-lg font-semibold leading-tight line-clamp-2">
                {currentInstruction || "Navigating..."}
              </p>
              <p className="text-slate-400 text-sm mt-0.5">
                Step {stepIndex + 1} of {totalSteps}
              </p>
            </div>
            <div className="flex flex-col gap-2 flex-shrink-0">
              <button
                onClick={onToggleVoice}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                  voiceMuted
                    ? "bg-slate-700/60 hover:bg-slate-600/60"
                    : "bg-blue-500/20 hover:bg-blue-500/40"
                }`}
                title={voiceMuted ? "Unmute voice" : "Mute voice"}
              >
                {voiceMuted
                  ? <VolumeX className="w-4 h-4 text-slate-400" />
                  : <Volume2 className="w-4 h-4 text-blue-400" />}
              </button>
              <button
                onClick={onStopNavigation}
                className="w-9 h-9 bg-red-500/20 hover:bg-red-500/40 rounded-full flex items-center justify-center transition-colors"
                title="Stop navigation"
              >
                <X className="w-4 h-4 text-red-400" />
              </button>
            </div>
          </div>

          {/* Next instruction preview */}
          {nextInstruction && (
            <div className="flex items-center gap-3 px-4 pb-3">
              <div className="flex-shrink-0 w-8 h-8 bg-slate-700/60 rounded flex items-center justify-center text-slate-400">
                {getManeuverIcon(nextInstruction)}
              </div>
              <p className="text-slate-400 text-sm truncate">
                Then: {nextInstruction}
              </p>
            </div>
          )}

          {/* Lane guidance */}
          {laneGuidance && laneGuidance.length > 0 && (
            <div className="flex items-center justify-center gap-1 px-4 pb-3">
              {laneGuidance.map((lane, i) => {
                const isHighlighted = lane.valid || lane.active;
                return (
                  <div
                    key={i}
                    className={`w-9 h-9 rounded flex items-center justify-center ${
                      isHighlighted
                        ? "bg-blue-500/30 text-blue-300 border border-blue-400/50"
                        : "bg-slate-700/50 text-slate-500 border border-slate-600/30"
                    }`}
                  >
                    {lane.indications?.[0]
                      ? getLaneIcon(lane.indications[0])
                      : <ArrowUp className="w-4 h-4" />}
                  </div>
                );
              })}
            </div>
          )}

          {/* Bottom bar: ETA, distance, speed limit */}
          <div className="flex items-center justify-between bg-slate-800/80 px-4 py-3">
            <div className="flex items-center gap-2 text-emerald-400">
              <Clock className="w-4 h-4" />
              <span className="text-sm font-medium">
                {eta ? `ETA ${eta}` : formatDuration(remainingDurationMin)}
              </span>
            </div>

            <div className="text-slate-300 text-sm font-medium">
              {formatDistance(remainingDistanceKm)} left
            </div>

            {speedLimit ? (
              <div className="flex items-center gap-1.5">
                <div className="w-8 h-8 rounded-full border-2 border-red-500 flex items-center justify-center bg-white">
                  <span className="text-xs font-bold text-black">
                    {Math.round(speedLimit)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-slate-400">
                <Gauge className="w-4 h-4" />
                <span className="text-sm">{formatDistance(totalDistanceKm - remainingDistanceKm)}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
