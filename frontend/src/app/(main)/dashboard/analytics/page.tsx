"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { feedbackApi } from "@/lib/api/feedback-api";
import type { ScoreTrendItem, TeamPerformanceItem } from "@/types/feedback";
import { TrendingUp, TrendingDown, Minus, Users } from "lucide-react";

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("30");
  const [trends, setTrends] = useState<ScoreTrendItem[]>([]);
  const [teamPerformance, setTeamPerformance] = useState<TeamPerformanceItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [trendsData, teamData] = await Promise.all([
          feedbackApi.getTrends(Number(period)),
          feedbackApi.getTeamPerformance(Number(period)),
        ]);
        setTrends(trendsData.trends);
        setTeamPerformance(teamData.members);
      } catch (error) {
        console.error("Failed to load analytics:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [period]);

  const chartConfig = {
    average_score: {
      label: "Average Score",
      color: "hsl(var(--chart-1))",
    },
    count: {
      label: "Issues Analyzed",
      color: "hsl(var(--chart-2))",
    },
  };

  const getTrendIcon = (trend: number) => {
    if (trend > 2) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (trend < -2) return <TrendingDown className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-muted-foreground" />;
  };

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Track quality trends and team performance over time.
          </p>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Score Trends */}
      <Card>
        <CardHeader>
          <CardTitle>Score Trends</CardTitle>
          <CardDescription>
            Average quality score over the selected period
          </CardDescription>
        </CardHeader>
        <CardContent className="h-[350px]">
          {isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : trends.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              No data available for this period
            </div>
          ) : (
            <ChartContainer config={chartConfig} className="h-full w-full">
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return date.toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    });
                  }}
                />
                <YAxis domain={[0, 100]} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Line
                  type="monotone"
                  dataKey="average_score"
                  stroke="var(--color-average_score)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      {/* Analysis Volume */}
      <Card>
        <CardHeader>
          <CardTitle>Analysis Volume</CardTitle>
          <CardDescription>
            Number of issues analyzed per day
          </CardDescription>
        </CardHeader>
        <CardContent className="h-[250px]">
          {isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : trends.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              No data available for this period
            </div>
          ) : (
            <ChartContainer config={chartConfig} className="h-full w-full">
              <BarChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return date.toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    });
                  }}
                />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={4} />
              </BarChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      {/* Team Performance */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            <CardTitle>Team Performance</CardTitle>
          </div>
          <CardDescription>
            Average scores by team member
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : teamPerformance.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              No team data available
            </div>
          ) : (
            <div className="space-y-4">
              {teamPerformance.map((member) => (
                <div
                  key={member.assignee}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <p className="font-medium">{member.assignee}</p>
                    <p className="text-sm text-muted-foreground">
                      {member.issues_count} issues analyzed
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-2xl font-bold">
                        {member.average_score.toFixed(0)}
                      </p>
                      <p className="text-xs text-muted-foreground">avg score</p>
                    </div>
                    <div className="flex items-center gap-1">
                      {getTrendIcon(member.trend)}
                      <span
                        className={`text-sm ${
                          member.trend > 2
                            ? "text-green-500"
                            : member.trend < -2
                            ? "text-red-500"
                            : "text-muted-foreground"
                        }`}
                      >
                        {member.trend > 0 ? "+" : ""}
                        {member.trend.toFixed(1)}
                      </span>
                    </div>
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
