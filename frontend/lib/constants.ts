export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

export const TORONTO_CENTER: [number, number] = [-79.3832, 43.6532];
export const TORONTO_ZOOM = 11;

export const TORONTO_BOUNDS: [[number, number], [number, number]] = [
  [-79.65, 43.55],
  [-79.10, 43.85],
];

export const MAP_STYLE = "mapbox://styles/mapbox/standard";

export const TTC_COLORS: Record<string, string> = {
  "1": "#F0CC49", // Line 1 Yonge-University (Yellow)
  "2": "#549F4D", // Line 2 Bloor-Danforth (Green)
  "4": "#9C246E", // Line 4 Sheppard (Purple)
  "5": "#DE7731", // Line 5 Eglinton Crosstown (Orange)
  "6": "#959595", // Line 6 Finch West (Grey)
};

export const MODE_COLORS: Record<string, string> = {
  transit: "#F0CC49",
  driving: "#3B82F6",
  walking: "#10B981",
  cycling: "#F59E0B",
  hybrid: "#8B5CF6",
};

export const MODE_ICONS: Record<string, string> = {
  transit: "🚇",
  driving: "🚗",
  walking: "🚶",
  cycling: "🚲",
  hybrid: "🔄",
};

export const STRESS_LABELS: Record<string, string> = {
  low: "Zen",
  medium: "Moderate",
  high: "Stressful",
};

export const CONGESTION_COLORS: Record<string, string> = {
  low: "#10B981",      // Green
  moderate: "#F59E0B", // Amber
  heavy: "#F97316",    // Orange
  severe: "#EF4444",   // Red
  unknown: "#3B82F6",  // Blue (fallback)
};

export const ISOCHRONE_COLORS: string[] = [
  "rgba(16, 185, 129, 0.25)",  // 10 min — green
  "rgba(245, 158, 11, 0.20)",  // 20 min — amber
  "rgba(239, 68, 68, 0.15)",   // 30 min — red
  "rgba(139, 92, 246, 0.12)",  // 40 min — purple
];

export const ISOCHRONE_BORDER_COLORS: string[] = [
  "#10B981",
  "#F59E0B",
  "#EF4444",
  "#8B5CF6",
];

// Panel widths
export const PANEL_WIDTH_DESKTOP = 420;
export const PANEL_WIDTH_TABLET = 360;

// Map styles
export const MAP_STYLE_LIGHT = "mapbox://styles/mapbox/standard";
export const MAP_STYLE_DARK = "mapbox://styles/mapbox/standard";

// TTC Line Logos
export const TTC_LINE_LOGOS: Record<string, string> = {
  "1": "/images/line-logos/line1.png",
  "2": "/images/line-logos/line2.png",
  "4": "/images/line-logos/line4.svg",
  "5": "/images/line-logos/line5.png",
  "6": "/images/line-logos/line6.png",
};
