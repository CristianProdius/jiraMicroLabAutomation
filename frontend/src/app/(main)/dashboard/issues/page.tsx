"use client";

import { useEffect, useState, useCallback } from "react";
import { IssuesTable } from "./_components/issues-table";
import { IssueFilters } from "./_components/issue-filters";
import { BulkActions } from "./_components/bulk-actions";
import { feedbackApi, issuesApi } from "@/lib/api/feedback-api";
import type { FeedbackSummary } from "@/types/feedback";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

export default function IssuesPage() {
  const [feedback, setFeedback] = useState<FeedbackSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [scoreFilter, setScoreFilter] = useState<{
    min?: number;
    max?: number;
  }>({});

  const loadFeedback = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await feedbackApi.list({
        min_score: scoreFilter.min,
        max_score: scoreFilter.max,
        limit: 50,
      });
      setFeedback(data);
    } catch (error) {
      console.error("Failed to load feedback:", error);
    } finally {
      setIsLoading(false);
    }
  }, [scoreFilter]);

  useEffect(() => {
    loadFeedback();
  }, [loadFeedback]);

  const handleSearch = async (jql: string) => {
    setIsSearching(true);
    try {
      // Search for issues and analyze them
      const result = await issuesApi.search(jql, 20);

      // For now, just load the feedback for these issues if they exist
      // In production, you might want to trigger analysis for new issues
      const data = await feedbackApi.list({ limit: 50 });
      setFeedback(data);
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleScoreFilter = (min?: number, max?: number) => {
    setScoreFilter({ min, max });
  };

  const handleAnalyze = async (issueKey: string) => {
    try {
      await issuesApi.analyze(issueKey);
      await loadFeedback();
    } catch (error) {
      console.error("Analysis failed:", error);
    }
  };

  const handleAnalyzeSelected = async () => {
    setIsProcessing(true);
    try {
      const selectedFeedback = feedback.filter((f) =>
        selectedIds.includes(f.id)
      );
      for (const item of selectedFeedback) {
        await issuesApi.analyze(item.issue_key);
      }
      await loadFeedback();
      setSelectedIds([]);
    } catch (error) {
      console.error("Batch analysis failed:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePostToJira = async () => {
    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        await feedbackApi.postToJira(id);
      }
      await loadFeedback();
      setSelectedIds([]);
    } catch (error) {
      console.error("Post to Jira failed:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Issues</h1>
          <p className="text-muted-foreground">
            View and manage analyzed Jira issues.
          </p>
        </div>
        <Button variant="outline" onClick={loadFeedback} disabled={isLoading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <IssueFilters
        onSearch={handleSearch}
        onScoreFilter={handleScoreFilter}
        isSearching={isSearching}
      />

      <BulkActions
        selectedCount={selectedIds.length}
        onAnalyzeSelected={handleAnalyzeSelected}
        onPostToJira={handlePostToJira}
        isProcessing={isProcessing}
      />

      <IssuesTable
        feedback={feedback}
        isLoading={isLoading}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        onAnalyze={handleAnalyze}
      />
    </div>
  );
}
