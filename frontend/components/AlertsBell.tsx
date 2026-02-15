"use client";

import { Bell } from "lucide-react";

interface AlertsBellProps {
  count: number;
  onClick: () => void;
}

export default function AlertsBell({ count, onClick }: AlertsBellProps) {
  return (
    <button
      onClick={onClick}
      className="relative p-2 rounded-lg hover:bg-[var(--surface-hover)] transition-colors text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
      aria-label={`${count} service alert${count !== 1 ? "s" : ""}`}
      title={`${count} service alert${count !== 1 ? "s" : ""}`}
    >
      <Bell className="w-4 h-4" />
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold leading-none px-1">
          {count > 9 ? "9+" : count}
        </span>
      )}
    </button>
  );
}
