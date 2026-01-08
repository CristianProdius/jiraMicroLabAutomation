"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ScoreGaugeProps {
  score: number;
  emoji: string;
}

export function ScoreGauge({ score, emoji }: ScoreGaugeProps) {
  // Calculate the stroke dash for the circular progress
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  // Determine color based on score
  const getColor = (s: number) => {
    if (s >= 80) return "#22c55e"; // green
    if (s >= 60) return "#eab308"; // yellow
    return "#ef4444"; // red
  };

  const getLabel = (s: number) => {
    if (s >= 90) return "Excellent";
    if (s >= 80) return "Good";
    if (s >= 70) return "Average";
    if (s >= 60) return "Below Average";
    if (s >= 50) return "Poor";
    return "Critical";
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-center">Quality Score</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center">
        <div className="relative">
          <svg width="160" height="160" className="transform -rotate-90">
            {/* Background circle */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth="12"
              className="text-muted"
            />
            {/* Progress circle */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke={getColor(score)}
              strokeWidth="12"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - progress}
              strokeLinecap="round"
              className="transition-all duration-500"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl">{emoji}</span>
            <span className="text-3xl font-bold">{score.toFixed(0)}</span>
          </div>
        </div>
        <span
          className="mt-2 text-sm font-medium"
          style={{ color: getColor(score) }}
        >
          {getLabel(score)}
        </span>
      </CardContent>
    </Card>
  );
}
