"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Info, XCircle } from "lucide-react";
import type { ServiceAlert } from "@/lib/types";
import { getAlerts } from "@/lib/api";

export default function LiveAlerts() {
  const [alerts, setAlerts] = useState<ServiceAlert[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);

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
    </div>
  );
}
