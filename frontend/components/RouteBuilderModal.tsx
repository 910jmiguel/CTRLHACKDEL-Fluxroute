"use client";

import { useEffect } from "react";
import { X, Plus, Calculator, Loader2, AlertCircle, Route, Train, Car, Footprints, Clock, DollarSign, MapPin } from "lucide-react";
import type { Coordinate, RouteOption } from "@/lib/types";
import { useCustomRoute } from "@/hooks/useCustomRoute";
import SegmentEditor from "./SegmentEditor";

interface RouteBuilderModalProps {
  baseRoute: RouteOption | null;
  origin: Coordinate | null;
  destination: Coordinate | null;
  onClose: () => void;
  onRouteCalculated: (route: RouteOption) => void;
}

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
    clearSuggestion,
    moveSegment,
    fetchSuggestions,
    calculate,
  } = useCustomRoute();

  // Fetch suggestions once on modal open
  useEffect(() => {
    if (origin && destination) {
      fetchSuggestions(origin, destination);
    }
  }, [origin, destination, fetchSuggestions]);

  const canCalculate = segments.length > 0 && origin && destination;

  const handleCalculate = async () => {
    if (!origin || !destination) return;
    const route = await calculate(origin, destination);
    if (route) {
      onRouteCalculated(route);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm backdrop-fade">
      <div className="glass-card max-w-2xl w-full mx-4 max-h-[85vh] flex flex-col border border-slate-700/50 modal-enter">
        {/* Gradient accent line */}
        <div className="h-[2px] w-full bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 rounded-t-xl" />

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700/30">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center">
              <Route className="w-4.5 h-4.5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Customize Route</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Combine transit, driving &amp; walking segments
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
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700/30">
          {error && (
            <div className="flex items-center gap-2 p-2.5 mb-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span className="text-xs text-red-400">{error}</span>
            </div>
          )}

          {calculatedRoute && (
            <div className="grid grid-cols-3 gap-2 mb-3 slide-up">
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <Clock className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wide">ETA</div>
                  <div className="text-sm font-semibold text-white">{Math.round(calculatedRoute.total_duration_min)} min</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <DollarSign className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wide">Cost</div>
                  <div className="text-sm font-semibold text-white">${calculatedRoute.cost.total.toFixed(2)}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <MapPin className="w-4 h-4 text-purple-400 flex-shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wide">Distance</div>
                  <div className="text-sm font-semibold text-white">{calculatedRoute.total_distance_km.toFixed(1)} km</div>
                </div>
              </div>
            </div>
          )}

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
        </div>
      </div>
    </div>
  );
}
