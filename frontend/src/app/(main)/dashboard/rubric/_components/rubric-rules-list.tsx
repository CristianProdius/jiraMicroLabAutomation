"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
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
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Settings } from "lucide-react";
import type { RubricRule, RubricRuleUpdate } from "@/types/feedback";

interface RubricRulesListProps {
  rules: RubricRule[];
  onRuleUpdate: (ruleId: string, data: RubricRuleUpdate) => Promise<void>;
}

export function RubricRulesList({ rules, onRuleUpdate }: RubricRulesListProps) {
  const [editingRule, setEditingRule] = useState<RubricRule | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const handleToggle = async (rule: RubricRule) => {
    setIsUpdating(true);
    try {
      await onRuleUpdate(rule.rule_id, { is_enabled: !rule.is_enabled });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleWeightChange = async (rule: RubricRule, weight: number) => {
    await onRuleUpdate(rule.rule_id, { weight });
  };

  const handleSaveThresholds = async () => {
    if (!editingRule) return;
    setIsUpdating(true);
    try {
      await onRuleUpdate(editingRule.rule_id, {
        thresholds: editingRule.thresholds,
      });
      setEditingRule(null);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rubric Rules</CardTitle>
        <CardDescription>
          Configure evaluation criteria and their weights
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="flex flex-col gap-4 rounded-lg border p-4"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium">{rule.name}</h4>
                  <Switch
                    checked={rule.is_enabled}
                    onCheckedChange={() => handleToggle(rule)}
                    disabled={isUpdating}
                  />
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {rule.description}
                </p>
              </div>

              {rule.thresholds && (
                <Dialog>
                  <DialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditingRule({ ...rule })}
                    >
                      <Settings className="h-4 w-4" />
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Configure {rule.name}</DialogTitle>
                      <DialogDescription>
                        Adjust thresholds for this rule
                      </DialogDescription>
                    </DialogHeader>
                    {editingRule && editingRule.thresholds && (
                      <div className="space-y-4 py-4">
                        {Object.entries(editingRule.thresholds).map(
                          ([key, value]) => (
                            <div
                              key={key}
                              className="flex items-center justify-between"
                            >
                              <Label className="capitalize">
                                {key.replace(/_/g, " ")}
                              </Label>
                              <Input
                                type="number"
                                value={value}
                                onChange={(e) =>
                                  setEditingRule({
                                    ...editingRule,
                                    thresholds: {
                                      ...editingRule.thresholds,
                                      [key]: Number(e.target.value),
                                    },
                                  })
                                }
                                className="w-24"
                              />
                            </div>
                          )
                        )}
                      </div>
                    )}
                    <DialogFooter>
                      <Button
                        onClick={handleSaveThresholds}
                        disabled={isUpdating}
                      >
                        Save Changes
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}
            </div>

            <div className="flex items-center gap-4">
              <Label className="text-sm text-muted-foreground w-16">
                Weight: {rule.weight.toFixed(1)}
              </Label>
              <Slider
                value={[rule.weight]}
                onValueCommit={(value) => handleWeightChange(rule, value[0])}
                min={0}
                max={3}
                step={0.1}
                disabled={!rule.is_enabled || isUpdating}
                className="flex-1"
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
