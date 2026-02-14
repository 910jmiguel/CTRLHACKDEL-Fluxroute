"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { CostBreakdown as CostBreakdownType } from "@/lib/types";

interface CostBreakdownProps {
  cost: CostBreakdownType;
}

export default function CostBreakdown({ cost }: CostBreakdownProps) {
  const [expanded, setExpanded] = useState(false);

  const hasBreakdown = cost.fare > 0 || cost.gas > 0 || cost.parking > 0;

  return (
    <div>
      <button
        onClick={() => hasBreakdown && setExpanded(!expanded)}
        className="flex items-center gap-1 text-sm font-semibold text-white"
      >
        ${cost.total.toFixed(2)}
        {hasBreakdown && (
          expanded ? (
            <ChevronUp className="w-3 h-3 text-slate-400" />
          ) : (
            <ChevronDown className="w-3 h-3 text-slate-400" />
          )
        )}
      </button>

      {expanded && hasBreakdown && (
        <div className="mt-1 space-y-0.5 text-xs text-slate-400 slide-up">
          {cost.fare > 0 && (
            <div className="flex justify-between">
              <span>Fare</span>
              <span>${cost.fare.toFixed(2)}</span>
            </div>
          )}
          {cost.gas > 0 && (
            <div className="flex justify-between">
              <span>Gas</span>
              <span>${cost.gas.toFixed(2)}</span>
            </div>
          )}
          {cost.parking > 0 && (
            <div className="flex justify-between">
              <span>Parking</span>
              <span>${cost.parking.toFixed(2)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
