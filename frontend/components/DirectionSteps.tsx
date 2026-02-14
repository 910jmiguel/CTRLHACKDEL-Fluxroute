"use client";

import { useState } from "react";
import {
  ArrowUp,
  CornerUpRight,
  CornerUpLeft,
  MapPin,
  Navigation,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type { DirectionStep } from "@/lib/types";

interface DirectionStepsProps {
  steps: DirectionStep[];
}

function getStepIcon(type: string, modifier: string) {
  if (type === "arrive" || type === "destination") return <MapPin className="w-3.5 h-3.5" />;
  if (modifier === "right" || modifier === "slight right" || modifier === "sharp right")
    return <CornerUpRight className="w-3.5 h-3.5" />;
  if (modifier === "left" || modifier === "slight left" || modifier === "sharp left")
    return <CornerUpLeft className="w-3.5 h-3.5" />;
  if (type === "depart") return <Navigation className="w-3.5 h-3.5" />;
  return <ArrowUp className="w-3.5 h-3.5" />;
}

export default function DirectionSteps({ steps }: DirectionStepsProps) {
  const [expanded, setExpanded] = useState(false);

  if (steps.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? "Hide" : "Show"} {steps.length} directions
      </button>

      {expanded && (
        <div
          className="mt-2 space-y-1.5 max-h-48 overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {steps.map((step, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-xs text-[var(--text-secondary)]"
            >
              <span className="mt-0.5 shrink-0 text-[var(--text-muted)]">
                {getStepIcon(step.maneuver_type, step.maneuver_modifier)}
              </span>
              <span className="flex-1 leading-relaxed">
                {step.instruction || "Continue"}
              </span>
              {step.distance_km > 0 && (
                <span className="shrink-0 text-[var(--text-muted)]">
                  {step.distance_km < 1
                    ? `${Math.round(step.distance_km * 1000)}m`
                    : `${step.distance_km.toFixed(1)}km`}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
