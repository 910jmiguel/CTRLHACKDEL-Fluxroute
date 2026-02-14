export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";
export const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

export const TORONTO_CENTER: [number, number] = [-79.3832, 43.6532];
export const TORONTO_ZOOM = 11;

export const TORONTO_BOUNDS: [[number, number], [number, number]] = [
  [-79.65, 43.55],
  [-79.10, 43.85],
];

export const MAP_STYLE = "mapbox://styles/mapbox/standard";

export const TTC_COLORS: Record<string, string> = {
  "1": "#FFCC00", // Line 1 Yonge-University (Yellow)
  "2": "#00A651", // Line 2 Bloor-Danforth (Green)
  "3": "#0082C9", // Line 3 Scarborough RT (Blue)
  "4": "#A8518A", // Line 4 Sheppard (Purple)
};

export const MODE_COLORS: Record<string, string> = {
  transit: "#FFCC00",
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
