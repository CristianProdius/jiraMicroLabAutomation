"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
  Copy,
  RefreshCw,
  Trash2,
  Send,
} from "lucide-react";
import { authApi, jiraApi, telegramApi } from "@/lib/api/feedback-api";
import type {
  User,
  JiraCredentials,
  TelegramStatus,
} from "@/types/feedback";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [jiraCredentials, setJiraCredentials] = useState<JiraCredentials | null>(null);
  const [telegramStatus, setTelegramStatus] = useState<TelegramStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Jira form state
  const [jiraForm, setJiraForm] = useState({
    base_url: "",
    email: "",
    api_token: "",
  });
  const [isSavingJira, setIsSavingJira] = useState(false);
  const [jiraTestResult, setJiraTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  // Telegram state
  const [telegramCode, setTelegramCode] = useState<string | null>(null);
  const [isGeneratingCode, setIsGeneratingCode] = useState(false);
  const [telegramError, setTelegramError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [userData, jiraCreds, tgStatus] = await Promise.all([
          authApi.getCurrentUser(),
          jiraApi.getCredentials(),
          telegramApi.getStatus(),
        ]);
        setUser(userData);
        setJiraCredentials(jiraCreds);
        setTelegramStatus(tgStatus);

        if (jiraCreds) {
          setJiraForm({
            base_url: jiraCreds.base_url,
            email: jiraCreds.email,
            api_token: "", // Don't show existing token
          });
        }
      } catch (error) {
        console.error("Failed to load settings:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  const handleTestJira = async () => {
    setJiraTestResult(null);
    try {
      const result = await jiraApi.testConnection({
        base_url: jiraForm.base_url,
        email: jiraForm.email,
        api_token: jiraForm.api_token || "existing",
      });
      setJiraTestResult(result);
    } catch (error) {
      setJiraTestResult({
        success: false,
        message: error instanceof Error ? error.message : "Connection failed",
      });
    }
  };

  const handleSaveJira = async () => {
    setIsSavingJira(true);
    try {
      const creds = await jiraApi.setCredentials({
        base_url: jiraForm.base_url,
        email: jiraForm.email,
        api_token: jiraForm.api_token,
      });
      setJiraCredentials(creds);
      setJiraForm({ ...jiraForm, api_token: "" });
      setJiraTestResult({ success: true, message: "Credentials saved successfully" });
    } catch (error) {
      setJiraTestResult({
        success: false,
        message: error instanceof Error ? error.message : "Failed to save credentials",
      });
    } finally {
      setIsSavingJira(false);
    }
  };

  const handleDeleteJira = async () => {
    try {
      await jiraApi.deleteCredentials();
      setJiraCredentials(null);
      setJiraForm({ base_url: "", email: "", api_token: "" });
    } catch (error) {
      console.error("Failed to delete credentials:", error);
    }
  };

  const handleGenerateTelegramCode = async () => {
    setIsGeneratingCode(true);
    setTelegramError(null);
    try {
      const result = await telegramApi.generateCode();
      setTelegramCode(result.code);
    } catch (error) {
      console.error("Failed to generate code:", error);
      const message = error instanceof Error ? error.message : "Failed to generate code";
      setTelegramError(message);
    } finally {
      setIsGeneratingCode(false);
    }
  };

  const handleToggleTelegramNotifications = async (enabled: boolean) => {
    try {
      await telegramApi.updateNotifications(enabled);
      setTelegramStatus(
        telegramStatus ? { ...telegramStatus, notifications_enabled: enabled } : null
      );
    } catch (error) {
      console.error("Failed to update notifications:", error);
    }
  };

  const handleUnlinkTelegram = async () => {
    try {
      await telegramApi.unlink();
      setTelegramStatus({ is_linked: false, telegram_username: null, notifications_enabled: false });
      setTelegramCode(null);
    } catch (error) {
      console.error("Failed to unlink Telegram:", error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (isLoading) {
    return (
      <div className="@container/main flex flex-col gap-4 md:gap-6">
        <div>
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-64 mt-2" />
        </div>
        <Skeleton className="h-64" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  return (
    <div className="@container/main flex flex-col gap-4 md:gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your Jira connection and notification preferences.
        </p>
      </div>

      {/* Account */}
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>Email</Label>
              <p className="text-sm text-muted-foreground mt-1">{user?.email}</p>
            </div>
            <div>
              <Label>Name</Label>
              <p className="text-sm text-muted-foreground mt-1">
                {user?.full_name || "Not set"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Jira Connection */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Jira Connection</CardTitle>
              <CardDescription>
                Connect your Jira instance for issue analysis
              </CardDescription>
            </div>
            {jiraCredentials && (
              <Badge variant="outline" className="text-green-500">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                Connected
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="base-url">Jira Base URL</Label>
              <Input
                id="base-url"
                placeholder="https://your-domain.atlassian.net"
                value={jiraForm.base_url}
                onChange={(e) =>
                  setJiraForm({ ...jiraForm, base_url: e.target.value })
                }
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="jira-email">Email</Label>
              <Input
                id="jira-email"
                type="email"
                placeholder="you@example.com"
                value={jiraForm.email}
                onChange={(e) =>
                  setJiraForm({ ...jiraForm, email: e.target.value })
                }
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="api-token">API Token</Label>
            <Input
              id="api-token"
              type="password"
              placeholder={jiraCredentials ? "••••••••••••" : "Enter your API token"}
              value={jiraForm.api_token}
              onChange={(e) =>
                setJiraForm({ ...jiraForm, api_token: e.target.value })
              }
              className="mt-1"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Get your API token from{" "}
              <a
                href="https://id.atlassian.com/manage-profile/security/api-tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                Atlassian Account Settings
                <ExternalLink className="inline h-3 w-3 ml-1" />
              </a>
            </p>
          </div>

          {jiraTestResult && (
            <div
              className={`flex items-center gap-2 rounded-lg p-3 ${
                jiraTestResult.success
                  ? "bg-green-500/10 text-green-500"
                  : "bg-red-500/10 text-red-500"
              }`}
            >
              {jiraTestResult.success ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              <span className="text-sm">{jiraTestResult.message}</span>
            </div>
          )}

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleTestJira}
              disabled={!jiraForm.base_url || !jiraForm.email}
            >
              Test Connection
            </Button>
            <Button
              onClick={handleSaveJira}
              disabled={
                isSavingJira ||
                !jiraForm.base_url ||
                !jiraForm.email ||
                (!jiraForm.api_token && !jiraCredentials)
              }
            >
              {isSavingJira ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Credentials"
              )}
            </Button>
            {jiraCredentials && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Remove
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Remove Jira Connection</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will remove your Jira credentials. You won't be able to
                      analyze issues until you add them again.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleDeleteJira}>
                      Remove
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Telegram */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Telegram Notifications</CardTitle>
              <CardDescription>
                Receive analysis notifications via Telegram
              </CardDescription>
            </div>
            {telegramStatus?.is_linked && (
              <Badge variant="outline" className="text-green-500">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                @{telegramStatus.telegram_username}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {telegramStatus?.is_linked ? (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <Label>Receive Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Get notified when issues are analyzed
                  </p>
                </div>
                <Switch
                  checked={telegramStatus.notifications_enabled}
                  onCheckedChange={handleToggleTelegramNotifications}
                />
              </div>
              <Separator />
              <Button variant="outline" onClick={handleUnlinkTelegram}>
                Unlink Telegram Account
              </Button>
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                Link your Telegram account to receive notifications when issues
                are analyzed.
              </p>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                    1
                  </span>
                  <span className="text-sm">
                    Start a chat with{" "}
                    <a
                      href="https://t.me/jira_feedback_microlab_bot"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      @jira_feedback_microlab_bot
                      <ExternalLink className="inline h-3 w-3 ml-1" />
                    </a>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                    2
                  </span>
                  <span className="text-sm">Generate a verification code below</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                    3
                  </span>
                  <span className="text-sm">
                    Send <code className="rounded bg-muted px-1">/link CODE</code>{" "}
                    in Telegram
                  </span>
                </div>
              </div>

              {telegramCode ? (
                <div className="flex items-center gap-2 rounded-lg border bg-muted p-4">
                  <code className="text-2xl font-bold tracking-wider">
                    {telegramCode}
                  </code>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => copyToClipboard(telegramCode)}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleGenerateTelegramCode}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Button
                    onClick={handleGenerateTelegramCode}
                    disabled={isGeneratingCode}
                  >
                    {isGeneratingCode ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Generate Code
                      </>
                    )}
                  </Button>
                  {telegramError && (
                    <div className="flex items-center gap-2 rounded-lg bg-red-500/10 p-3 text-red-500">
                      <XCircle className="h-4 w-4" />
                      <span className="text-sm">{telegramError}</span>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
