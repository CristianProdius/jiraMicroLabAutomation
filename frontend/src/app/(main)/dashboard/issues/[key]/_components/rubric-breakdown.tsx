"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info } from "lucide-react";
import type { RubricBreakdownItem } from "@/types/feedback";

interface RubricBreakdownProps {
  breakdown: Record<string, RubricBreakdownItem>;
}

const RULE_LABELS: Record<string, string> = {
  title_clarity: "Title Clarity",
  description_length: "Description Length",
  acceptance_criteria: "Acceptance Criteria",
  ambiguous_terms: "Ambiguous Terms",
  estimate_present: "Estimate Present",
  labels_valid: "Labels Valid",
  scope_clarity: "Scope Clarity",
};

export function RubricBreakdown({ breakdown }: RubricBreakdownProps) {
  const entries = Object.entries(breakdown);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rubric Breakdown</CardTitle>
        <CardDescription>Score breakdown by evaluation criteria</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {entries.map(([ruleId, item]) => (
          <div key={ruleId} className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">
                  {RULE_LABELS[ruleId] || ruleId}
                </span>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Info className="h-3 w-3 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-[300px]">
                      <p>{item.message}</p>
                      {item.suggestion && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Tip: {item.suggestion}
                        </p>
                      )}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <span className="text-sm text-muted-foreground">
                {(item.score * 100).toFixed(0)}%
              </span>
            </div>
            <Progress value={item.score * 100} className="h-2" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
