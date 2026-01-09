/**
 * API methods for the Jira Feedback application.
 */

import { api } from "./client";
import type {
  User,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  JiraCredentials,
  JiraCredentialsRequest,
  JiraIssue,
  RubricConfig,
  RubricConfigListItem,
  RubricRuleUpdate,
  FeedbackSummary,
  FeedbackDetail,
  FeedbackStats,
  ScoreTrendItem,
  TeamPerformanceItem,
  AnalyzeRequest,
  BatchAnalyzeRequest,
  AnalysisJob,
  TelegramStatus,
  TelegramCodeResponse,
  // New types
  IssueRevisionHistory,
  RevisionStats,
  StudentsListResponse,
  StudentProgress,
  SkillRadarData,
  GradeExportRequest,
  GradeExportPreview,
  SkillGapAnalysis,
  SkillDetail,
} from "@/types/feedback";

// Auth API
export const authApi = {
  login: async (credentials: LoginRequest): Promise<TokenResponse> => {
    // Backend sets HTTP-only cookies automatically
    return api.postForm<TokenResponse>(
      "/api/v1/auth/login",
      {
        username: credentials.username,
        password: credentials.password,
      },
      { skipAuth: true }
    );
  },

  register: async (data: RegisterRequest): Promise<User> => {
    return api.post<User>("/api/v1/auth/register", data, { skipAuth: true });
  },

  logout: async (): Promise<void> => {
    // Backend clears HTTP-only cookies
    await api.post("/api/v1/auth/logout", undefined, { skipAuth: true });
  },

  getCurrentUser: async (): Promise<User> => {
    return api.get<User>("/api/v1/auth/me");
  },

  refresh: async (): Promise<TokenResponse> => {
    // Refresh uses the HTTP-only refresh_token cookie
    return api.post<TokenResponse>(
      "/api/v1/auth/refresh",
      {},
      { skipAuth: true }
    );
  },
};

// Jira Credentials API
export const jiraApi = {
  getCredentials: async (): Promise<JiraCredentials | null> => {
    try {
      return await api.get<JiraCredentials>("/api/v1/auth/jira/credentials");
    } catch {
      return null;
    }
  },

  setCredentials: async (data: JiraCredentialsRequest): Promise<JiraCredentials> => {
    return api.post<JiraCredentials>("/api/v1/auth/jira/credentials", data);
  },

  testConnection: async (data: JiraCredentialsRequest): Promise<{ success: boolean; message: string }> => {
    return api.post("/api/v1/auth/jira/test", data);
  },

  deleteCredentials: async (): Promise<void> => {
    return api.delete("/api/v1/auth/jira/credentials");
  },
};

// Issues API
export const issuesApi = {
  search: async (jql: string, limit = 50): Promise<{ issues: JiraIssue[]; total: number }> => {
    return api.post(`/api/v1/issues/search`, {
      jql,
      max_results: limit,
    });
  },

  get: async (key: string): Promise<JiraIssue> => {
    return api.get<JiraIssue>(`/api/v1/issues/${key}`);
  },

  analyze: async (key: string, options?: AnalyzeRequest): Promise<FeedbackDetail> => {
    return api.post<FeedbackDetail>(`/api/v1/issues/${key}/analyze`, options || {});
  },

  batchAnalyze: async (request: BatchAnalyzeRequest): Promise<AnalysisJob> => {
    return api.post<AnalysisJob>("/api/v1/issues/analyze-batch", request);
  },
};

// Rubrics API
export const rubricsApi = {
  list: async (): Promise<RubricConfigListItem[]> => {
    return api.get<RubricConfigListItem[]>("/api/v1/rubrics");
  },

  get: async (id: number): Promise<RubricConfig> => {
    return api.get<RubricConfig>(`/api/v1/rubrics/${id}`);
  },

  create: async (name: string): Promise<RubricConfig> => {
    return api.post<RubricConfig>("/api/v1/rubrics", { name });
  },

  update: async (id: number, data: Partial<RubricConfig>): Promise<RubricConfig> => {
    return api.put<RubricConfig>(`/api/v1/rubrics/${id}`, data);
  },

  delete: async (id: number): Promise<void> => {
    return api.delete(`/api/v1/rubrics/${id}`);
  },

  setDefault: async (id: number): Promise<RubricConfig> => {
    return api.post<RubricConfig>(`/api/v1/rubrics/${id}/set-default`);
  },

  updateRule: async (configId: number, ruleId: string, data: RubricRuleUpdate): Promise<void> => {
    return api.put(`/api/v1/rubrics/${configId}/rules/${ruleId}`, data);
  },

  listTerms: async (configId: number): Promise<string[]> => {
    return api.get<string[]>(`/api/v1/rubrics/${configId}/terms`);
  },

  addTerm: async (configId: number, term: string): Promise<string[]> => {
    return api.post<string[]>(`/api/v1/rubrics/${configId}/terms`, { term });
  },

  deleteTerm: async (configId: number, term: string): Promise<string[]> => {
    return api.delete<string[]>(`/api/v1/rubrics/${configId}/terms/${encodeURIComponent(term)}`);
  },

  previewScore: async (
    configId: number,
    data: { summary: string; description?: string; labels?: string[]; estimate?: number }
  ): Promise<{ score: number; breakdown: Record<string, unknown> }> => {
    return api.post(`/api/v1/rubrics/${configId}/preview`, data);
  },
};

// Feedback API
export const feedbackApi = {
  list: async (params?: {
    issue_key?: string;
    min_score?: number;
    max_score?: number;
    limit?: number;
    offset?: number;
  }): Promise<FeedbackSummary[]> => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
    }
    const query = searchParams.toString();
    return api.get<FeedbackSummary[]>(`/api/v1/feedback${query ? `?${query}` : ""}`);
  },

  get: async (id: number): Promise<FeedbackDetail> => {
    return api.get<FeedbackDetail>(`/api/v1/feedback/${id}`);
  },

  getByIssueKey: async (key: string): Promise<FeedbackDetail | null> => {
    const list = await feedbackApi.list({ issue_key: key, limit: 1 });
    if (list.length === 0) return null;
    return feedbackApi.get(list[0].id);
  },

  getStats: async (): Promise<FeedbackStats> => {
    return api.get<FeedbackStats>("/api/v1/feedback/stats");
  },

  getTrends: async (days = 30): Promise<{ trends: ScoreTrendItem[]; period_days: number }> => {
    return api.get(`/api/v1/feedback/trends?days=${days}`);
  },

  getTeamPerformance: async (days = 30): Promise<{ members: TeamPerformanceItem[]; period_days: number }> => {
    return api.get(`/api/v1/feedback/team?days=${days}`);
  },

  postToJira: async (id: number): Promise<{ success: boolean; comment_id?: string }> => {
    return api.post(`/api/v1/feedback/${id}/post-jira`);
  },
};

// Jobs API
export const jobsApi = {
  list: async (limit = 20): Promise<AnalysisJob[]> => {
    return api.get<AnalysisJob[]>(`/api/v1/issues/jobs?limit=${limit}`);
  },

  get: async (jobId: string): Promise<AnalysisJob> => {
    return api.get<AnalysisJob>(`/api/v1/issues/jobs/${jobId}`);
  },
};

// Telegram API
export const telegramApi = {
  getStatus: async (): Promise<TelegramStatus> => {
    return api.get<TelegramStatus>("/api/v1/telegram/status");
  },

  generateCode: async (): Promise<TelegramCodeResponse> => {
    return api.post<TelegramCodeResponse>("/api/v1/telegram/generate-code");
  },

  updateNotifications: async (enabled: boolean): Promise<void> => {
    return api.post("/api/v1/telegram/notifications", { enabled });
  },

  unlink: async (): Promise<void> => {
    return api.delete("/api/v1/telegram/unlink");
  },

  getBotInfo: async (): Promise<{ configured: boolean; username?: string; name?: string }> => {
    return api.get("/api/v1/telegram/bot-info");
  },
};

// WebSocket stats API
export const wsApi = {
  getStats: async (): Promise<{ total_connections: number; users: number; jobs: number }> => {
    return api.get("/api/v1/ws/stats");
  },
};

// Revision Tracking API
export const revisionsApi = {
  getIssueRevisions: async (issueKey: string): Promise<IssueRevisionHistory> => {
    return api.get<IssueRevisionHistory>(`/api/v1/feedback/issue/${issueKey}/revisions`);
  },

  getStats: async (): Promise<RevisionStats> => {
    return api.get<RevisionStats>("/api/v1/feedback/revisions/stats");
  },
};

// Students API
export const studentsApi = {
  list: async (days = 90): Promise<StudentsListResponse> => {
    return api.get<StudentsListResponse>(`/api/v1/feedback/students?days=${days}`);
  },

  getProgress: async (assignee: string, days = 90): Promise<StudentProgress> => {
    return api.get<StudentProgress>(`/api/v1/feedback/student/${encodeURIComponent(assignee)}?days=${days}`);
  },

  getSkillRadar: async (assignee: string, days = 90): Promise<SkillRadarData> => {
    return api.get<SkillRadarData>(`/api/v1/feedback/student/${encodeURIComponent(assignee)}/skill-radar?days=${days}`);
  },
};

// Grade Export API
export const gradesApi = {
  preview: async (request: GradeExportRequest): Promise<GradeExportPreview> => {
    return api.post<GradeExportPreview>("/api/v1/feedback/export/grades/preview", request);
  },

  exportCsv: async (request: GradeExportRequest): Promise<Blob> => {
    const response = await fetch("/api/v1/feedback/export/grades", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error("Failed to export grades");
    }
    return response.blob();
  },
};

// Skills Analysis API
export const skillsApi = {
  getAnalysis: async (days = 30): Promise<SkillGapAnalysis> => {
    return api.get<SkillGapAnalysis>(`/api/v1/feedback/skills/analysis?days=${days}`);
  },

  getDetail: async (ruleId: string, days = 30): Promise<SkillDetail> => {
    return api.get<SkillDetail>(`/api/v1/feedback/skills/${ruleId}?days=${days}`);
  },
};
