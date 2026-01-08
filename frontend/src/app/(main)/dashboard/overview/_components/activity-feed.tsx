"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useWebSocket } from "@/lib/websocket";
import type { WebSocketEvent } from "@/types/feedback";
import { useEffect, useState } from "react";
import { Wifi, WifiOff } from "lucide-react";

interface ActivityItem {
  id: string;
  type: string;
  message: string;
  timestamp: string;
  issue_key?: string;
  score?: number;
}

function eventToActivity(event: WebSocketEvent): ActivityItem | null {
  const id = `${event.event}-${event.timestamp}`;
  const timestamp = new Date(event.timestamp).toLocaleTimeString();

  switch (event.event) {
    case "job_started":
      return {
        id,
        type: "job",
        message: `Batch analysis started`,
        timestamp,
      };
    case "job_progress":
      return {
        id,
        type: "progress",
        message: `Processing ${event.data.current_issue} (${event.data.processed}/${event.data.total})`,
        timestamp,
        issue_key: event.data.current_issue as string,
      };
    case "issue_complete":
      return {
        id,
        type: "success",
        message: `Analyzed ${event.data.issue_key}`,
        timestamp,
        issue_key: event.data.issue_key as string,
        score: event.data.score as number,
      };
    case "issue_failed":
      return {
        id,
        type: "error",
        message: `Failed to analyze ${event.data.issue_key}`,
        timestamp,
        issue_key: event.data.issue_key as string,
      };
    case "job_completed":
      return {
        id,
        type: "success",
        message: `Batch analysis completed: ${event.data.processed} issues`,
        timestamp,
      };
    case "job_failed":
      return {
        id,
        type: "error",
        message: `Batch analysis failed: ${event.data.error}`,
        timestamp,
      };
    default:
      return null;
  }
}

function getTypeBadgeVariant(type: string): "default" | "secondary" | "destructive" | "outline" {
  switch (type) {
    case "success":
      return "default";
    case "error":
      return "destructive";
    case "progress":
      return "secondary";
    default:
      return "outline";
  }
}

export function ActivityFeed() {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const { isConnected, events } = useWebSocket("/ws/live");

  useEffect(() => {
    if (events.length === 0) return;

    const lastEvent = events[events.length - 1];
    const activity = eventToActivity(lastEvent);
    if (activity) {
      setActivities((prev) => [activity, ...prev.slice(0, 49)]);
    }
  }, [events]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Live Activity</CardTitle>
            <CardDescription>Real-time analysis events</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <>
                <Wifi className="h-4 w-4 text-green-500" />
                <span className="text-xs text-green-500">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Disconnected</span>
              </>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          {activities.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
              {isConnected
                ? "Waiting for activity..."
                : "Connect to see live updates"}
            </div>
          ) : (
            <div className="space-y-3">
              {activities.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start gap-3 rounded-lg border p-2"
                >
                  <Badge variant={getTypeBadgeVariant(activity.type)} className="mt-0.5">
                    {activity.type}
                  </Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{activity.message}</p>
                    {activity.score !== undefined && (
                      <p className="text-xs text-muted-foreground">
                        Score: {activity.score.toFixed(0)}
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {activity.timestamp}
                  </span>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
