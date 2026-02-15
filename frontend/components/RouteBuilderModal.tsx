"use client";

import { useEffect, useState } from "react";
import {
  X,
  Plus,
  Calculator,
  Loader2,
  AlertCircle,
  Route,
  Train,
  Car,
  Footprints,
  Clock,
  DollarSign,
  MapPin,
  ChevronLeft,
  Play,
  ChevronDown,
  ChevronUp,
  ArrowUp,
  CornerUpRight,
  CornerUpLeft,
  Navigation,
  Zap,
} from "lucide-react";
import type { Coordinate, RouteOption, RouteSegment, DirectionStep } from "@/lib/types";
import { useCustomRoute } from "@/hooks/useCustomRoute";
import SegmentEditor from "./SegmentEditor";
import DelayIndicator from "./DelayIndicator";

interface RouteBuilderModalProps {
  baseRoute: RouteOption | null;
  origin: Coordinate | null;
  destination: Coordinate | null;
  onClose: () => void;
  onRouteCalculated: (route: RouteOption) => void;
}

// --- Step-by-step route preview components ---

const SEGMENT_ICON: Record<string, React.ReactNode> = {
  transit: <Train className="w-3.5 h-3.5" />,
  driving: <Car className="w-3.5 h-3.5" />,
  walking: <Footprints className="w-3.5 h-3.5" />,
};

const SEGMENT_BAR_COLOR: Record<string, string> = {
  transit: "bg-yellow-500",
  driving: "bg-blue-500",
  walking: "bg-emerald-500",
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
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${colors[level] || ""}`}>
      {labels[level] || level}
    </span>
  );
}

function getStepIcon(type: string, modifier: string) {
  if (type === "arrive" || type === "destination") return <MapPin className="w-3 h-3" />;
  if (modifier?.includes("right")) return <CornerUpRight className="w-3 h-3" />;
  if (modifier?.includes("left")) return <CornerUpLeft className="w-3 h-3" />;
  if (type === "depart") return <Navigation className="w-3 h-3" />;
  return <ArrowUp className="w-3 h-3" />;
}

function InlineDirectionSteps({ steps }: { steps: DirectionStep[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!steps || steps.length === 0) return null;

  return (
    <>
      <button
        onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
        className="flex items-center gap-1 mt-1 text-[11px] text-blue-400 hover:text-blue-300"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? "Hide" : "Show"} {steps.length} directions
      </button>
      {expanded && (
        <div className="mt-1.5 space-y-1.5 max-h-40 overflow-y-auto pl-1">
          {steps.map((step, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <span className="mt-0.5 shrink-0 text-slate-500">
                {getStepIcon(step.maneuver_type, step.maneuver_modifier)}
              </span>
              <span className="flex-1 leading-relaxed">{step.instruction || "Continue"}</span>
              {step.distance_km > 0 && (
                <span className="shrink-0 text-slate-500">
                  {step.distance_km < 1
                    ? `${Math.round(step.distance_km * 1000)}m`
                    : `${step.distance_km.toFixed(1)}km`}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function RoutePreviewTimeline({ segments }: { segments: RouteSegment[] }) {
  return (
    <div className="space-y-0">
      {segments.map((seg, i) => {
        const hasSteps = seg.steps && seg.steps.length > 0;

        return (
          <div key={i} className="flex gap-3">
            {/* Timeline bar */}
            <div className="flex flex-col items-center">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-white ${SEGMENT_BAR_COLOR[seg.mode] || "bg-slate-500"}`}
                style={seg.color ? { backgroundColor: seg.color } : {}}
              >
                {SEGMENT_ICON[seg.mode] || <MapPin className="w-3 h-3" />}
              </div>
              {i < segments.length - 1 && (
                <div
                  className="w-0.5 flex-1 min-h-[20px]"
                  style={{ backgroundColor: seg.color || "#64748b", opacity: 0.4 }}
                />
              )}
            </div>

            {/* Segment details */}
            <div className="flex-1 pb-3 min-w-0">
              <div className="text-sm font-medium text-white">
                {seg.instructions || `${seg.mode} segment`}
              </div>
              <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {Math.round(seg.duration_min)} min
                </span>
                <span>
                  {seg.distance_km < 1
                    ? `${Math.round(seg.distance_km * 1000)}m`
                    : `${seg.distance_km.toFixed(1)} km`}
                </span>
                {seg.transit_line && (
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                    style={{ backgroundColor: `${seg.color}25`, color: seg.color }}
                  >
                    {seg.transit_line}
                  </span>
                )}
                {seg.congestion_level && <CongestionBadge level={seg.congestion_level} />}
              </div>
              {hasSteps && <InlineDirectionSteps steps={seg.steps!} />}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// --- Main Modal ---

export default function RouteBuilderModal({
  baseRoute: _baseRoute,
  origin,
  destination,
  onClose,
  onRouteCalculated,
}: RouteBuilderModalProps) {
  void _baseRoute; // Reserved for future pre-population
  const {
    segments,
    suggestions,
    suggestionsLoading,
    calculatedRoute,
    loading,
    error,
    addSegment,
    removeSegment,
    updateSegmentMode,
    selectSuggestion,
    selectTransferPair,
    clearSuggestion,
    clearCalculatedRoute,
    moveSegment,
    fetchSuggestions,
    calculate,
  } = useCustomRoute();

  // Track whether we're showing preview
  const showPreview = !!calculatedRoute;

  // Fetch suggestions once on modal open
  useEffect(() => {
    if (origin && destination) {
      fetchSuggestions(origin, destination);
    }
  }, [origin, destination, fetchSuggestions]);

  const canCalculate = segments.length > 0 && origin && destination;

  const handleCalculate = async () => {
    if (!origin || !destination) return;
    await calculate(origin, destination);
    // Don't call onRouteCalculated yet — show preview first
  };

  const handleGo = () => {
    if (calculatedRoute) {
      onRouteCalculated(calculatedRoute);
    }
  };

  const handleBackToEdit = () => {
    clearCalculatedRoute();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm backdrop-fade">
      <div className="glass-card max-w-2xl w-full mx-4 max-h-[85vh] flex flex-col border border-slate-700/50 modal-enter">
        {/* Gradient accent line */}
        <div className="h-[2px] w-full bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 rounded-t-xl" />

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700/30">
          <div className="flex items-center gap-3">
            {showPreview && (
              <button
                onClick={handleBackToEdit}
                className="p-1.5 text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-700/50"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            )}
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center">
              <Route className="w-4.5 h-4.5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">
                {showPreview ? "Route Preview" : "Customize Route"}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {showPreview
                  ? "Review your route step by step"
                  : "Combine transit, driving & walking segments"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-700/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {showPreview ? (
            /* ===== PREVIEW PHASE ===== */
            <div className="space-y-4 slide-up">
              {/* Stats row */}
              <div className="grid grid-cols-3 gap-2">
                <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <Clock className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-wide">ETA</div>
                    <div className="text-base font-bold text-white">
                      {Math.round(calculatedRoute.total_duration_min)} min
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <DollarSign className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-wide">Cost</div>
                    <div className="text-base font-bold text-white">
                      ${calculatedRoute.cost.total.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                  <MapPin className="w-4 h-4 text-purple-400 flex-shrink-0" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-wide">Dist</div>
                    <div className="text-base font-bold text-white">
                      {calculatedRoute.total_distance_km.toFixed(1)} km
                    </div>
                  </div>
                </div>
              </div>

              {/* Stress + delay summary */}
              <div className="flex items-center gap-3">
                {calculatedRoute.stress_score > 0 && (
                  <div className="flex items-center gap-1.5 text-xs">
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    <span className="text-slate-400">Stress:</span>
                    <span className={`font-medium ${
                      calculatedRoute.stress_score < 0.3 ? "text-emerald-400" :
                      calculatedRoute.stress_score < 0.6 ? "text-amber-400" : "text-red-400"
                    }`}>
                      {calculatedRoute.stress_score < 0.3 ? "Low" :
                       calculatedRoute.stress_score < 0.6 ? "Moderate" : "High"}
                    </span>
                  </div>
                )}
                {calculatedRoute.delay_info.probability > 0 && (
                  <DelayIndicator
                    probability={calculatedRoute.delay_info.probability}
                    expectedMinutes={calculatedRoute.delay_info.expected_minutes}
                    compact
                  />
                )}
              </div>

              {/* Segment mode bar — visual overview */}
              {calculatedRoute.segments.length > 1 && (
                <div className="flex gap-0.5 h-2 rounded-full overflow-hidden">
                  {calculatedRoute.segments.map((seg, i) => {
                    const pct = (seg.duration_min / calculatedRoute.total_duration_min) * 100;
                    return (
                      <div
                        key={i}
                        className="h-full rounded-sm"
                        style={{
                          width: `${Math.max(pct, 4)}%`,
                          backgroundColor: seg.color || (
                            seg.mode === "transit" ? "#EAB308" :
                            seg.mode === "driving" ? "#3B82F6" : "#10B981"
                          ),
                          opacity: 0.7,
                        }}
                        title={`${seg.instructions || seg.mode} — ${Math.round(seg.duration_min)} min`}
                      />
                    );
                  })}
                </div>
              )}

              {/* Divider */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                  Step-by-step
                </span>
                <div className="flex-1 h-px bg-slate-700/50" />
              </div>

              {/* Step-by-step timeline */}
              <RoutePreviewTimeline segments={calculatedRoute.segments} />

              {/* Delay details (if applicable) */}
              {calculatedRoute.delay_info.probability > 0 && (
                <div className="mt-2">
                  <DelayIndicator
                    probability={calculatedRoute.delay_info.probability}
                    expectedMinutes={calculatedRoute.delay_info.expected_minutes}
                    confidence={calculatedRoute.delay_info.confidence}
                    factors={calculatedRoute.delay_info.factors}
                  />
                </div>
              )}
            </div>
          ) : (
            /* ===== BUILD PHASE ===== */
            <>
              {segments.length === 0 && (
                <div className="text-center py-10">
                  <div className="flex items-center justify-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center">
                      <Train className="w-5 h-5 text-yellow-400" />
                    </div>
                    <div className="flex flex-col items-center gap-1">
                      <div className="flex gap-0.5">
                        <span className="w-1 h-1 rounded-full bg-slate-600" />
                        <span className="w-1 h-1 rounded-full bg-slate-600" />
                        <span className="w-1 h-1 rounded-full bg-slate-600" />
                      </div>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                      <Car className="w-5 h-5 text-blue-400" />
                    </div>
                    <div className="flex flex-col items-center gap-1">
                      <div className="flex gap-0.5">
                        <span className="w-1 h-1 rounded-full bg-slate-600" />
                        <span className="w-1 h-1 rounded-full bg-slate-600" />
                        <span className="w-1 h-1 rounded-full bg-slate-600" />
                      </div>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                      <Footprints className="w-5 h-5 text-emerald-400" />
                    </div>
                  </div>
                  <p className="text-sm text-slate-300 font-medium mb-1">Build your perfect route</p>
                  <p className="text-xs text-slate-500 max-w-xs mx-auto">
                    Add segments below to mix transit lines, driving, and walking into a single custom route.
                  </p>
                </div>
              )}

              {segments.map((seg, i) => (
                <div
                  key={seg.id}
                  className="stagger-in"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <SegmentEditor
                    segment={seg}
                    index={i}
                    total={segments.length}
                    suggestions={suggestions}
                    suggestionsLoading={suggestionsLoading}
                    onUpdateMode={updateSegmentMode}
                    onSelectSuggestion={selectSuggestion}
                    onSelectTransferPair={selectTransferPair}
                    onClearSuggestion={clearSuggestion}
                    onRemove={removeSegment}
                    onMove={moveSegment}
                  />
                </div>
              ))}

              {/* Add segment button */}
              <button
                onClick={addSegment}
                className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-slate-600/50 text-slate-400 text-sm hover:border-blue-500/50 hover:text-blue-400 hover:bg-blue-500/5 active:scale-[0.98] transition-all"
              >
                <Plus className="w-4 h-4" />
                Add Segment
              </button>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700/30">
          {error && (
            <div className="flex items-center gap-2 p-2.5 mb-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span className="text-xs text-red-400">{error}</span>
            </div>
          )}

          {showPreview ? (
            /* Preview phase: GO + Back buttons */
            <div className="flex gap-2">
              <button
                onClick={handleBackToEdit}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-slate-600/50 text-slate-300 text-sm font-medium hover:bg-slate-700/50 active:scale-[0.98] transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
                Edit
              </button>
              <button
                onClick={handleGo}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white text-sm font-semibold shadow-lg shadow-emerald-500/20 active:scale-[0.98] transition-all"
              >
                <Play className="w-4 h-4" />
                GO — Use This Route
              </button>
            </div>
          ) : (
            /* Build phase: Calculate button */
            <button
              onClick={handleCalculate}
              disabled={!canCalculate || loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium shadow-lg shadow-blue-500/20 active:scale-[0.98] transition-all"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Calculator className="w-4 h-4" />
              )}
              {loading ? "Calculating..." : "Calculate Route"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
