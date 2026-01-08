"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { FeedbackSummary } from "@/types/feedback";

interface RecentFeedbackListProps {
  feedback: FeedbackSummary[];
  isLoading: boolean;
}

function getScoreBadgeVariant(score: number): "default" | "secondary" | "destructive" | "outline" {
  if (score >= 80) return "default";
  if (score >= 60) return "secondary";
  return "destructive";
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function RecentFeedbackList({
  feedback,
  isLoading,
}: RecentFeedbackListProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Feedback</CardTitle>
          <CardDescription>Latest issue analyses</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-48" />
                </div>
                <Skeleton className="h-6 w-12" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Feedback</CardTitle>
        <CardDescription>Latest issue analyses</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          {feedback.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              No feedback yet. Start analyzing issues!
            </div>
          ) : (
            <div className="space-y-4">
              {feedback.map((item) => (
                <Link
                  key={item.id}
                  href={`/dashboard/issues/${item.issue_key}`}
                  className="flex items-center gap-4 rounded-lg border p-3 transition-colors hover:bg-muted/50"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-lg">
                    {item.emoji}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{item.issue_key}</span>
                      {item.issue_type && (
                        <Badge variant="outline" className="text-xs">
                          {item.issue_type}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      {item.issue_summary || "No summary"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(item.created_at)}
                    </p>
                  </div>
                  <Badge variant={getScoreBadgeVariant(item.score)}>
                    {item.score.toFixed(0)}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
