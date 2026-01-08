"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, Filter, X } from "lucide-react";

interface IssueFiltersProps {
  onSearch: (jql: string) => void;
  onScoreFilter: (min?: number, max?: number) => void;
  isSearching: boolean;
}

export function IssueFilters({
  onSearch,
  onScoreFilter,
  isSearching,
}: IssueFiltersProps) {
  const [jql, setJql] = useState("");
  const [scoreRange, setScoreRange] = useState<string>("all");

  const handleSearch = () => {
    if (jql.trim()) {
      onSearch(jql.trim());
    }
  };

  const handleScoreChange = (value: string) => {
    setScoreRange(value);
    switch (value) {
      case "excellent":
        onScoreFilter(80, 100);
        break;
      case "good":
        onScoreFilter(60, 79);
        break;
      case "poor":
        onScoreFilter(0, 59);
        break;
      default:
        onScoreFilter(undefined, undefined);
    }
  };

  const clearFilters = () => {
    setJql("");
    setScoreRange("all");
    onScoreFilter(undefined, undefined);
  };

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-1 gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search issues by JQL (e.g., project = DEMO)"
            value={jql}
            onChange={(e) => setJql(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="pl-9"
          />
        </div>
        <Button onClick={handleSearch} disabled={isSearching || !jql.trim()}>
          {isSearching ? "Searching..." : "Search"}
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={scoreRange} onValueChange={handleScoreChange}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Score range" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Scores</SelectItem>
            <SelectItem value="excellent">Excellent (80+)</SelectItem>
            <SelectItem value="good">Good (60-79)</SelectItem>
            <SelectItem value="poor">Needs Work (&lt;60)</SelectItem>
          </SelectContent>
        </Select>

        {(jql || scoreRange !== "all") && (
          <Button variant="ghost" size="icon" onClick={clearFilters}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
