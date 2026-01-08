"use client";

import { useEffect, useState, useCallback } from "react";
import { RubricRulesList } from "./_components/rubric-rules-list";
import { AmbiguousTermsEditor } from "./_components/ambiguous-terms-editor";
import { ConfigSelector } from "./_components/config-selector";
import { rubricsApi } from "@/lib/api/feedback-api";
import type {
  RubricConfig,
  RubricConfigListItem,
  RubricRuleUpdate,
} from "@/types/feedback";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";

export default function RubricConfigPage() {
  const [configs, setConfigs] = useState<RubricConfigListItem[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<RubricConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadConfigs = useCallback(async () => {
    try {
      const data = await rubricsApi.list();
      setConfigs(data);

      // Select default or first config
      const defaultConfig = data.find((c) => c.is_default) || data[0];
      if (defaultConfig && (!selectedConfig || selectedConfig.id !== defaultConfig.id)) {
        const fullConfig = await rubricsApi.get(defaultConfig.id);
        setSelectedConfig(fullConfig);
      }
    } catch (error) {
      console.error("Failed to load configs:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleSelectConfig = async (id: number) => {
    setIsLoading(true);
    try {
      const config = await rubricsApi.get(id);
      setSelectedConfig(config);
    } catch (error) {
      console.error("Failed to load config:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateConfig = async (name: string) => {
    const newConfig = await rubricsApi.create(name);
    setConfigs([...configs, { id: newConfig.id, name: newConfig.name, is_default: false, created_at: newConfig.created_at }]);
    setSelectedConfig(newConfig);
  };

  const handleDeleteConfig = async (id: number) => {
    await rubricsApi.delete(id);
    setConfigs(configs.filter((c) => c.id !== id));
    if (selectedConfig?.id === id) {
      const remaining = configs.filter((c) => c.id !== id);
      if (remaining.length > 0) {
        const fullConfig = await rubricsApi.get(remaining[0].id);
        setSelectedConfig(fullConfig);
      } else {
        setSelectedConfig(null);
      }
    }
  };

  const handleSetDefault = async (id: number) => {
    await rubricsApi.setDefault(id);
    setConfigs(
      configs.map((c) => ({
        ...c,
        is_default: c.id === id,
      }))
    );
    if (selectedConfig) {
      setSelectedConfig({ ...selectedConfig, is_default: selectedConfig.id === id });
    }
  };

  const handleRuleUpdate = async (ruleId: string, data: RubricRuleUpdate) => {
    if (!selectedConfig) return;
    await rubricsApi.updateRule(selectedConfig.id, ruleId, data);

    // Update local state
    setSelectedConfig({
      ...selectedConfig,
      rules: selectedConfig.rules.map((r) =>
        r.rule_id === ruleId ? { ...r, ...data } : r
      ),
    });
  };

  const handleAddTerm = async (term: string) => {
    if (!selectedConfig) return;
    const terms = await rubricsApi.addTerm(selectedConfig.id, term);
    setSelectedConfig({ ...selectedConfig, ambiguous_terms: terms });
  };

  const handleRemoveTerm = async (term: string) => {
    if (!selectedConfig) return;
    const terms = await rubricsApi.deleteTerm(selectedConfig.id, term);
    setSelectedConfig({ ...selectedConfig, ambiguous_terms: terms });
  };

  const handleSettingsUpdate = async (field: string, value: unknown) => {
    if (!selectedConfig) return;
    await rubricsApi.update(selectedConfig.id, { [field]: value });
    setSelectedConfig({ ...selectedConfig, [field]: value });
  };

  if (isLoading && !selectedConfig) {
    return (
      <div className="@container/main flex flex-col gap-4 md:gap-6">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72 mt-2" />
        </div>
        <Skeleton className="h-12 w-96" />
        <Skeleton className="h-64" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Rubric Configuration</h1>
        <p className="text-muted-foreground">
          Customize evaluation criteria and scoring weights.
        </p>
      </div>

      <ConfigSelector
        configs={configs}
        selectedId={selectedConfig?.id ?? null}
        onSelect={handleSelectConfig}
        onCreate={handleCreateConfig}
        onDelete={handleDeleteConfig}
        onSetDefault={handleSetDefault}
      />

      {selectedConfig && (
        <>
          {/* General Settings */}
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
              <CardDescription>
                Basic requirements for issue evaluation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="min-words">Minimum Description Words</Label>
                  <p className="text-sm text-muted-foreground">
                    Minimum word count required for the description
                  </p>
                </div>
                <Input
                  id="min-words"
                  type="number"
                  value={selectedConfig.min_description_words}
                  onChange={(e) =>
                    handleSettingsUpdate(
                      "min_description_words",
                      Number(e.target.value)
                    )
                  }
                  className="w-24"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="require-ac">Require Acceptance Criteria</Label>
                  <p className="text-sm text-muted-foreground">
                    Penalize issues without acceptance criteria
                  </p>
                </div>
                <Switch
                  id="require-ac"
                  checked={selectedConfig.require_acceptance_criteria}
                  onCheckedChange={(checked) =>
                    handleSettingsUpdate("require_acceptance_criteria", checked)
                  }
                />
              </div>
            </CardContent>
          </Card>

          {/* Rules */}
          <RubricRulesList
            rules={selectedConfig.rules}
            onRuleUpdate={handleRuleUpdate}
          />

          {/* Ambiguous Terms */}
          <AmbiguousTermsEditor
            terms={selectedConfig.ambiguous_terms}
            onAddTerm={handleAddTerm}
            onRemoveTerm={handleRemoveTerm}
          />
        </>
      )}
    </div>
  );
}
