"use client";

import { useEffect, useState } from "react";
import { MetricsCards } from "./_components/metrics-cards";
import { ScoreDistributionChart } from "./_components/score-distribution-chart";
import { RecentFeedbackList } from "./_components/recent-feedback-list";
import { ActivityFeed } from "./_components/activity-feed";
import { feedbackApi } from "@/lib/api/feedback-api";
import type { FeedbackStats, FeedbackSummary } from "@/types/feedback";

export default function OverviewPage() {
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [recentFeedback, setRecentFeedback] = useState<FeedbackSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, feedbackData] = await Promise.all([
          feedbackApi.getStats(),
          feedbackApi.list({ limit: 10 }),
        ]);
        setStats(statsData);
        setRecentFeedback(feedbackData);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Jira Feedback Overview</h1>
        <p className="text-muted-foreground">
          Monitor issue quality and track feedback across your Jira projects.
        </p>
      </div>

      <MetricsCards stats={stats} isLoading={isLoading} />

      <div className="grid gap-4 md:grid-cols-2">
        <ScoreDistributionChart
          distribution={stats?.score_distribution ?? null}
          isLoading={isLoading}
        />
        <ActivityFeed />
      </div>

      <RecentFeedbackList feedback={recentFeedback} isLoading={isLoading} />
    </div>
  );
}
