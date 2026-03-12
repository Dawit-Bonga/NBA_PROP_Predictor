export type Target = "PTS" | "REB" | "AST";

export interface ApiConfig {
  targets: Target[];
  api_version: string;
}

export interface HealthResponse {
  status: string;
}

export interface PlayersResponse {
  players: string[];
}

export interface ModelHoldoutMetrics {
  rows: number;
  mae: number;
  rmse: number;
  baseline_mae: number;
  interval_coverage: number;
  mean_interval_width: number;
}

export interface ModelMetadata {
  target?: Target;
  feature_columns?: string[];
  generated_at?: string;
  metrics?: {
    holdout: ModelHoldoutMetrics;
  };
  available?: boolean;
}

export type ModelsResponse = Record<string, ModelMetadata>;

export interface PredictionRequest {
  player: string;
  opponent?: string;
  is_home?: number;
  rest_days?: number;
  season?: string;
  game_date?: string;
}

export interface PredictionBand {
  mean: number;
  lower: number;
  upper: number;
}

export interface PredictionResponse {
  player: string;
  opponent: string;
  is_home: number;
  rest_days: number;
  last_game_date: string;
  data_source: string;
  context_source: string;
  PTS: PredictionBand;
  REB: PredictionBand;
  AST: PredictionBand;
}

export interface PropRow {
  player: string;
  stat: string;
  line: number;
  stat_mapped: string;
  source: string;
  timestamp: string;
}

export interface PredictionRow {
  player: string;
  stat: string;
  stat_mapped: string;
  line: number;
  prediction: number | null;
  lower: number | null;
  upper: number | null;
  opponent: string | null;
  is_home: number | null;
  rest_days: number | null;
  last_game_date: string | null;
  data_source: string | null;
  context_source: string | null;
  edge: number | null;
  generated_at: string;
  error: string;
}

export interface BetRow extends PredictionRow {
  abs_edge: number;
  recommendation: string;
  confidence: string;
}

export interface PlayerSummary {
  last5_pts: number;
  last5_reb: number;
  last5_ast: number;
  last10_pts: number;
  last10_reb: number;
  last10_ast: number;
  season_pts: number;
  season_reb: number;
  season_ast: number;
  last_game_pts: number;
  last_game_reb: number;
  last_game_ast: number;
  last_game_min: number;
}

export interface RecentGameRow {
  GAME_DATE: string;
  MATCHUP: string;
  WL: string;
  MIN: number | string;
  PTS: number;
  REB: number;
  AST: number;
  FGA: number;
  FTA: number;
  TOV: number;
}

export interface PlayerInsightsResponse {
  player: string;
  opponent: string;
  is_home: number;
  rest_days: number;
  last_game_date: string;
  data_source: string;
  context_source: string;
  summary: PlayerSummary;
  recent_games: RecentGameRow[];
}
