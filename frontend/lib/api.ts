import { API_URL } from "./constants";
import type {
  RouteRequest,
  RouteResponse,
  DelayPredictionResponse,
  ChatMessage,
  ChatResponse,
  ServiceAlert,
  VehiclePosition,
  TransitLinesData,
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
