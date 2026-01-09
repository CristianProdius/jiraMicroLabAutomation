"use client";

import { useEffect, useState } from "react";
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
import { Progress } from "@/components/ui/progress";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell } from "recharts";
import { skillsApi } from "@/lib/api/feedback-api";
import type { SkillGapAnalysis } from "@/types/feedback";
import {
  Target,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
} from "lucide-react";

export default function SkillsAnalysisPage() {
  const [period, setPeriod] = useState("30");
  const [analysis, setAnalysis] = useState<SkillGapAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const data = await skillsApi.getAnalysis(Number(period));
        setAnalysis(data);
      } catch (error) {
        console.error("Failed to load skill analysis:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [period]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "#22c55e"; // green-500
    if (score >= 70) return "#eab308"; // yellow-500
    if (score >= 60) return "#f97316"; // orange-500
    return "#ef4444"; // red-500
  };

  const chartConfig = {
    score: {
      label: "Average Score",
      color: "hsl(var(--chart-1))",
    },
  };

  // Transform data for the bar chart
  const chartData = analysis
    ? Object.entries(analysis.overall_stats)
        .map(([ruleId, score]) => ({
          ruleId,
          name: analysis.rule_names[ruleId] || ruleId,
          score,
          fill: getScoreColor(score),
        }))
        .sort((a, b) => a.score - b.score)
    : [];

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Target className="h-6 w-6" />
            Skill Gap Analysis
          </h1>
          <p className="text-muted-foreground">
            Identify class-wide strengths and areas for improvement.
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

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : analysis ? (
        <>
          {/* Overview Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Skills Overview</CardTitle>
              <CardDescription>
                Class average score per rubric criterion (sorted by performance)
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              {chartData.length === 0 ? (
                <div className="flex h-full items-center justify-center text-muted-foreground">
                  No data available
                </div>
              ) : (
                <ChartContainer config={chartConfig} className="h-full w-full">
                  <BarChart data={chartData} layout="vertical" margin={{ left: 100 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" domain={[0, 100]} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="score" radius={4}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              )}
            </CardContent>
          </Card>

          {/* Weak and Strong Areas */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Weak Areas */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                  <CardTitle>Areas Needing Attention</CardTitle>
                </div>
                <CardDescription>Skills with lowest class average</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analysis.weak_areas.map((area) => (
                    <Link
                      key={area.rule_id}
                      href={`/dashboard/skills/${area.rule_id}`}
                      className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="font-medium">{area.rule_name}</p>
                          <span
                            className={`font-bold ${
                              area.average_score >= 70 ? "text-yellow-500" : "text-red-500"
                            }`}
                          >
                            {area.average_score.toFixed(0)}%
                          </span>
                        </div>
                        <div className="mt-2">
                          <Progress
                            value={area.average_score}
                            className="h-2"
                          />
                        </div>
                        <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{area.students_struggling} students struggling</span>
                          <span className="flex items-center gap-1">
                            {area.improvement_trend > 0 ? (
                              <TrendingUp className="h-3 w-3 text-green-500" />
                            ) : area.improvement_trend < 0 ? (
                              <TrendingDown className="h-3 w-3 text-red-500" />
                            ) : null}
                            {area.improvement_trend > 0 ? "+" : ""}
                            {area.improvement_trend.toFixed(1)} trend
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="ml-4 h-5 w-5 text-muted-foreground" />
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Strong Areas */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <CardTitle>Strong Areas</CardTitle>
                </div>
                <CardDescription>Skills with highest class average</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analysis.strong_areas.map((area) => (
                    <Link
                      key={area.rule_id}
                      href={`/dashboard/skills/${area.rule_id}`}
                      className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="font-medium">{area.rule_name}</p>
                          <span className="font-bold text-green-500">
                            {area.average_score.toFixed(0)}%
                          </span>
                        </div>
                        <div className="mt-2">
                          <Progress
                            value={area.average_score}
                            className="h-2"
                          />
                        </div>
                        <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{area.students_struggling} students below 70%</span>
                          <span className="flex items-center gap-1">
                            {area.improvement_trend > 0 ? (
                              <TrendingUp className="h-3 w-3 text-green-500" />
                            ) : area.improvement_trend < 0 ? (
                              <TrendingDown className="h-3 w-3 text-red-500" />
                            ) : null}
                            {area.improvement_trend > 0 ? "+" : ""}
                            {area.improvement_trend.toFixed(1)} trend
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="ml-4 h-5 w-5 text-muted-foreground" />
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Students with Skill Gaps */}
          <Card>
            <CardHeader>
              <CardTitle>Students with Skill Gaps</CardTitle>
              <CardDescription>
                Students performing below class average in specific areas
              </CardDescription>
            </CardHeader>
            <CardContent>
              {analysis.student_gaps.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-muted-foreground">
                  No significant skill gaps identified
                </div>
              ) : (
                <div className="space-y-3">
                  {analysis.student_gaps.map((student) => (
                    <Link
                      key={student.assignee}
                      href={`/dashboard/students/${encodeURIComponent(student.assignee)}`}
                      className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 font-semibold text-primary">
                          {student.assignee.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium">{student.assignee}</p>
                          <p className="text-sm text-muted-foreground">
                            {student.skill_gaps.length} skill
                            {student.skill_gaps.length !== 1 ? "s" : ""} below class average
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <Badge variant="destructive">
                            {student.biggest_gap_rule}
                          </Badge>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {student.biggest_gap_amount.toFixed(0)} pts below avg
                          </p>
                        </div>
                        <ChevronRight className="h-5 w-5 text-muted-foreground" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="flex h-64 items-center justify-center">
            <p className="text-muted-foreground">No analysis data available</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
