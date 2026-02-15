import { API_URL } from "./constants";
import type {
  RouteRequest,
  RouteResponse,
  RouteOption,
  DelayPredictionResponse,
  ChatMessage,
  ChatResponse,
  ServiceAlert,
  VehiclePosition,
  TransitLinesData,
  LineInfo,
  CustomRouteRequest,
  TransitSuggestionsResponse,
  Coordinate,
  CustomRouteRequestV2,
} from "./types";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function getRoutes(request: RouteRequest): Promise<RouteResponse> {
  return fetchApi<RouteResponse>("/routes", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function predictDelay(params: {
  line: string;
  hour?: number;
  day_of_week?: number;
  month?: number;
}): Promise<DelayPredictionResponse> {
  const query = new URLSearchParams({ line: params.line });
  if (params.hour !== undefined) query.set("hour", String(params.hour));
  if (params.day_of_week !== undefined) query.set("day_of_week", String(params.day_of_week));
  if (params.month !== undefined) query.set("month", String(params.month));
  return fetchApi<DelayPredictionResponse>(`/predict-delay?${query}`);
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
  context?: Record<string, unknown>
): Promise<ChatResponse> {
  return fetchApi<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message, history, context }),
  });
}

export async function getAlerts(): Promise<{ alerts: ServiceAlert[] }> {
  return fetchApi<{ alerts: ServiceAlert[] }>("/alerts");
}

export async function getVehicles(): Promise<{ vehicles: VehiclePosition[] }> {
  return fetchApi<{ vehicles: VehiclePosition[] }>("/vehicles");
}

export async function getWeather(): Promise<Record<string, unknown>> {
  return fetchApi<Record<string, unknown>>("/weather");
}

export async function getNearbyStops(lat: number, lng: number, radius?: number) {
  const query = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
  });
  if (radius) query.set("radius_km", String(radius));
  return fetchApi<{ stops: Array<Record<string, unknown>> }>(`/nearby-stops?${query}`);
}

export async function getTransitShape(routeId: string) {
  return fetchApi<{ route_id: string; geometry: GeoJSON.LineString }>(
    `/transit-shape/${routeId}`
  );
}

export async function getTransitLines(): Promise<TransitLinesData> {
  return fetchApi<TransitLinesData>("/transit-lines");
}

export async function healthCheck() {
  return fetchApi<{ status: string }>("/health");
}

export async function getLineStops(lineId: string): Promise<LineInfo> {
  return fetchApi<LineInfo>(`/line-stops/${lineId}`);
}

export async function calculateCustomRoute(request: CustomRouteRequest): Promise<RouteOption> {
  return fetchApi<RouteOption>("/custom-route", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getTransitSuggestions(
  origin: Coordinate,
  destination: Coordinate
): Promise<TransitSuggestionsResponse> {
  return fetchApi<TransitSuggestionsResponse>("/suggest-transit-routes", {
    method: "POST",
    body: JSON.stringify({ origin, destination }),
  });
}

export async function calculateCustomRouteV2(request: CustomRouteRequestV2): Promise<RouteOption> {
  return fetchApi<RouteOption>("/custom-route-v2", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
