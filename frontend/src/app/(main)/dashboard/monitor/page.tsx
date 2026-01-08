"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Wifi, WifiOff, Play, Square, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { useWebSocket } from "@/lib/websocket";
import { issuesApi, jobsApi } from "@/lib/api/feedback-api";
import type { AnalysisJob, WebSocketEvent } from "@/types/feedback";

interface LogEntry {
  id: string;
  timestamp: string;
  type: "info" | "success" | "error" | "progress";
  message: string;
  issueKey?: string;
  score?: number;
}

export default function MonitorPage() {
  const [jql, setJql] = useState("");
  const [maxIssues, setMaxIssues] = useState(20);
  const [dryRun, setDryRun] = useState(true);
  const [postToJira, setPostToJira] = useState(false);
  const [sendTelegram, setSendTelegram] = useState(false);

  const [activeJob, setActiveJob] = useState<AnalysisJob | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [recentJobs, setRecentJobs] = useState<AnalysisJob[]>([]);

  const handleEvent = useCallback((event: WebSocketEvent) => {
    const timestamp = new Date().toLocaleTimeString();
    const id = `${Date.now()}-${Math.random()}`;

    switch (event.event) {
      case "job_started":
        setLogs((prev) => [
          { id, timestamp, type: "info", message: `Job started: ${event.data.job_id}` },
          ...prev,
        ]);
        break;
      case "job_progress":
        setLogs((prev) => [
          {
            id,
            timestamp,
            type: "progress",
            message: `Processing ${event.data.current_issue} (${event.data.processed}/${event.data.total})`,
            issueKey: event.data.current_issue as string,
          },
          ...prev,
        ]);
        if (activeJob) {
          setActiveJob({
            ...activeJob,
            processed_issues: event.data.processed as number,
            total_issues: event.data.total as number,
          });
        }
        break;
      case "issue_complete":
        setLogs((prev) => [
          {
            id,
            timestamp,
            type: "success",
            message: `Completed ${event.data.issue_key} - Score: ${(event.data.score as number).toFixed(0)}`,
            issueKey: event.data.issue_key as string,
            score: event.data.score as number,
          },
          ...prev,
        ]);
        break;
      case "issue_failed":
        setLogs((prev) => [
          {
            id,
            timestamp,
            type: "error",
            message: `Failed ${event.data.issue_key}: ${event.data.error}`,
            issueKey: event.data.issue_key as string,
          },
          ...prev,
        ]);
        break;
      case "job_completed":
        setLogs((prev) => [
          {
            id,
            timestamp,
            type: "success",
            message: `Job completed! Processed ${event.data.processed} issues`,
          },
          ...prev,
        ]);
        setActiveJob(null);
        loadRecentJobs();
        break;
      case "job_failed":
        setLogs((prev) => [
          {
            id,
            timestamp,
            type: "error",
            message: `Job failed: ${event.data.error}`,
          },
          ...prev,
        ]);
        setActiveJob(null);
        loadRecentJobs();
        break;
    }
  }, [activeJob]);

  const wsEndpoint = activeJob ? `/ws/analysis/${activeJob.job_id}` : "/ws/live";
  const { isConnected } = useWebSocket(wsEndpoint as `/ws/analysis/${string}`, handleEvent);

  const loadRecentJobs = async () => {
    try {
      const jobs = await jobsApi.list(5);
      setRecentJobs(jobs);
    } catch (error) {
      console.error("Failed to load jobs:", error);
    }
  };

  useEffect(() => {
    loadRecentJobs();
  }, []);

  const handleStart = async () => {
    if (!jql.trim()) return;

    setIsStarting(true);
    setLogs([]);

    try {
      const job = await issuesApi.batchAnalyze({
        jql: jql.trim(),
        max_issues: maxIssues,
        dry_run: dryRun,
        post_to_jira: postToJira,
        send_telegram: sendTelegram,
      });
      setActiveJob(job);
      setLogs([
        {
          id: "start",
          timestamp: new Date().toLocaleTimeString(),
          type: "info",
          message: `Started batch analysis job: ${job.job_id}`,
        },
      ]);
    } catch (error) {
      setLogs([
        {
          id: "error",
          timestamp: new Date().toLocaleTimeString(),
          type: "error",
          message: `Failed to start job: ${error instanceof Error ? error.message : "Unknown error"}`,
        },
      ]);
    } finally {
      setIsStarting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "running":
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const progress = activeJob?.total_issues
    ? (activeJob.processed_issues / activeJob.total_issues) * 100
    : 0;

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Live Monitor</h1>
          <p className="text-muted-foreground">
            Run batch analysis and monitor progress in real-time.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-sm text-green-500">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Disconnected</span>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Start Job Card */}
        <Card>
          <CardHeader>
            <CardTitle>Start Batch Analysis</CardTitle>
            <CardDescription>
              Analyze multiple issues using JQL query
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="jql">JQL Query</Label>
              <Input
                id="jql"
                placeholder='e.g., project = DEMO AND status = "To Do"'
                value={jql}
                onChange={(e) => setJql(e.target.value)}
                disabled={!!activeJob}
              />
            </div>

            <div>
              <Label htmlFor="max-issues">Max Issues</Label>
              <Input
                id="max-issues"
                type="number"
                value={maxIssues}
                onChange={(e) => setMaxIssues(Number(e.target.value))}
                min={1}
                max={100}
                disabled={!!activeJob}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="dry-run">Dry Run (no posting)</Label>
              <Switch
                id="dry-run"
                checked={dryRun}
                onCheckedChange={setDryRun}
                disabled={!!activeJob}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="post-jira">Post to Jira</Label>
              <Switch
                id="post-jira"
                checked={postToJira}
                onCheckedChange={setPostToJira}
                disabled={!!activeJob || dryRun}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="telegram">Send Telegram</Label>
              <Switch
                id="telegram"
                checked={sendTelegram}
                onCheckedChange={setSendTelegram}
                disabled={!!activeJob || dryRun}
              />
            </div>

            <Button
              className="w-full"
              onClick={handleStart}
              disabled={isStarting || !!activeJob || !jql.trim()}
            >
              {isStarting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : activeJob ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Start Analysis
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Progress Card */}
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
            <CardDescription>
              {activeJob
                ? `Job: ${activeJob.job_id.slice(0, 8)}...`
                : "No active job"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {activeJob ? (
              <>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>
                      {activeJob.processed_issues} / {activeJob.total_issues || "?"} issues
                    </span>
                    <span>{progress.toFixed(0)}%</span>
                  </div>
                  <Progress value={progress} />
                </div>

                <div className="flex gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Status: </span>
                    <Badge variant="secondary">{activeJob.status}</Badge>
                  </div>
                  {activeJob.failed_issues > 0 && (
                    <div>
                      <span className="text-muted-foreground">Failed: </span>
                      <Badge variant="destructive">{activeJob.failed_issues}</Badge>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex h-24 items-center justify-center text-muted-foreground">
                Start a batch analysis to see progress
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Live Log */}
      <Card>
        <CardHeader>
          <CardTitle>Live Log</CardTitle>
          <CardDescription>Real-time analysis events</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[300px] rounded-md border p-4">
            {logs.length === 0 ? (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                Events will appear here during analysis
              </div>
            ) : (
              <div className="space-y-2 font-mono text-sm">
                {logs.map((log) => (
                  <div
                    key={log.id}
                    className={`flex items-start gap-2 ${
                      log.type === "error"
                        ? "text-red-500"
                        : log.type === "success"
                        ? "text-green-500"
                        : log.type === "progress"
                        ? "text-blue-500"
                        : "text-muted-foreground"
                    }`}
                  >
                    <span className="text-muted-foreground">[{log.timestamp}]</span>
                    <span>{log.message}</span>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Recent Jobs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Jobs</CardTitle>
          <CardDescription>Previously run batch analyses</CardDescription>
        </CardHeader>
        <CardContent>
          {recentJobs.length === 0 ? (
            <div className="flex h-24 items-center justify-center text-muted-foreground">
              No recent jobs
            </div>
          ) : (
            <div className="space-y-2">
              {recentJobs.map((job) => (
                <div
                  key={job.job_id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(job.status)}
                    <div>
                      <p className="font-mono text-sm">
                        {job.job_id.slice(0, 8)}...
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {job.jql?.slice(0, 40) || "No JQL"}
                        {job.jql && job.jql.length > 40 ? "..." : ""}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <p>
                      {job.processed_issues}/{job.total_issues} issues
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
