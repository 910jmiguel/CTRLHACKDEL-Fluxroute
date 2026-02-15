"use client";

import { X, Plus, Calculator, Loader2 } from "lucide-react";
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
    calculatedRoute,
    loading,
    error,
    addSegment,
    removeSegment,
    updateSegment,
    moveSegment,
    fetchLineStops,
    calculate,
  } = useCustomRoute();

  const canCalculate = segments.length > 0 && origin && destination;

  const handleCalculate = async () => {
    if (!origin || !destination) return;
    const route = await calculate(origin, destination);
    if (route) {
      onRouteCalculated(route);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-card max-w-2xl w-full mx-4 max-h-[85vh] flex flex-col border border-slate-700/50">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700/30">
          <div>
            <h2 className="text-lg font-semibold text-white">Customize Route</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Build your own route by combining transit lines and driving/walking segments
            </p>
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
            <div className="text-center text-slate-400 py-8">
              <p className="text-sm mb-2">No segments yet</p>
              <p className="text-xs text-slate-500">
                Add segments to build your custom route. Transit segments let you pick specific TTC lines and stations.
              </p>
            </div>
          )}

          {segments.map((seg, i) => (
            <SegmentEditor
              key={seg.id}
              segment={seg}
              index={i}
              total={segments.length}
              onUpdate={updateSegment}
              onRemove={removeSegment}
              onMove={moveSegment}
              onFetchLine={fetchLineStops}
            />
          ))}

          {/* Add segment button */}
          <button
            onClick={addSegment}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-slate-600/50 text-slate-400 text-sm hover:border-blue-500/50 hover:text-blue-400 transition-all"
          >
            <Plus className="w-4 h-4" />
            Add Segment
          </button>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700/30">
          {error && (
            <div className="text-xs text-red-400 mb-2">{error}</div>
          )}

          {calculatedRoute && (
            <div className="flex items-center gap-4 mb-3 text-sm">
              <span className="text-slate-400">
                ETA: <span className="text-white font-semibold">{Math.round(calculatedRoute.total_duration_min)} min</span>
              </span>
              <span className="text-slate-400">
                Cost: <span className="text-white font-semibold">${calculatedRoute.cost.total.toFixed(2)}</span>
              </span>
              <span className="text-slate-400">
                Distance: <span className="text-white font-semibold">{calculatedRoute.total_distance_km.toFixed(1)} km</span>
              </span>
            </div>
          )}

          <button
            onClick={handleCalculate}
            disabled={!canCalculate || loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-all"
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
