"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ScoreGauge } from "./_components/score-gauge";
import { RubricBreakdown } from "./_components/rubric-breakdown";
import { FeedbackCards } from "./_components/feedback-cards";
import { feedbackApi, issuesApi } from "@/lib/api/feedback-api";
import type { FeedbackDetail } from "@/types/feedback";
import {
  ArrowLeft,
  ExternalLink,
  Play,
  Send,
  Check,
  Loader2,
} from "lucide-react";

export default function IssueDetailPage() {
  const params = useParams();
  const router = useRouter();
  const issueKey = params.key as string;

  const [feedback, setFeedback] = useState<FeedbackDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPosting, setIsPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadFeedback() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await feedbackApi.getByIssueKey(issueKey);
        setFeedback(data);
      } catch (err) {
        setError("Failed to load feedback");
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }

    loadFeedback();
  }, [issueKey]);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      const result = await issuesApi.analyze(issueKey);
      setFeedback(result);
    } catch (err) {
      setError("Analysis failed");
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handlePostToJira = async () => {
    if (!feedback) return;
    setIsPosting(true);
    try {
      await feedbackApi.postToJira(feedback.id);
      setFeedback({ ...feedback, was_posted_to_jira: true });
    } catch (err) {
      setError("Failed to post to Jira");
      console.error(err);
    } finally {
      setIsPosting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="@container/main flex flex-col gap-4 md:gap-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-8 w-48" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-64" />
          <Skeleton className="h-64 md:col-span-2" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  if (error && !feedback) {
    return (
      <div className="@container/main flex flex-col gap-4 md:gap-6">
        <Button variant="ghost" onClick={() => router.back()} className="w-fit">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">{error}</p>
          <p className="text-sm text-muted-foreground mt-2">
            This issue may not have been analyzed yet.
          </p>
          <Button onClick={handleAnalyze} className="mt-4" disabled={isAnalyzing}>
            {isAnalyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Analyze Now
              </>
            )}
          </Button>
        </Card>
      </div>
    );
  }

  if (!feedback) {
    return (
      <div className="@container/main flex flex-col gap-4 md:gap-6">
        <Button variant="ghost" onClick={() => router.back()} className="w-fit">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">
            No feedback found for {issueKey}
          </p>
          <Button onClick={handleAnalyze} className="mt-4" disabled={isAnalyzing}>
            {isAnalyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Analyze Now
              </>
            )}
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{feedback.issue_key}</h1>
              {feedback.issue_type && (
                <Badge variant="outline">{feedback.issue_type}</Badge>
              )}
              {feedback.issue_status && (
                <Badge variant="secondary">{feedback.issue_status}</Badge>
              )}
            </div>
            <p className="text-muted-foreground">
              {feedback.issue_summary || "No summary"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleAnalyze} disabled={isAnalyzing}>
            {isAnalyzing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Re-analyze
          </Button>
          {feedback.was_posted_to_jira ? (
            <Button variant="outline" disabled>
              <Check className="mr-2 h-4 w-4" />
              Posted to Jira
            </Button>
          ) : (
            <Button onClick={handlePostToJira} disabled={isPosting}>
              {isPosting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              Post to Jira
            </Button>
          )}
        </div>
      </div>

      {/* Score and Breakdown */}
      <div className="grid gap-4 md:grid-cols-3">
        <ScoreGauge score={feedback.score} emoji={feedback.emoji} />
        <div className="md:col-span-2">
          <RubricBreakdown breakdown={feedback.rubric_breakdown} />
        </div>
      </div>

      {/* Overall Assessment */}
      <Card>
        <CardHeader>
          <CardTitle>Overall Assessment</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">{feedback.overall_assessment}</p>
        </CardContent>
      </Card>

      {/* Feedback Cards */}
      <FeedbackCards
        strengths={feedback.strengths}
        improvements={feedback.improvements}
        suggestions={feedback.suggestions}
      />

      {/* Improved AC */}
      {feedback.improved_ac && (
        <Card>
          <CardHeader>
            <CardTitle>Improved Acceptance Criteria</CardTitle>
            <CardDescription>
              AI-refined acceptance criteria suggestion
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg">
              {feedback.improved_ac}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Metadata</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-2 sm:grid-cols-2 md:grid-cols-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Assignee</dt>
              <dd className="font-medium">{feedback.assignee || "Unassigned"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Labels</dt>
              <dd className="font-medium">
                {feedback.labels?.length
                  ? feedback.labels.join(", ")
                  : "None"}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Analyzed</dt>
              <dd className="font-medium">
                {new Date(feedback.created_at).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Telegram</dt>
              <dd className="font-medium">
                {feedback.was_sent_to_telegram ? "Sent" : "Not sent"}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
