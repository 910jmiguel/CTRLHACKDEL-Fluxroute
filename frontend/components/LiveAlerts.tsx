"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Info, XCircle, X, ChevronUp, ChevronDown } from "lucide-react";
import type { ServiceAlert } from "@/lib/types";
import { getAlerts } from "@/lib/api";

type AlertState = "expanded" | "collapsed" | "dismissed";

export default function LiveAlerts() {
  const [alerts, setAlerts] = useState<ServiceAlert[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [state, setState] = useState<AlertState>("expanded");

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await getAlerts();
        setAlerts(data.alerts || []);
      } catch {
        // Silent fail
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setCurrentIdx((prev) => Math.min(prev, Math.max(0, alerts.length - 1)));
  }, [alerts]);

  // Rotate through alerts
  useEffect(() => {
    if (alerts.length <= 1) return;
    const interval = setInterval(() => {
      setCurrentIdx((prev) => (prev + 1) % alerts.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [alerts.length]);

  if (alerts.length === 0) return null;

  const alert = alerts[currentIdx];
  if (!alert) return null;

  const Icon =
    alert.severity === "error"
      ? XCircle
      : alert.severity === "warning"
      ? AlertTriangle
      : Info;

  const severityColors = {
    info: "border-blue-500/30 bg-blue-500/10 text-blue-300",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    error: "border-red-500/30 bg-red-500/10 text-red-300",
  };

  // Dismissed: floating badge in top-right
  if (state === "dismissed") {
    return (
      <button
        onClick={() => setState("expanded")}
        className="fixed top-3 right-14 z-50 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-medium hover:bg-amber-500/30 transition-colors shadow-lg backdrop-blur-md"
      >
        <AlertTriangle className="w-3 h-3" />
        {alerts.length} alert{alerts.length !== 1 ? "s" : ""}
      </button>
    );
  }

  // Collapsed: thin bar
  if (state === "collapsed") {
    return (
      <div
        className={`w-full px-4 py-1 border-b flex items-center gap-2 text-xs ${severityColors[alert.severity]}`}
      >
        <Icon className="w-3 h-3 flex-shrink-0" />
        <span className="flex-1 truncate font-medium">
          {alerts.length} alert{alerts.length !== 1 ? "s" : ""}
        </span>
        <button
          onClick={() => setState("expanded")}
          className="p-0.5 hover:bg-white/10 rounded transition-colors"
          title="Expand alerts"
        >
          <ChevronDown className="w-3 h-3" />
        </button>
        <button
          onClick={() => setState("dismissed")}
          className="p-0.5 hover:bg-white/10 rounded transition-colors"
          title="Dismiss alerts"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    );
  }

  // Expanded: full alert banner
  return (
    <div
      className={`w-full px-4 py-2 border-b flex items-center gap-3 text-sm ${
        severityColors[alert.severity]
      }`}
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      <div className="flex-1 truncate">
        <span className="font-medium">{alert.title}</span>
        <span className="mx-2 text-white/30">|</span>
        <span className="text-white/60">{alert.description}</span>
      </div>
      {alerts.length > 1 && (
        <span className="text-xs text-white/30 flex-shrink-0">
          {currentIdx + 1}/{alerts.length}
        </span>
      )}
      <button
        onClick={() => setState("collapsed")}
        className="p-1 hover:bg-white/10 rounded transition-colors"
        title="Minimize"
      >
        <ChevronUp className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => setState("dismissed")}
        className="p-1 hover:bg-white/10 rounded transition-colors"
        title="Dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
