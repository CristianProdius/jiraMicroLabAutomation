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
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from "recharts";
import { studentsApi } from "@/lib/api/feedback-api";
import type { StudentProgress, SkillRadarData } from "@/types/feedback";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  Trophy,
  Target,
  Award,
  Flame,
  Star,
} from "lucide-react";

export default function StudentDetailPage() {
  const params = useParams();
  const assignee = decodeURIComponent(params.assignee as string);
  const [period, setPeriod] = useState("90");
  const [progress, setProgress] = useState<StudentProgress | null>(null);
  const [radarData, setRadarData] = useState<SkillRadarData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [progressData, radar] = await Promise.all([
          studentsApi.getProgress(assignee, Number(period)),
          studentsApi.getSkillRadar(assignee, Number(period)),
        ]);
        setProgress(progressData);
        setRadarData(radar);
      } catch (error) {
        console.error("Failed to load student data:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [assignee, period]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600 dark:text-green-400";
    if (score >= 70) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getMilestoneIcon = (type: string) => {
    switch (type) {
      case "first_passing":
        return <Trophy className="h-5 w-5 text-yellow-500" />;
      case "perfect_score":
        return <Star className="h-5 w-5 text-yellow-500" />;
      case "streak":
        return <Flame className="h-5 w-5 text-orange-500" />;
      case "improvement":
        return <TrendingUp className="h-5 w-5 text-green-500" />;
      default:
        return <Award className="h-5 w-5 text-blue-500" />;
    }
  };

  const chartConfig = {
    average_score: {
      label: "Score",
      color: "hsl(var(--chart-1))",
    },
    student: {
      label: "Student",
      color: "hsl(var(--chart-1))",
    },
    class: {
      label: "Class Average",
      color: "hsl(var(--chart-2))",
    },
  };

  // Transform radar data for recharts
  const radarChartData = radarData
    ? radarData.skills.map((skill, index) => ({
        skill,
        student: radarData.student_scores[index],
        class: radarData.class_average_scores[index],
      }))
    : [];

  // Filter out days with no data for the line chart
  const trendData = progress?.score_trend.filter((d) => d.count > 0) || [];

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/students">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{assignee}</h1>
            <p className="text-muted-foreground">Student Progress Dashboard</p>
          </div>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
            <SelectItem value="180">Last 6 months</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : progress ? (
        <>
          {/* Stats Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Average Score</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${getScoreColor(progress.average_score)}`}>
                  {progress.average_score.toFixed(1)}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Issues Analyzed</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{progress.total_issues}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Passing Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{progress.passing_rate.toFixed(0)}%</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Milestones</CardTitle>
                <Trophy className="h-4 w-4 text-yellow-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{progress.milestones.length}</div>
              </CardContent>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Score Timeline */}
            <Card>
              <CardHeader>
                <CardTitle>Score Timeline</CardTitle>
                <CardDescription>Quality scores over time</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                {trendData.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    No data available
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

            {/* Skill Radar */}
            <Card>
              <CardHeader>
                <CardTitle>Skill Comparison</CardTitle>
                <CardDescription>Student vs Class Average</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                {radarChartData.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    No skill data available
                  </div>
                ) : (
                  <ChartContainer config={chartConfig} className="h-full w-full">
                    <RadarChart data={radarChartData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="skill" tick={{ fontSize: 10 }} />
                      <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                      <Radar
                        name="Student"
                        dataKey="student"
                        stroke="var(--color-student)"
                        fill="var(--color-student)"
                        fillOpacity={0.3}
                      />
                      <Radar
                        name="Class Average"
                        dataKey="class"
                        stroke="var(--color-class)"
                        fill="var(--color-class)"
                        fillOpacity={0.1}
                      />
                      <Legend />
                    </RadarChart>
                  </ChartContainer>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Skill Breakdown & Comparison */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Skill Breakdown</CardTitle>
                <CardDescription>Performance per rubric criterion</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(progress.skill_breakdown).map(([ruleId, score]) => {
                    const comparison = progress.class_comparison[ruleId] || 0;
                    const ruleName =
                      radarData?.skills[radarData.skill_ids.indexOf(ruleId)] || ruleId;

                    return (
                      <div key={ruleId} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{ruleName}</span>
                          <div className="flex items-center gap-2">
                            <span className={`font-bold ${getScoreColor(score)}`}>
                              {score.toFixed(0)}%
                            </span>
                            <span
                              className={`text-xs ${
                                comparison > 0 ? "text-green-500" : comparison < 0 ? "text-red-500" : "text-muted-foreground"
                              }`}
                            >
                              {comparison > 0 ? "+" : ""}
                              {comparison.toFixed(0)} vs class
                            </span>
                          </div>
                        </div>
                        <div className="h-2 rounded-full bg-muted">
                          <div
                            className={`h-2 rounded-full ${
                              score >= 80
                                ? "bg-green-500"
                                : score >= 70
                                ? "bg-yellow-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${Math.min(score, 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Milestones */}
            <Card>
              <CardHeader>
                <CardTitle>Achievements</CardTitle>
                <CardDescription>Milestones and accomplishments</CardDescription>
              </CardHeader>
              <CardContent>
                {progress.milestones.length === 0 ? (
                  <div className="flex h-32 items-center justify-center text-muted-foreground">
                    No milestones achieved yet
                  </div>
                ) : (
                  <div className="space-y-4">
                    {progress.milestones.map((milestone, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 rounded-lg border p-3"
                      >
                        <div className="mt-0.5">{getMilestoneIcon(milestone.type)}</div>
                        <div className="flex-1">
                          <p className="font-medium">{milestone.title}</p>
                          <p className="text-sm text-muted-foreground">
                            {milestone.description}
                          </p>
                          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                            <span>
                              {new Date(milestone.achieved_at).toLocaleDateString()}
                            </span>
                            {milestone.issue_key && (
                              <Badge variant="outline" className="text-xs">
                                {milestone.issue_key}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest analyzed issues</CardDescription>
            </CardHeader>
            <CardContent>
              {progress.recent_feedbacks.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-muted-foreground">
                  No recent activity
                </div>
              ) : (
                <div className="space-y-3">
                  {progress.recent_feedbacks.map((feedback) => (
                    <Link
                      key={feedback.id}
                      href={`/dashboard/issues/${feedback.issue_key}`}
                      className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{feedback.emoji}</span>
                        <div>
                          <p className="font-medium">{feedback.issue_key}</p>
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {feedback.issue_summary}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className={`text-lg font-bold ${getScoreColor(feedback.score)}`}>
                          {feedback.score.toFixed(0)}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {new Date(feedback.created_at).toLocaleDateString()}
                        </span>
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
            <p className="text-muted-foreground">Student not found</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
