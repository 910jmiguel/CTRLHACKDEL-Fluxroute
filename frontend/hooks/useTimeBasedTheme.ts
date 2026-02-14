"use client";

import { useState, useEffect } from "react";

export type MapTheme = "dawn" | "day" | "dusk" | "night";

function getThemeForHour(hour: number): MapTheme {
  if (hour >= 6 && hour < 8) return "dawn";
  if (hour >= 8 && hour < 18) return "day";
  if (hour >= 18 && hour < 20) return "dusk";
  return "night";
}

export function useTimeBasedTheme() {
  const [theme, setTheme] = useState<MapTheme>(() =>
    getThemeForHour(new Date().getHours())
  );

  useEffect(() => {
    const update = () => setTheme(getThemeForHour(new Date().getHours()));
    const interval = setInterval(update, 60_000);
    return () => clearInterval(interval);
  }, []);

  const isDark = theme === "night" || theme === "dusk";

  return { theme, isDark };
}
