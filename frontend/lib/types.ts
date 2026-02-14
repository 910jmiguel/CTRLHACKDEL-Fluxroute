export type RouteMode = "transit" | "driving" | "walking" | "cycling" | "hybrid";

export interface Coordinate {
  lat: number;
  lng: number;
}

export interface RouteSegment {
  mode: RouteMode;
  geometry: GeoJSON.LineString;
  distance_km: number;
  duration_min: number;
  instructions?: string;
  transit_line?: string;
  transit_route_id?: string;
  color?: string;
  congestion_level?: string; // "low" | "moderate" | "heavy" | "severe"
  congestion_segments?: Array<{
    geometry: GeoJSON.LineString;
    congestion: string;
  }>;
}

export interface CostBreakdown {
  fare: number;
  gas: number;
  parking: number;
  total: number;
}

export interface DelayInfo {
  probability: number;
  expected_minutes: number;
  confidence: number;
  factors: string[];
}

export interface RouteOption {
  id: string;
  label: string;
  mode: RouteMode;
  segments: RouteSegment[];
  total_distance_km: number;
  total_duration_min: number;
  cost: CostBreakdown;
  delay_info: DelayInfo;
  stress_score: number;
  departure_time?: string;
  arrival_time?: string;
  summary: string;
  traffic_summary?: string; // "Heavy traffic", "Moderate traffic", etc.
}

export interface RouteRequest {
  origin: Coordinate;
  destination: Coordinate;
  modes?: RouteMode[];
  departure_time?: string;
}

export interface RouteResponse {
  routes: RouteOption[];
  origin: Coordinate;
  destination: Coordinate;
}

export interface DelayPredictionResponse {
  delay_probability: number;
  expected_delay_minutes: number;
  confidence: number;
  contributing_factors: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  message: string;
  suggested_actions: string[];
}

export interface ServiceAlert {
  id: string;
  route_id?: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "error";
  active: boolean;
}

export interface VehiclePosition {
  vehicle_id: string;
  route_id?: string;
  latitude: number;
  longitude: number;
  bearing?: number;
  speed?: number;
  timestamp?: number;
}
