"use client";

import { useState } from "react";
import { X, AlertTriangle, Info, XCircle } from "lucide-react";
import Image from "next/image";
import type { ServiceAlert } from "@/lib/types";
import { useIsMobile } from "@/hooks/useMediaQuery";
import { TTC_LINE_ALERT_LOGOS, TTC_ALERT_LINE_IDS } from "@/lib/constants";

interface AlertsPanelProps {
  open: boolean;
  onClose: () => void;
  alerts: ServiceAlert[];
}

const SEVERITY_CONFIG = {
  info: {
    icon: Info,
    bar: "bg-blue-500",
    badge: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  },
  warning: {
    icon: AlertTriangle,
    bar: "bg-amber-500",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  error: {
    icon: XCircle,
    bar: "bg-red-500",
    badge: "bg-red-500/10 text-red-400 border-red-500/30",
  },
};

/**
 * Extract the TTC line ID from an alert's route_id or title.
 * Matches things like "Line 1", "line1", "1", route_id "1", etc.
 */
function extractLineId(alert: ServiceAlert): string | null {
  // Check route_id first
  if (alert.route_id) {
    const cleaned = alert.route_id.replace(/^line\s*/i, "").trim();
    if (TTC_ALERT_LINE_IDS.includes(cleaned)) return cleaned;
  }
  // Fallback: scan title for "Line X"
  const match = alert.title.match(/line\s*(\d)/i);
  if (match && TTC_ALERT_LINE_IDS.includes(match[1])) return match[1];
  return null;
}

function getAlertLogo(alert: ServiceAlert): string | null {
  const lineId = extractLineId(alert);
  if (!lineId) return null;
  const key = `${lineId}-${alert.severity}`;
  return TTC_LINE_ALERT_LOGOS[key] || null;
}

export default function AlertsPanel({ open, onClose, alerts }: AlertsPanelProps) {
  const isMobile = useIsMobile();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  if (!open) return null;

  const visibleAlerts = alerts.filter((a) => !dismissed.has(a.id));

  const dismissAlert = (id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 fade-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className={`fixed z-40 ${
          isMobile
            ? "inset-0 bg-[var(--background)]"
            : "top-0 right-0 h-full w-[380px] panel-glass shadow-2xl border-l border-[var(--glass-border)] slide-in-right"
        } flex flex-col`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h2 className="font-heading font-semibold text-sm text-[var(--text-primary)]">
              Service Alerts
            </h2>
            <span className="text-xs text-[var(--text-muted)]">
              {visibleAlerts.length}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            aria-label="Close alerts panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Alert list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {visibleAlerts.length === 0 && (
            <div className="text-center text-[var(--text-muted)] text-sm py-12">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No active alerts</p>
            </div>
          )}

          {visibleAlerts.map((alert, i) => {
            const config = SEVERITY_CONFIG[alert.severity];
            const Icon = config.icon;
            const alertLogo = getAlertLogo(alert);

            return (
              <div
                key={alert.id}
                className="glass-card overflow-hidden stagger-in"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                {/* Severity color bar */}
                <div className={`h-1 ${config.bar}`} />

                <div className="p-3">
                  <div className="flex items-start gap-3">
                    {/* Line alert logo or fallback severity icon */}
                    {alertLogo ? (
                      <Image
                        src={alertLogo}
                        alt={`Line ${extractLineId(alert)} ${alert.severity}`}
                        width={32}
                        height={32}
                        className="rounded-full flex-shrink-0 mt-0.5"
                      />
                    ) : (
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                        alert.severity === "error"
                          ? "bg-red-500/15"
                          : alert.severity === "warning"
                          ? "bg-amber-500/15"
                          : "bg-blue-500/15"
                      }`}>
                        <Icon className={`w-4 h-4 ${
                          alert.severity === "error"
                            ? "text-red-400"
                            : alert.severity === "warning"
                            ? "text-amber-400"
                            : "text-blue-400"
                        }`} />
                      </div>
                    )}

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-sm font-medium text-[var(--text-primary)]">
                          {alert.title}
                        </h3>
                        <button
                          onClick={() => dismissAlert(alert.id)}
                          className="p-1 rounded hover:bg-[var(--surface-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors flex-shrink-0"
                          aria-label="Dismiss alert"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mt-1">
                        {alert.description}
                      </p>
                      {alert.route_id && !alertLogo && (
                        <span className={`inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded-full border ${config.badge}`}>
                          Route {alert.route_id}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
