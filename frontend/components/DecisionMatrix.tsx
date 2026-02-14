"use client";

import { Zap, Wallet, Heart } from "lucide-react";
import type { RouteOption } from "@/lib/types";

interface DecisionMatrixProps {
  routes: RouteOption[];
  onSelect: (route: RouteOption) => void;
}

export default function DecisionMatrix({
  routes,
  onSelect,
}: DecisionMatrixProps) {
  if (routes.length < 2) return null;

  const fastest = [...routes].sort(
    (a, b) => a.total_duration_min - b.total_duration_min
  )[0];
  const cheapest = [...routes].sort(
    (a, b) => a.cost.total - b.cost.total
  )[0];
  const zen = [...routes].sort((a, b) => a.stress_score - b.stress_score)[0];

  const columns = [
    {
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      title: "Fastest",
      route: fastest,
      highlight: `${Math.round(fastest.total_duration_min)} min`,
      color: "border-amber-500/30 hover:border-amber-500/60",
    },
    {
      icon: <Wallet className="w-4 h-4 text-emerald-400" />,
      title: "Thrifty",
      route: cheapest,
      highlight: `$${cheapest.cost.total.toFixed(2)}`,
      color: "border-emerald-500/30 hover:border-emerald-500/60",
    },
    {
      icon: <Heart className="w-4 h-4 text-pink-400" />,
      title: "Zen",
      route: zen,
      highlight: `${Math.round((1 - zen.stress_score) * 100)}% calm`,
      color: "border-pink-500/30 hover:border-pink-500/60",
    },
  ];

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wide px-1 mb-2">
        Decision Matrix
      </h3>
      <div className="grid grid-cols-3 gap-2">
        {columns.map((col) => (
          <button
            key={col.title}
            onClick={() => onSelect(col.route)}
            className={`glass-card p-3 text-center border transition-all ${col.color}`}
          >
            <div className="flex justify-center mb-1">{col.icon}</div>
            <div className="text-xs font-semibold text-white">{col.title}</div>
            <div className="text-sm font-bold mt-1 text-white">
              {col.highlight}
            </div>
            <div className="text-xs text-slate-400 mt-0.5 capitalize">
              {col.route.mode}
            </div>
            {col.route.traffic_summary && (
              <div className={`text-[10px] mt-1 px-1.5 py-0.5 rounded-full ${col.route.traffic_summary.includes("Heavy") || col.route.traffic_summary.includes("Severe")
                  ? "bg-red-500/20 text-red-400"
                  : col.route.traffic_summary.includes("Moderate")
                    ? "bg-amber-500/20 text-amber-400"
                    : "bg-emerald-500/20 text-emerald-400"
                }`}>
                {col.route.traffic_summary}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
