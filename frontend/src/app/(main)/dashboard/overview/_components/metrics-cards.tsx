"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ClipboardCheck,
  TrendingUp,
  AlertTriangle,
  Clock,
} from "lucide-react";

interface MetricsCardsProps {
  stats: {
    total_analyzed: number;
    average_score: number;
    issues_below_70: number;
    recent_count_7d: number;
  } | null;
  isLoading: boolean;
}

export function MetricsCards({ stats, isLoading }: MetricsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
              <Skeleton className="mt-1 h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: "Total Analyzed",
      value: stats?.total_analyzed ?? 0,
      description: "Issues analyzed all time",
      icon: ClipboardCheck,
      color: "text-blue-500",
    },
    {
      title: "Average Score",
      value: stats?.average_score?.toFixed(1) ?? "0",
      description: "Quality score average",
      icon: TrendingUp,
      color: stats && stats.average_score >= 70 ? "text-green-500" : "text-yellow-500",
    },
    {
      title: "Needs Improvement",
      value: stats?.issues_below_70 ?? 0,
      description: "Issues scoring below 70",
      icon: AlertTriangle,
      color: "text-orange-500",
    },
    {
      title: "This Week",
      value: stats?.recent_count_7d ?? 0,
      description: "Analyzed in last 7 days",
      icon: Clock,
      color: "text-purple-500",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
            <p className="text-xs text-muted-foreground">{card.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
