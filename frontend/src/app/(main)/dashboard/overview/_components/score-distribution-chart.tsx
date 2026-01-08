"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Pie, PieChart, Cell, ResponsiveContainer, Legend } from "recharts";

interface ScoreDistributionChartProps {
  distribution: Record<string, number> | null;
  isLoading: boolean;
}

const COLORS = {
  "90-100": "#22c55e", // green
  "80-89": "#84cc16", // lime
  "70-79": "#eab308", // yellow
  "60-69": "#f97316", // orange
  "50-59": "#ef4444", // red
  "0-49": "#dc2626", // dark red
};

export function ScoreDistributionChart({
  distribution,
  isLoading,
}: ScoreDistributionChartProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Score Distribution</CardTitle>
          <CardDescription>Issues by quality score range</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <Skeleton className="h-48 w-48 rounded-full" />
        </CardContent>
      </Card>
    );
  }

  const data = distribution
    ? Object.entries(distribution)
        .map(([name, value]) => ({
          name,
          value,
          fill: COLORS[name as keyof typeof COLORS] || "#8884d8",
        }))
        .filter((item) => item.value > 0)
    : [];

  const chartConfig = {
    "90-100": { label: "Excellent (90-100)", color: COLORS["90-100"] },
    "80-89": { label: "Good (80-89)", color: COLORS["80-89"] },
    "70-79": { label: "Average (70-79)", color: COLORS["70-79"] },
    "60-69": { label: "Below Average (60-69)", color: COLORS["60-69"] },
    "50-59": { label: "Poor (50-59)", color: COLORS["50-59"] },
    "0-49": { label: "Critical (0-49)", color: COLORS["0-49"] },
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score Distribution</CardTitle>
        <CardDescription>Issues by quality score range</CardDescription>
      </CardHeader>
      <CardContent className="h-[300px]">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            No data available
          </div>
        ) : (
          <ChartContainer config={chartConfig} className="h-full w-full">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent />} />
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={(entry) => `${entry.name}: ${entry.value}`}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Legend />
            </PieChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
