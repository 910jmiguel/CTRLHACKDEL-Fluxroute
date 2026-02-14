"use client";

interface DelayIndicatorProps {
  probability: number;
  expectedMinutes: number;
  compact?: boolean;
}

export default function DelayIndicator({
  probability,
  expectedMinutes,
  compact = false,
}: DelayIndicatorProps) {
  const level =
    probability < 0.2 ? "low" : probability < 0.4 ? "medium" : "high";

  const config = {
    low: { bg: "bg-emerald-500/20", text: "text-emerald-400", border: "border-emerald-500/30", label: "Low Risk" },
    medium: { bg: "bg-amber-500/20", text: "text-amber-400", border: "border-amber-500/30", label: "Moderate" },
    high: { bg: "bg-red-500/20", text: "text-red-400", border: "border-red-500/30", label: "High Risk" },
  }[level];

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text} border ${config.border}`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            level === "low"
              ? "bg-emerald-400"
              : level === "medium"
              ? "bg-amber-400"
              : "bg-red-400"
          }`}
        />
        {Math.round(probability * 100)}%
      </span>
    );
  }

  return (
    <div className={`rounded-lg p-2 ${config.bg} border ${config.border}`}>
      <div className="flex items-center justify-between">
        <span className={`text-xs font-medium ${config.text}`}>
          {config.label}
        </span>
        <span className={`text-xs ${config.text}`}>
          {Math.round(probability * 100)}% chance
        </span>
      </div>
      {expectedMinutes > 0 && (
        <div className="text-xs text-slate-400 mt-1">
          ~{expectedMinutes.toFixed(0)} min expected delay
        </div>
      )}
    </div>
  );
}
