"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CheckCircle2, AlertCircle, Lightbulb } from "lucide-react";

interface FeedbackCardsProps {
  strengths: string[];
  improvements: string[];
  suggestions: string[];
}

export function FeedbackCards({
  strengths,
  improvements,
  suggestions,
}: FeedbackCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            <CardTitle className="text-lg">Strengths</CardTitle>
          </div>
          <CardDescription>What this issue does well</CardDescription>
        </CardHeader>
        <CardContent>
          {strengths.length === 0 ? (
            <p className="text-sm text-muted-foreground">No strengths identified</p>
          ) : (
            <ul className="space-y-2">
              {strengths.map((item, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <span className="text-green-500 mt-0.5">+</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-orange-500" />
            <CardTitle className="text-lg">Improvements</CardTitle>
          </div>
          <CardDescription>Areas that need attention</CardDescription>
        </CardHeader>
        <CardContent>
          {improvements.length === 0 ? (
            <p className="text-sm text-muted-foreground">No improvements needed</p>
          ) : (
            <ul className="space-y-2">
              {improvements.map((item, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <span className="text-orange-500 mt-0.5">-</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-blue-500" />
            <CardTitle className="text-lg">Suggestions</CardTitle>
          </div>
          <CardDescription>Actionable recommendations</CardDescription>
        </CardHeader>
        <CardContent>
          {suggestions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No suggestions</p>
          ) : (
            <ul className="space-y-2">
              {suggestions.map((item, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <span className="text-blue-500 mt-0.5">*</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
