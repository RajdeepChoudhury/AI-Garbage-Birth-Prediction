export type Risk = "Low" | "Medium" | "High" | "Critical";
export type Role = "admin" | "officer" | "analyst" | "citizen";

export interface User { id: number; email: string; role: Role; is_active: boolean }
export interface TokenPair { access_token: string; refresh_token: string; token_type: string }

export interface Factor { feature: string; value: number; impact: number }

export interface Forecast {
  id: number;
  ward: number;
  latitude: number;
  longitude: number;
  forecast_date: string;
  predicted_volume: number;
  risk_level: Risk;
  hotspot_probability: number;
  urgency_score: number;
  confidence: number;
  recommended_cleaning_time: string;
  predicted_overflow_date: string | null;
  top_factors: Factor[] | null;
  created_at: string;
}

export interface RegressionScores { MAE: number; RMSE: number; R2: number; "Train Seconds": number }
export interface ClassificationScores {
  Precision: number; Recall: number; F1: number; "F1 High and Critical": number; "Train Seconds": number;
}
export interface Metrics {
  regression: Record<string, RegressionScores>;
  classification: Record<string, ClassificationScores>;
  best: { regressor: string; classifier: string };
  not_yet_evaluated: string[];
  data_note: string;
  feature_importance: Record<string, number>;
}

export interface UploadSummary { rows_read: number; wards_forecast: number; risk_counts: Record<string, number> }
export interface AssistantReply { answer: string; model: string; wards_in_context: number }
