"use client";

export type MapTheme = "dawn" | "day" | "dusk" | "night";

export function useTimeBasedTheme() {
  const theme: MapTheme = "dawn";
  const isDark = false;

  return { theme, isDark };
}
