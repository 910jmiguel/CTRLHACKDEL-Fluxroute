export type RouteMode = "transit" | "driving" | "walking" | "cycling" | "hybrid";

export type ViewMode = "map" | "dashboard" | "navigation";
export type ThemeMode = "light" | "dark";

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
  departure_time?: string;
  arrival_time?: string;
  trip_id?: string;
  board_stop_id?: string;
  alight_stop_id?: string;
  next_departures?: Array<{ departure_time: string; minutes_until: number }>;
  schedule_source?: string;  // "gtfs-rt" | "gtfs-static" | "estimated"
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

// --- Navigation Types (Phase 1 & 2) ---

export interface NavigationInstruction {
  instruction: string;
  distance_km: number;
  duration_min: number;
  maneuver_type: string;
  maneuver_modifier: string;
  voice_instruction?: string;
  banner_primary?: string;
  banner_secondary?: string;
  lane_guidance?: Array<{
    indications: string[];
    valid: boolean;
    active?: boolean;
  }>;
  geometry?: GeoJSON.LineString;
}

export interface NavigationRoute {
  route: RouteOption;
  navigation_instructions: NavigationInstruction[];
  voice_locale: string;
  alternatives: RouteOption[];
}

export interface NavigationRouteRequest {
  origin: Coordinate;
  destination: Coordinate;
  waypoints?: Coordinate[];
  profile?: string;
  alternatives?: boolean;
  voice_instructions?: boolean;
  banner_instructions?: boolean;
  exclude?: string[];
  depart_at?: string;
  voice_locale?: string;
}

export interface IsochroneRequest {
  center: Coordinate;
  profile?: string;
  contours_minutes?: number[];
  polygons?: boolean;
}

export interface IsochroneResponse {
  geojson: GeoJSON.FeatureCollection;
  center: Coordinate;
  profile: string;
  contours_minutes: number[];
}

export interface OptimizationRequest {
  coordinates: Coordinate[];
  profile?: string;
  roundtrip?: boolean;
  source?: string;
  destination?: string;
}

export interface OptimizationResponse {
  waypoint_order: number[];
  routes: RouteOption[];
  total_distance_km: number;
  total_duration_min: number;
}

export interface NavigationPositionUpdate {
  type: "position_update";
  lat: number;
  lng: number;
  speed?: number;
  bearing?: number;
}

export interface NavigationUpdate {
  type: "navigation_update" | "reroute" | "traffic_update" | "arrival" | "error";
  step_index?: number;
  remaining_distance_km?: number;
  remaining_duration_min?: number;
  eta?: string;
  instruction?: string;
  voice_instruction?: string;
  lane_guidance?: Array<{
    indications: string[];
    valid: boolean;
    active?: boolean;
  }>;
  speed_limit?: number;
  destination_reached?: boolean;
  new_route?: {
    geometry: GeoJSON.LineString;
    distance_km: number;
    duration_min: number;
    steps: Array<Record<string, unknown>>;
    navigation_instructions: NavigationInstruction[];
  };
  reason?: string;
}

export interface NavigationSessionResponse {
  session_id: string;
  websocket_url: string;
  route: Record<string, unknown>;
}
