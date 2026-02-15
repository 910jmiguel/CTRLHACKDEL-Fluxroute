"use client";

import { X, Play, Wand2, ChevronLeft } from "lucide-react";
import type { RouteOption } from "@/lib/types";
import type { ModeFilter } from "@/hooks/useRoutes";
import { useIsMobile } from "@/hooks/useMediaQuery";
import { PANEL_WIDTH_DESKTOP, PANEL_WIDTH_TABLET } from "@/lib/constants";
import { useIsTablet } from "@/hooks/useMediaQuery";
import RoutePills from "./RoutePills";
import JourneyTimeline from "./JourneyTimeline";
import BottomSheet from "./BottomSheet";

interface RoutePanelProps {
  open: boolean;
  onClose: () => void;
  onOpen: () => void;
  routes: RouteOption[];
  filteredRoutes: RouteOption[];
  selectedRoute: RouteOption | null;
  onSelectRoute: (route: RouteOption) => void;
  activeFilter: ModeFilter;
  onFilterChange: (filter: ModeFilter) => void;
  onCustomize?: (route: RouteOption) => void;
  onStartNavigation?: () => void;
  isNavigating?: boolean;
  originLabel?: string;
  destinationLabel?: string;
  error?: string | null;
}

function PanelContent({
  routes,
  selectedRoute,
  onSelectRoute,
  activeFilter,
  onFilterChange,
  onCustomize,
  onStartNavigation,
  isNavigating,
  originLabel,
  destinationLabel,
  error,
}: Omit<RoutePanelProps, "open" | "onClose" | "onOpen" | "filteredRoutes">) {
  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">
          {error}
        </div>
      )}

      <RoutePills
        routes={routes}
        selectedRoute={selectedRoute}
        onSelect={onSelectRoute}
        activeFilter={activeFilter}
        onFilterChange={onFilterChange}
      />

      {/* Navigation button */}
      {routes.length > 0 && (
        <>
          {isNavigating ? (
            <div className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Navigation Active
            </div>
          ) : onStartNavigation ? (
            <button
              onClick={onStartNavigation}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold transition-all bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-900/20"
              aria-label="Start navigation"
            >
              <Play className="w-4 h-4" />
              GO
            </button>
          ) : null}
        </>
      )}

      {/* Journey timeline for selected route */}
      {selectedRoute && (
        <JourneyTimeline
          route={selectedRoute}
          originLabel={originLabel}
          destinationLabel={destinationLabel}
        />
      )}

      {/* Customize button */}
      {selectedRoute && onCustomize && (
        <button
          onClick={() => onCustomize(selectedRoute)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-[var(--border)] text-[var(--text-secondary)] text-sm hover:border-[var(--accent)] hover:text-[var(--accent)] hover:bg-[var(--surface-hover)] transition-all"
        >
          <Wand2 className="w-4 h-4" />
          Customize Route
        </button>
      )}

      {routes.length === 0 && !error && (
        <div className="text-center text-[var(--text-muted)] text-sm py-8">
          <p>Enter origin and destination to compare routes.</p>
        </div>
      )}
    </div>
  );
}

export default function RoutePanel(props: RoutePanelProps) {
  const { open, onClose, onOpen, routes } = props;
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();

  // Mobile: when closed, fully unmount (no reopen tab)
  if (!open && isMobile) return null;

  // Desktop: when closed, show a reopen tab if there are routes
  if (!open) {
    if (routes.length === 0) return null;
    return (
      <button
        onClick={onOpen}
        className="absolute top-16 right-0 z-30 panel-glass rounded-l-lg px-2 py-3 hover:bg-[var(--surface-hover)] transition-colors text-[var(--text-secondary)] hover:text-[var(--text-primary)] shadow-lg border-l border-y border-[var(--glass-border)]"
        aria-label="Open route panel"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
    );
  }

  // Mobile: bottom sheet
  if (isMobile) {
    return (
      <BottomSheet onClose={onClose}>
        <div className="px-4 pb-6">
          <PanelContent {...props} />
        </div>
      </BottomSheet>
    );
  }

  // Desktop / Tablet: slide-over panel
  const panelWidth = isTablet ? PANEL_WIDTH_TABLET : PANEL_WIDTH_DESKTOP;

  return (
    <div
      className="absolute top-0 right-0 h-full z-30 slide-in-right"
      style={{ width: panelWidth }}
    >
      <div className="h-full panel-glass flex flex-col shadow-2xl border-l border-[var(--glass-border)]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <h2 className="font-heading font-semibold text-sm text-[var(--text-primary)]">
            Routes
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            aria-label="Close route panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-4">
          <PanelContent {...props} />
        </div>
      </div>
    </div>
  );
}
