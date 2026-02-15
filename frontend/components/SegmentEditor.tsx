"use client";

import { Car, Footprints, Train, Bus, X, ChevronUp, ChevronDown, Check, ArrowRightLeft } from "lucide-react";
import type { TransitRouteSuggestion, CustomSegmentV2 } from "@/lib/types";
import { useMemo } from "react";

interface SegmentEditorProps {
  segment: CustomSegmentV2;
  index: number;
  total: number;
  suggestions: TransitRouteSuggestion[];
  suggestionsLoading: boolean;
  onUpdateMode: (id: string, mode: "driving" | "walking" | "transit") => void;
  onSelectSuggestion: (segId: string, suggestion: TransitRouteSuggestion) => void;
  onSelectTransferPair: (segId: string, leg1: TransitRouteSuggestion, leg2: TransitRouteSuggestion) => void;
  onClearSuggestion: (segId: string) => void;
  onRemove: (id: string) => void;
  onMove: (id: string, direction: "up" | "down") => void;
}

const MODE_OPTIONS = [
  { value: "driving" as const, label: "Drive", icon: <Car className="w-3.5 h-3.5" /> },
  { value: "walking" as const, label: "Walk", icon: <Footprints className="w-3.5 h-3.5" /> },
  { value: "transit" as const, label: "Transit", icon: <Train className="w-3.5 h-3.5" /> },
];

function ModeIcon({ mode }: { mode: string }) {
  switch (mode) {
    case "SUBWAY":
    case "RAIL":
      return <Train className="w-4 h-4" />;
    case "BUS":
      return <Bus className="w-4 h-4" />;
    case "TRAM":
      return <Train className="w-4 h-4" />;
    default:
      return <Train className="w-4 h-4" />;
  }
}

function SuggestionCard({
  suggestion,
  isSelected,
  onSelect,
}: {
  suggestion: TransitRouteSuggestion;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-2.5 rounded-lg border transition-all ${
        isSelected
          ? "border-blue-500/60 bg-blue-500/10"
          : "border-slate-700/40 bg-slate-800/40 hover:border-slate-600/60 hover:bg-slate-800/60"
      }`}
    >
      <div className="flex items-start gap-2.5">
        {/* Color dot + mode icon */}
        <div
          className="flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center mt-0.5"
          style={{ backgroundColor: `${suggestion.color}20`, color: suggestion.color }}
        >
          <ModeIcon mode={suggestion.transit_mode} />
        </div>

        {/* Route info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-bold px-1.5 py-0.5 rounded"
              style={{ backgroundColor: `${suggestion.color}25`, color: suggestion.color }}
            >
              {suggestion.display_name}
            </span>
            <span className="text-[10px] text-slate-500">{suggestion.direction_hint}</span>
            {isSelected && <Check className="w-3.5 h-3.5 text-blue-400 ml-auto flex-shrink-0" />}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 truncate">
            {suggestion.board_stop_name} → {suggestion.alight_stop_name}
          </div>
          <div className="flex items-center gap-3 mt-1">
            {suggestion.estimated_duration_min > 0 && (
              <span className="text-[10px] text-slate-500">
                ~{Math.round(suggestion.estimated_duration_min)} min
              </span>
            )}
            {suggestion.estimated_distance_km > 0 && (
              <span className="text-[10px] text-slate-500">
                {suggestion.estimated_distance_km.toFixed(1)} km
              </span>
            )}
            <span className="text-[10px] text-slate-600">{suggestion.transit_mode.toLowerCase()}</span>
          </div>
        </div>
      </div>
    </button>
  );
}

function TransferSuggestionCard({
  leg1,
  leg2,
  onSelect,
}: {
  leg1: TransitRouteSuggestion;
  leg2: TransitRouteSuggestion;
  onSelect: () => void;
}) {
  const totalDuration = Math.round(leg1.estimated_duration_min + leg2.estimated_duration_min + 3); // +3 min transfer
  const totalDistance = leg1.estimated_distance_km + leg2.estimated_distance_km;

  return (
    <button
      onClick={onSelect}
      className="w-full text-left p-2.5 rounded-lg border border-slate-700/40 bg-slate-800/40 hover:border-purple-500/50 hover:bg-slate-800/60 transition-all"
    >
      {/* Leg 1 */}
      <div className="flex items-center gap-2">
        <div
          className="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center"
          style={{ backgroundColor: `${leg1.color}20`, color: leg1.color }}
        >
          <ModeIcon mode={leg1.transit_mode} />
        </div>
        <span
          className="text-[11px] font-bold px-1.5 py-0.5 rounded"
          style={{ backgroundColor: `${leg1.color}25`, color: leg1.color }}
        >
          {leg1.display_name}
        </span>
        <span className="text-[10px] text-slate-500 truncate">
          {leg1.board_stop_name} → {leg1.alight_stop_name}
        </span>
      </div>

      {/* Transfer indicator */}
      <div className="flex items-center gap-2 my-1.5 pl-2">
        <ArrowRightLeft className="w-3 h-3 text-purple-400 flex-shrink-0" />
        <span className="text-[10px] text-purple-400 font-medium">
          Transfer at {leg1.transfer_station_name}
        </span>
      </div>

      {/* Leg 2 */}
      <div className="flex items-center gap-2">
        <div
          className="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center"
          style={{ backgroundColor: `${leg2.color}20`, color: leg2.color }}
        >
          <ModeIcon mode={leg2.transit_mode} />
        </div>
        <span
          className="text-[11px] font-bold px-1.5 py-0.5 rounded"
          style={{ backgroundColor: `${leg2.color}25`, color: leg2.color }}
        >
          {leg2.display_name}
        </span>
        <span className="text-[10px] text-slate-500 truncate">
          {leg2.board_stop_name} → {leg2.alight_stop_name}
        </span>
      </div>

      {/* Total stats */}
      <div className="flex items-center gap-3 mt-1.5 pl-2">
        <span className="text-[10px] text-slate-500">~{totalDuration} min total</span>
        <span className="text-[10px] text-slate-500">{totalDistance.toFixed(1)} km</span>
        <span className="text-[10px] text-purple-400/70">1 transfer</span>
      </div>
    </button>
  );
}

function SelectedRouteCard({
  suggestion,
  onClear,
}: {
  suggestion: TransitRouteSuggestion;
  onClear: () => void;
}) {
  return (
    <div className="flex items-center gap-2.5 p-2.5 rounded-lg border border-blue-500/40 bg-blue-500/10">
      <div
        className="flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center"
        style={{ backgroundColor: `${suggestion.color}25`, color: suggestion.color }}
      >
        <ModeIcon mode={suggestion.transit_mode} />
      </div>
      <div className="flex-1 min-w-0">
        <span
          className="text-xs font-bold px-1.5 py-0.5 rounded"
          style={{ backgroundColor: `${suggestion.color}25`, color: suggestion.color }}
        >
          {suggestion.display_name}
        </span>
        <div className="text-[11px] text-slate-400 mt-0.5 truncate">
          {suggestion.board_stop_name} → {suggestion.alight_stop_name}
        </div>
      </div>
      <button
        onClick={onClear}
        className="p-1 text-slate-500 hover:text-red-400 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export default function SegmentEditor({
  segment,
  index,
  total,
  suggestions,
  suggestionsLoading,
  onUpdateMode,
  onSelectSuggestion,
  onSelectTransferPair,
  onClearSuggestion,
  onRemove,
  onMove,
}: SegmentEditorProps) {
  // Separate direct suggestions from transfer groups
  const { directSuggestions, transferGroups } = useMemo(() => {
    const direct: TransitRouteSuggestion[] = [];
    const groupMap = new Map<string, TransitRouteSuggestion[]>();

    for (const s of suggestions) {
      if (s.transfer_group_id) {
        const existing = groupMap.get(s.transfer_group_id) || [];
        existing.push(s);
        groupMap.set(s.transfer_group_id, existing);
      } else {
        direct.push(s);
      }
    }

    // Only keep complete pairs (leg 1 + leg 2)
    const groups: Array<{ leg1: TransitRouteSuggestion; leg2: TransitRouteSuggestion }> = [];
    for (const legs of groupMap.values()) {
      const leg1 = legs.find((l) => l.transfer_sequence === 1);
      const leg2 = legs.find((l) => l.transfer_sequence === 2);
      if (leg1 && leg2) {
        groups.push({ leg1, leg2 });
      }
    }

    return { directSuggestions: direct, transferGroups: groups };
  }, [suggestions]);

  return (
    <div className="glass-card p-3 border border-slate-700/40 hover:border-slate-600/60 transition-colors">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="segment-badge w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white">
            {index + 1}
          </span>
          <span className="text-xs text-slate-300 font-medium">
            {segment.selectedSuggestion
              ? segment.selectedSuggestion.display_name
              : segment.mode === "driving"
                ? "Drive"
                : segment.mode === "walking"
                  ? "Walk"
                  : "Transit"}
          </span>
        </div>
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
            onClick={() => onUpdateMode(segment.id, opt.value)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium duration-200 transition-all ${
              segment.mode === opt.value
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/40 shadow-sm shadow-blue-500/10"
                : "bg-slate-800/50 text-slate-400 border border-transparent hover:bg-slate-700/50"
            }`}
          >
            {opt.icon}
            {opt.label}
          </button>
        ))}
      </div>

      {/* Transit: suggestion cards */}
      {segment.mode === "transit" && (
        <div className="space-y-2">
          {segment.selectedSuggestion ? (
            <SelectedRouteCard
              suggestion={segment.selectedSuggestion}
              onClear={() => onClearSuggestion(segment.id)}
            />
          ) : (
            <>
              {suggestionsLoading && (
                <div className="text-xs text-slate-500 text-center py-3">
                  Loading transit routes...
                </div>
              )}
              {!suggestionsLoading && suggestions.length === 0 && (
                <div className="text-xs text-slate-500 text-center py-3">
                  No transit routes found for this trip.
                </div>
              )}
              {!suggestionsLoading && (directSuggestions.length > 0 || transferGroups.length > 0) && (
                <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
                  {/* Direct routes */}
                  {directSuggestions.map((s) => (
                    <SuggestionCard
                      key={s.suggestion_id}
                      suggestion={s}
                      isSelected={false}
                      onSelect={() => onSelectSuggestion(segment.id, s)}
                    />
                  ))}

                  {/* Transfer routes */}
                  {transferGroups.length > 0 && (
                    <>
                      <div className="flex items-center gap-2 pt-2 pb-1">
                        <ArrowRightLeft className="w-3 h-3 text-purple-400" />
                        <span className="text-[10px] font-medium text-purple-400 uppercase tracking-wider">
                          Transfer Routes
                        </span>
                        <div className="flex-1 h-px bg-slate-700/50" />
                      </div>
                      {transferGroups.map(({ leg1, leg2 }) => (
                        <TransferSuggestionCard
                          key={leg1.transfer_group_id}
                          leg1={leg1}
                          leg2={leg2}
                          onSelect={() => onSelectTransferPair(segment.id, leg1, leg2)}
                        />
                      ))}
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Drive/Walk info */}
      {segment.mode !== "transit" && (
        <div className="flex items-center gap-2 px-2.5 py-2 rounded-md bg-slate-800/40 text-xs text-slate-400">
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${segment.mode === "driving" ? "bg-blue-400" : "bg-emerald-400"}`} />
          <span>
            {segment.mode === "driving" ? "Drive" : "Walk"} from{" "}
            <span className="text-slate-300">{index === 0 ? "origin" : "prev segment"}</span> to{" "}
            <span className="text-slate-300">{index === total - 1 ? "destination" : "next segment"}</span>
          </span>
        </div>
      )}
    </div>
  );
}
