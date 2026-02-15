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

// --- V2 Custom Route Builder Types ---

export interface TransitRouteSuggestion {
  suggestion_id: string;
  route_id: string;
  display_name: string;
  transit_mode: "SUBWAY" | "BUS" | "TRAM" | "RAIL";
  color: string;
  board_stop_name: string;
  board_coord: Coordinate;
  board_stop_id?: string;
  alight_stop_name: string;
  alight_coord: Coordinate;
  alight_stop_id?: string;
  direction_hint: string;
  relevance_reason: string;
  estimated_duration_min: number;
  estimated_distance_km: number;
  intermediate_stops?: Array<{stop_id: string; stop_name: string; lat: number; lng: number}>;
  transfer_group_id?: string;
  transfer_sequence?: number;
  transfer_station_name?: string;
}

export interface TransitSuggestionsResponse {
  suggestions: TransitRouteSuggestion[];
  source: string;
}

export interface CustomSegmentV2 {
  id: string;
  mode: "driving" | "walking" | "transit";
  selectedSuggestion?: TransitRouteSuggestion;
}

export interface CustomSegmentRequestV2 {
  mode: RouteMode;
  suggestion_id?: string;
  route_id?: string;
  board_coord?: Coordinate;
  alight_coord?: Coordinate;
  board_stop_name?: string;
  alight_stop_name?: string;
  board_stop_id?: string;
  alight_stop_id?: string;
  transit_mode?: string;
  display_name?: string;
  color?: string;
}

export interface CustomRouteRequestV2 {
  segments: CustomSegmentRequestV2[];
  trip_origin: Coordinate;
  trip_destination: Coordinate;
}
