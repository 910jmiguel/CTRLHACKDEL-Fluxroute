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
  const theme: MapTheme = "dawn";
  const isDark = false;

  return { theme, isDark };
}
