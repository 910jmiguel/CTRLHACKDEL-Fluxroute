export type RouteMode = "transit" | "driving" | "walking" | "cycling" | "hybrid";

export interface Coordinate {
  lat: number;
  lng: number;
}

export interface DirectionStep {
  instruction: string;
  distance_km: number;
  duration_min: number;
  maneuver_type: string;
  maneuver_modifier: string;
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
  steps?: DirectionStep[];
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

export interface ParkingInfo {
  station_name: string;
  daily_rate: number;
  capacity: number;
  parking_type: string; // "surface", "structure"
  agency: string;
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
  parking_info?: ParkingInfo;
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

export interface TransitLinesData {
  lines: GeoJSON.FeatureCollection;
  stations: GeoJSON.FeatureCollection;
}

export interface CustomSegmentRequest {
  mode: RouteMode;
  line_id?: string;
  start_station_id?: string;
  end_station_id?: string;
  origin?: Coordinate;
  destination?: Coordinate;
}

export interface CustomRouteRequest {
  segments: CustomSegmentRequest[];
  trip_origin: Coordinate;
  trip_destination: Coordinate;
}

export interface LineStop {
  stop_id: string;
  stop_name: string;
  lat: number;
  lng: number;
}

export interface LineInfo {
  line_id: string;
  line_name: string;
  color: string;
  stops: LineStop[];
}

export interface StopSearchResult {
  stop_id: string;
  stop_name: string;
  lat: number;
  lng: number;
  route_id?: string;
  line?: string;
}

export type SearchSuggestion =
  | { type: "station"; data: StopSearchResult }
  | { type: "address"; data: { place_name: string; center: [number, number] } };
