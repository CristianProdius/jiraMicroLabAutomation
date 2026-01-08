/**
 * Types for the Jira Feedback application.
 * These match the backend Pydantic schemas.
 */

// Auth types
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Jira types
export interface JiraCredentials {
  id: number;
  base_url: string;
  email: string;
  is_active: boolean;
}

export interface JiraCredentialsRequest {
  base_url: string;
  email: string;
  api_token: string;
}

export interface JiraIssue {
  key: string;
  summary: string;
  description: string | null;
  status: string;
  issue_type: string;
  assignee: string | null;
  labels: string[];
  estimate: number | null;
  acceptance_criteria: string | null;
  has_attachments: boolean;
  has_subtasks: boolean;
  created: string;
  updated: string;
}

// Rubric types
export interface RubricRule {
  id: number;
  rule_id: string;
  name: string;
  description: string;
  weight: number;
  is_enabled: boolean;
  thresholds: Record<string, number> | null;
}

export interface RubricConfig {
  id: number;
  name: string;
  is_default: boolean;
  min_description_words: number;
  require_acceptance_criteria: boolean;
  allowed_labels: string[] | null;
  rules: RubricRule[];
  ambiguous_terms: string[];
  created_at: string;
  updated_at: string;
}

export interface RubricConfigListItem {
  id: number;
  name: string;
  is_default: boolean;
  created_at: string;
}

export interface RubricRuleUpdate {
  weight?: number;
  is_enabled?: boolean;
  thresholds?: Record<string, number> | null;
}

// Feedback types
export interface FeedbackSummary {
  id: number;
  issue_key: string;
  issue_summary: string | null;
  score: number;
  emoji: string;
  issue_type: string | null;
  assignee: string | null;
  was_posted_to_jira: boolean;
  created_at: string;
}

export interface FeedbackDetail {
  id: number;
  issue_key: string;
  issue_summary: string | null;
  score: number;
  emoji: string;
  overall_assessment: string;
  strengths: string[];
  improvements: string[];
  suggestions: string[];
  rubric_breakdown: Record<string, RubricBreakdownItem>;
  improved_ac: string | null;
  resources: string[] | null;
  issue_type: string | null;
  issue_status: string | null;
  assignee: string | null;
  labels: string[] | null;
  was_posted_to_jira: boolean;
  was_sent_to_telegram: boolean;
  created_at: string;
}

export interface RubricBreakdownItem {
  score: number;
  weighted_score: number;
  message: string;
  suggestion: string | null;
}

export interface FeedbackStats {
  total_analyzed: number;
  average_score: number;
  score_distribution: Record<string, number>;
  issues_below_70: number;
  top_improvement_areas: string[];
  recent_count_7d: number;
  recent_count_30d: number;
}

export interface ScoreTrendItem {
  date: string;
  average_score: number;
  count: number;
}

export interface TeamPerformanceItem {
  assignee: string;
  issues_count: number;
  average_score: number;
  trend: number;
}

// Analysis types
export interface AnalyzeRequest {
  rubric_config_id?: number;
  post_to_jira?: boolean;
  send_telegram?: boolean;
}

export interface BatchAnalyzeRequest {
  jql: string;
  max_issues?: number;
  rubric_config_id?: number;
  dry_run?: boolean;
  post_to_jira?: boolean;
  send_telegram?: boolean;
}

export interface AnalysisJob {
  id: number;
  job_id: string;
  jql: string | null;
  issue_keys: string[] | null;
  status: "pending" | "running" | "completed" | "failed";
  total_issues: number;
  processed_issues: number;
  failed_issues: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

// WebSocket event types
export type WebSocketEventType =
  | "job_started"
  | "job_progress"
  | "job_completed"
  | "job_failed"
  | "issue_started"
  | "issue_rubric_complete"
  | "issue_complete"
  | "issue_failed"
  | "pong"
  | "activity";

export interface WebSocketEvent {
  event: WebSocketEventType;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface JobProgressEvent extends WebSocketEvent {
  event: "job_progress";
  data: {
    job_id: string;
    current_issue: string;
    processed: number;
    total: number;
    failed: number;
  };
}

export interface IssueCompleteEvent extends WebSocketEvent {
  event: "issue_complete";
  data: {
    job_id: string;
    issue_key: string;
    score: number;
    emoji: string;
  };
}

// Telegram types
export interface TelegramStatus {
  is_linked: boolean;
  telegram_username: string | null;
  notifications_enabled: boolean;
}

export interface TelegramCodeResponse {
  code: string;
  expires_in_minutes: number;
}

// Dashboard types
export interface DashboardMetrics {
  total_analyzed: number;
  average_score: number;
  issues_below_70: number;
  pending_jobs: number;
}

export interface ActivityItem {
  id: string;
  type: "analysis" | "job" | "notification";
  message: string;
  timestamp: string;
  issue_key?: string;
  score?: number;
}
