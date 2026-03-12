import type {
  ApiConfig,
  BetRow,
  HealthResponse,
  ModelsResponse,
  PredictionRow,
  PredictionRequest,
  PredictionResponse,
  PlayerInsightsResponse,
  PropRow,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  baseUrl: API_BASE_URL,
  health: () => request<HealthResponse>("/health"),
  config: () => request<ApiConfig>("/config"),
  players: () => request<{ players: string[] }>("/players"),
  models: () => request<ModelsResponse>("/models"),
  props: () => request<{ props: PropRow[] }>("/props"),
  predictions: () => request<{ predictions: PredictionRow[] }>("/predictions"),
  bets: () => request<{ bets: BetRow[] }>("/bets"),
  refreshPipeline: (minEdge = 2) =>
    request<{ predictions: number; bets: number; min_edge: number }>(`/pipeline/refresh?min_edge=${minEdge}`, {
      method: "POST",
    }),
  playerInsights: (payload: PredictionRequest) =>
    request<PlayerInsightsResponse>("/player-insights", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  predict: (payload: PredictionRequest) =>
    request<PredictionResponse>("/predict", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
