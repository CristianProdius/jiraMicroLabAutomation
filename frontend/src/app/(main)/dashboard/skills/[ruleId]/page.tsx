"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { skillsApi } from "@/lib/api/feedback-api";
import type { SkillDetail } from "@/types/feedback";
import {
  ArrowLeft,
  Lightbulb,
  Users,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";

const COLORS = ["#22c55e", "#84cc16", "#eab308", "#f97316", "#ef4444", "#dc2626"];
const DISTRIBUTION_ORDER = ["90-100", "80-89", "70-79", "60-69", "50-59", "0-49"];

export default function SkillDetailPage() {
  const params = useParams();
  const ruleId = params.ruleId as string;
  const [period, setPeriod] = useState("30");
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const data = await skillsApi.getDetail(ruleId, Number(period));
        setDetail(data);
      } catch (error) {
        console.error("Failed to load skill detail:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [ruleId, period]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600 dark:text-green-400";
    if (score >= 70) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const chartConfig = {
    average_score: {
      label: "Average Score",
      color: "hsl(var(--chart-1))",
    },
  };

  // Filter out days with no data for the line chart
  const trendData = detail?.trend_data.filter((d) => d.sample_size > 0) || [];

  // Transform distribution data for pie chart
  const distributionData = detail
    ? DISTRIBUTION_ORDER.map((range, index) => ({
        name: range,
        value: detail.score_distribution[range] || 0,
        color: COLORS[index],
      })).filter((d) => d.value > 0)
    : [];

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/skills">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              {isLoading ? <Skeleton className="h-8 w-48" /> : detail?.rule_name}
            </h1>
            <p className="text-muted-foreground">Skill Analysis Detail</p>
          </div>
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

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : detail ? (
        <>
          {/* Stats Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Class Average</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-4xl font-bold ${getScoreColor(detail.class_average)}`}>
                {detail.class_average.toFixed(1)}%
              </div>
            </CardContent>
          </Card>

          {/* Charts Row */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Trend Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Score Trend</CardTitle>
                <CardDescription>Class performance over time</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                {trendData.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    No trend data available
                  </div>
                ) : (
                  <ChartContainer config={chartConfig} className="h-full w-full">
                    <LineChart data={trendData}>
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
                        dot={{ r: 4 }}
                      />
                    </LineChart>
                  </ChartContainer>
                )}
              </CardContent>
            </Card>

            {/* Distribution Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Score Distribution</CardTitle>
                <CardDescription>How scores are distributed</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                {distributionData.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    No distribution data available
                  </div>
                ) : (
                  <ChartContainer config={chartConfig} className="h-full w-full">
                    <PieChart>
                      <Pie
                        data={distributionData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) =>
                          `${name}: ${(percent * 100).toFixed(0)}%`
                        }
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {distributionData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <ChartTooltip content={<ChartTooltipContent />} />
                    </PieChart>
                  </ChartContainer>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Students by Performance */}
          <div className="grid gap-4 lg:grid-cols-3">
            {/* Excellent */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <CardTitle className="text-lg">Excellent (90%+)</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {detail.students_by_performance.excellent?.length === 0 ? (
                  <p className="text-muted-foreground">No students</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {detail.students_by_performance.excellent?.map((student) => (
                      <Link
                        key={student}
                        href={`/dashboard/students/${encodeURIComponent(student)}`}
                      >
                        <Badge variant="secondary" className="cursor-pointer hover:bg-green-100">
                          {student}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Good */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-yellow-500" />
                  <CardTitle className="text-lg">Good (70-89%)</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {detail.students_by_performance.good?.length === 0 ? (
                  <p className="text-muted-foreground">No students</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {detail.students_by_performance.good?.map((student) => (
                      <Link
                        key={student}
                        href={`/dashboard/students/${encodeURIComponent(student)}`}
                      >
                        <Badge variant="secondary" className="cursor-pointer hover:bg-yellow-100">
                          {student}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Struggling */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <CardTitle className="text-lg">Needs Help (&lt;70%)</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {detail.students_by_performance.struggling?.length === 0 ? (
                  <p className="text-muted-foreground">No students</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {detail.students_by_performance.struggling?.map((student) => (
                      <Link
                        key={student}
                        href={`/dashboard/students/${encodeURIComponent(student)}`}
                      >
                        <Badge variant="destructive" className="cursor-pointer">
                          {student}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Improvement Suggestions */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                <CardTitle>Improvement Tips</CardTitle>
              </div>
              <CardDescription>
                Suggestions for improving scores in this area
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {detail.improvement_suggestions.map((suggestion, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                      {index + 1}
                    </span>
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="flex h-64 items-center justify-center">
            <p className="text-muted-foreground">Skill not found</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
