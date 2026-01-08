"use client";

import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { Badge } from "@/components/ui/badge";
import { Plus, Star, Trash2 } from "lucide-react";
import type { RubricConfigListItem } from "@/types/feedback";

interface ConfigSelectorProps {
  configs: RubricConfigListItem[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onCreate: (name: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onSetDefault: (id: number) => Promise<void>;
}

export function ConfigSelector({
  configs,
  selectedId,
  onSelect,
  onCreate,
  onDelete,
  onSetDefault,
}: ConfigSelectorProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setIsCreating(true);
    try {
      await onCreate(newName.trim());
      setNewName("");
      setIsCreateOpen(false);
    } finally {
      setIsCreating(false);
    }
  };

  const selectedConfig = configs.find((c) => c.id === selectedId);

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <Label>Configuration:</Label>
        <Select
          value={selectedId?.toString() ?? ""}
          onValueChange={(value) => onSelect(Number(value))}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Select config" />
          </SelectTrigger>
          <SelectContent>
            {configs.map((config) => (
              <SelectItem key={config.id} value={config.id.toString()}>
                <div className="flex items-center gap-2">
                  {config.name}
                  {config.is_default && (
                    <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                  )}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedConfig && !selectedConfig.is_default && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onSetDefault(selectedConfig.id)}
        >
          <Star className="mr-2 h-4 w-4" />
          Set as Default
        </Button>
      )}

      {selectedConfig && !selectedConfig.is_default && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onDelete(selectedConfig.id)}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </Button>
      )}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <Plus className="mr-2 h-4 w-4" />
            New Config
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Configuration</DialogTitle>
            <DialogDescription>
              Create a new rubric configuration with default settings
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="name">Configuration Name</Label>
            <Input
              id="name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g., Strict Standards"
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={isCreating || !newName.trim()}>
              {isCreating ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
