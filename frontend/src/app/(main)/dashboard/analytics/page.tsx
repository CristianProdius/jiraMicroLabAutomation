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
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { feedbackApi, gradesApi } from "@/lib/api/feedback-api";
import type { ScoreTrendItem, TeamPerformanceItem, GradeExportPreview } from "@/types/feedback";
import { TrendingUp, TrendingDown, Minus, Users, Download, FileSpreadsheet } from "lucide-react";

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("30");
  const [trends, setTrends] = useState<ScoreTrendItem[]>([]);
  const [teamPerformance, setTeamPerformance] = useState<TeamPerformanceItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Grade export state
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportFromDate, setExportFromDate] = useState("");
  const [exportToDate, setExportToDate] = useState("");
  const [exportPreview, setExportPreview] = useState<GradeExportPreview | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

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

  const loadExportPreview = async () => {
    setIsLoadingPreview(true);
    try {
      const preview = await gradesApi.preview({
        from_date: exportFromDate || undefined,
        to_date: exportToDate || undefined,
      });
      setExportPreview(preview);
    } catch (error) {
      console.error("Failed to load export preview:", error);
    } finally {
      setIsLoadingPreview(false);
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const blob = await gradesApi.exportCsv({
        from_date: exportFromDate || undefined,
        to_date: exportToDate || undefined,
      });

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `grades_${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setExportDialogOpen(false);
    } catch (error) {
      console.error("Failed to export grades:", error);
    } finally {
      setIsExporting(false);
    }
  };

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case "A": return "text-green-600 dark:text-green-400";
      case "B": return "text-blue-600 dark:text-blue-400";
      case "C": return "text-yellow-600 dark:text-yellow-400";
      case "D": return "text-orange-600 dark:text-orange-400";
      case "F": return "text-red-600 dark:text-red-400";
      default: return "text-muted-foreground";
    }
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
        <div className="flex items-center gap-2">
          <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" onClick={() => loadExportPreview()}>
                <FileSpreadsheet className="mr-2 h-4 w-4" />
                Export Grades
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Export Grades to CSV</DialogTitle>
                <DialogDescription>
                  Export student grades for gradebook integration. Select a date range to filter.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="from-date">From Date</Label>
                    <Input
                      id="from-date"
                      type="date"
                      value={exportFromDate}
                      onChange={(e) => setExportFromDate(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="to-date">To Date</Label>
                    <Input
                      id="to-date"
                      type="date"
                      value={exportToDate}
                      onChange={(e) => setExportToDate(e.target.value)}
                    />
                  </div>
                </div>
                <Button variant="secondary" onClick={loadExportPreview} disabled={isLoadingPreview}>
                  {isLoadingPreview ? "Loading..." : "Refresh Preview"}
                </Button>

                {exportPreview && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-center">
                      <div className="rounded-lg border p-3">
                        <p className="text-2xl font-bold">{exportPreview.total_students}</p>
                        <p className="text-xs text-muted-foreground">Students</p>
                      </div>
                      <div className="rounded-lg border p-3">
                        <p className="text-2xl font-bold">{exportPreview.class_average.toFixed(1)}</p>
                        <p className="text-xs text-muted-foreground">Class Avg</p>
                      </div>
                    </div>

                    <div className="rounded-lg border">
                      <div className="max-h-[200px] overflow-auto">
                        <table className="w-full text-sm">
                          <thead className="sticky top-0 bg-muted">
                            <tr>
                              <th className="p-2 text-left font-medium">Student</th>
                              <th className="p-2 text-center font-medium">Issues</th>
                              <th className="p-2 text-center font-medium">Avg Score</th>
                              <th className="p-2 text-center font-medium">Grade</th>
                            </tr>
                          </thead>
                          <tbody>
                            {exportPreview.records.map((student) => (
                              <tr key={student.student_name} className="border-t">
                                <td className="p-2">{student.student_name}</td>
                                <td className="p-2 text-center">{student.issue_count}</td>
                                <td className="p-2 text-center">{student.average_score.toFixed(1)}</td>
                                <td className={`p-2 text-center font-bold ${getGradeColor(student.letter_grade)}`}>
                                  {student.letter_grade}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setExportDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleExport} disabled={isExporting || !exportPreview}>
                  <Download className="mr-2 h-4 w-4" />
                  {isExporting ? "Exporting..." : "Download CSV"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

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
