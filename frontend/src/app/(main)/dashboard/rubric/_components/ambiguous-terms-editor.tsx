"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X, Plus } from "lucide-react";

interface AmbiguousTermsEditorProps {
  terms: string[];
  onAddTerm: (term: string) => Promise<void>;
  onRemoveTerm: (term: string) => Promise<void>;
}

export function AmbiguousTermsEditor({
  terms,
  onAddTerm,
  onRemoveTerm,
}: AmbiguousTermsEditorProps) {
  const [newTerm, setNewTerm] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  const handleAdd = async () => {
    if (!newTerm.trim()) return;
    setIsAdding(true);
    try {
      await onAddTerm(newTerm.trim());
      setNewTerm("");
    } finally {
      setIsAdding(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ambiguous Terms</CardTitle>
        <CardDescription>
          Words or phrases that indicate vague requirements
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Add a term (e.g., 'appropriate', 'maybe')"
            value={newTerm}
            onChange={(e) => setNewTerm(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1"
          />
          <Button onClick={handleAdd} disabled={isAdding || !newTerm.trim()}>
            <Plus className="mr-2 h-4 w-4" />
            Add
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {terms.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No ambiguous terms configured
            </p>
          ) : (
            terms.map((term) => (
              <Badge
                key={term}
                variant="secondary"
                className="flex items-center gap-1"
              >
                {term}
                <button
                  onClick={() => onRemoveTerm(term)}
                  className="ml-1 hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
