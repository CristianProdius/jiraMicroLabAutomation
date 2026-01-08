"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Play, Send, ChevronDown } from "lucide-react";

interface BulkActionsProps {
  selectedCount: number;
  onAnalyzeSelected: () => void;
  onPostToJira: () => void;
  isProcessing: boolean;
}

export function BulkActions({
  selectedCount,
  onAnalyzeSelected,
  onPostToJira,
  isProcessing,
}: BulkActionsProps) {
  if (selectedCount === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-4 rounded-lg border bg-muted/50 px-4 py-2">
      <span className="text-sm text-muted-foreground">
        {selectedCount} selected
      </span>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" disabled={isProcessing}>
            Actions
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onClick={onAnalyzeSelected}>
            <Play className="mr-2 h-4 w-4" />
            Re-analyze Selected
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onPostToJira}>
            <Send className="mr-2 h-4 w-4" />
            Post to Jira
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
