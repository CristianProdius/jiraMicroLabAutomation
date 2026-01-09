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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { studentsApi } from "@/lib/api/feedback-api";
import type { StudentSummary } from "@/types/feedback";
import {
  Users,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  ChevronRight,
  GraduationCap,
} from "lucide-react";

export default function StudentsPage() {
  const [period, setPeriod] = useState("90");
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [filteredStudents, setFilteredStudents] = useState<StudentSummary[]>([]);
  const [classAverage, setClassAverage] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"score" | "issues" | "trend">("score");

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const data = await studentsApi.list(Number(period));
        setStudents(data.students);
        setFilteredStudents(data.students);
        setClassAverage(data.class_average_score);
      } catch (error) {
        console.error("Failed to load students:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [period]);

  useEffect(() => {
    let filtered = students.filter((s) =>
      s.assignee.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Sort
    filtered = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case "score":
          return b.average_score - a.average_score;
        case "issues":
          return b.total_issues - a.total_issues;
        case "trend":
          return b.trend - a.trend;
        default:
          return 0;
      }
    });

    setFilteredStudents(filtered);
  }, [searchQuery, sortBy, students]);

  const getTrendIcon = (trend: number) => {
    if (trend > 2) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (trend < -2) return <TrendingDown className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-muted-foreground" />;
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600 dark:text-green-400";
    if (score >= 70) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getPassingRateBadge = (rate: number) => {
    if (rate >= 80)
      return <Badge variant="default" className="bg-green-500">Excellent</Badge>;
    if (rate >= 60)
      return <Badge variant="secondary">Good</Badge>;
    return <Badge variant="destructive">Needs Attention</Badge>;
  };

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <GraduationCap className="h-6 w-6" />
            Students
          </h1>
          <p className="text-muted-foreground">
            Track individual student progress and performance.
          </p>
        </div>
        <div className="flex items-center gap-2">
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
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Students</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">{students.length}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Class Average</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className={`text-2xl font-bold ${getScoreColor(classAverage)}`}>
                {classAverage.toFixed(1)}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Passing Rate</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {students.length > 0
                  ? (
                      (students.filter((s) => s.average_score >= 70).length /
                        students.length) *
                      100
                    ).toFixed(0)
                  : 0}
                %
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search students..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={sortBy} onValueChange={(v) => setSortBy(v as typeof sortBy)}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="score">Avg Score</SelectItem>
                <SelectItem value="issues">Issues Count</SelectItem>
                <SelectItem value="trend">Trend</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Students List */}
      <Card>
        <CardHeader>
          <CardTitle>Student Performance</CardTitle>
          <CardDescription>
            Click on a student to view detailed progress
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : filteredStudents.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              {searchQuery ? "No students match your search" : "No student data available"}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredStudents.map((student) => (
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
                        {student.total_issues} issues analyzed
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className={`text-xl font-bold ${getScoreColor(student.average_score)}`}>
                        {student.average_score.toFixed(0)}
                      </p>
                      <p className="text-xs text-muted-foreground">avg score</p>
                    </div>
                    <div className="text-right">
                      {getPassingRateBadge(student.passing_rate)}
                      <p className="mt-1 text-xs text-muted-foreground">
                        {student.passing_rate.toFixed(0)}% passing
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      {getTrendIcon(student.trend)}
                      <span
                        className={`text-sm ${
                          student.trend > 2
                            ? "text-green-500"
                            : student.trend < -2
                            ? "text-red-500"
                            : "text-muted-foreground"
                        }`}
                      >
                        {student.trend > 0 ? "+" : ""}
                        {student.trend.toFixed(1)}
                      </span>
                    </div>
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
