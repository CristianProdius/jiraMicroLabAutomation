"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, ExternalLink, Play, Check } from "lucide-react";
import type { FeedbackSummary } from "@/types/feedback";

interface IssuesTableProps {
  feedback: FeedbackSummary[];
  isLoading: boolean;
  selectedIds: number[];
  onSelectionChange: (ids: number[]) => void;
  onAnalyze?: (issueKey: string) => void;
}

function getScoreBadgeVariant(score: number): "default" | "secondary" | "destructive" | "outline" {
  if (score >= 80) return "default";
  if (score >= 60) return "secondary";
  return "destructive";
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function IssuesTable({
  feedback,
  isLoading,
  selectedIds,
  onSelectionChange,
  onAnalyze,
}: IssuesTableProps) {
  const allSelected = feedback.length > 0 && selectedIds.length === feedback.length;
  const someSelected = selectedIds.length > 0 && selectedIds.length < feedback.length;

  const toggleAll = () => {
    if (allSelected) {
      onSelectionChange([]);
    } else {
      onSelectionChange(feedback.map((f) => f.id));
    }
  };

  const toggleOne = (id: number) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((i) => i !== id));
    } else {
      onSelectionChange([...selectedIds, id]);
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]" />
              <TableHead>Issue</TableHead>
              <TableHead>Summary</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Assignee</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="w-[40px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {[...Array(5)].map((_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-4 w-4" /></TableCell>
                <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                <TableCell><Skeleton className="h-4 w-48" /></TableCell>
                <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                <TableCell><Skeleton className="h-4 w-4" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (feedback.length === 0) {
    return (
      <div className="rounded-md border p-8 text-center">
        <p className="text-muted-foreground">No issues analyzed yet.</p>
        <p className="text-sm text-muted-foreground mt-1">
          Search for issues and analyze them to see feedback here.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40px]">
              <Checkbox
                checked={allSelected}
                ref={(el) => {
                  if (el) (el as HTMLButtonElement).dataset.state = someSelected ? "indeterminate" : allSelected ? "checked" : "unchecked";
                }}
                onCheckedChange={toggleAll}
              />
            </TableHead>
            <TableHead>Issue</TableHead>
            <TableHead className="max-w-[300px]">Summary</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Assignee</TableHead>
            <TableHead>Date</TableHead>
            <TableHead className="w-[40px]" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {feedback.map((item) => (
            <TableRow key={item.id}>
              <TableCell>
                <Checkbox
                  checked={selectedIds.includes(item.id)}
                  onCheckedChange={() => toggleOne(item.id)}
                />
              </TableCell>
              <TableCell>
                <Link
                  href={`/dashboard/issues/${item.issue_key}`}
                  className="font-medium hover:underline flex items-center gap-1"
                >
                  {item.emoji} {item.issue_key}
                </Link>
              </TableCell>
              <TableCell className="max-w-[300px]">
                <span className="truncate block">
                  {item.issue_summary || "No summary"}
                </span>
              </TableCell>
              <TableCell>
                {item.issue_type && (
                  <Badge variant="outline">{item.issue_type}</Badge>
                )}
              </TableCell>
              <TableCell>
                <Badge variant={getScoreBadgeVariant(item.score)}>
                  <span className={getScoreColor(item.score)}>
                    {item.score.toFixed(0)}
                  </span>
                </Badge>
              </TableCell>
              <TableCell>
                <span className="text-sm text-muted-foreground">
                  {item.assignee || "Unassigned"}
                </span>
              </TableCell>
              <TableCell>
                <span className="text-sm text-muted-foreground">
                  {formatDate(item.created_at)}
                </span>
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem asChild>
                      <Link href={`/dashboard/issues/${item.issue_key}`}>
                        <ExternalLink className="mr-2 h-4 w-4" />
                        View Details
                      </Link>
                    </DropdownMenuItem>
                    {onAnalyze && (
                      <DropdownMenuItem onClick={() => onAnalyze(item.issue_key)}>
                        <Play className="mr-2 h-4 w-4" />
                        Re-analyze
                      </DropdownMenuItem>
                    )}
                    {item.was_posted_to_jira ? (
                      <DropdownMenuItem disabled>
                        <Check className="mr-2 h-4 w-4" />
                        Posted to Jira
                      </DropdownMenuItem>
                    ) : (
                      <DropdownMenuItem>
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Post to Jira
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
