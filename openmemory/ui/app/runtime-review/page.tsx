"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Check,
  Copy,
  Eye,
  Loader2,
  Pencil,
  RefreshCcw,
  RotateCcw,
  ShieldAlert,
  Trash2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  RuntimeReviewContext,
  RuntimeReviewMemory,
  useRuntimeReviewApi,
} from "@/hooks/useRuntimeReviewApi";

type ScopeFilter = "all" | "private" | "group";

const STORAGE_KEY = "mem0plus-review-config-v1";

function deriveScope(memory: RuntimeReviewMemory): "private" | "group" {
  return memory.space_type === "shared-space" ? "group" : "private";
}

function getScopeDescription(scope: ScopeFilter): string {
  if (scope === "private") {
    return "Agent-specific and personal memory items.";
  }
  if (scope === "group") {
    return "Project memory shared across cooperating agents.";
  }
  return "Both private and group memories visible to the current review context.";
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "n/a";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "n/a";
  }
  return parsed.toLocaleString();
}

function isSensitive(memory: RuntimeReviewMemory): boolean {
  return Boolean(memory.metadata?.sensitive);
}

function isMasked(memory: RuntimeReviewMemory): boolean {
  return Boolean(memory.metadata?.masked);
}

function getMetadataEntries(memory: RuntimeReviewMemory): Array<[string, string]> {
  return Object.entries(memory.metadata || {})
    .filter(([, value]) => value !== null && value !== "")
    .map(([key, value]) => [key, String(value)]);
}

function RuntimeReviewPage() {
  const {
    defaultBaseUrl,
    error,
    getMemory,
    forgetMemory,
    isLoading,
    listMemories,
    markIncorrect,
    updateMemory,
  } = useRuntimeReviewApi();

  const [baseUrl, setBaseUrl] = useState(defaultBaseUrl);
  const [namespaceId, setNamespaceId] = useState("");
  const [agentId, setAgentId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>("all");
  const [searchText, setSearchText] = useState("");
  const [memories, setMemories] = useState<RuntimeReviewMemory[]>([]);
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [editReason, setEditReason] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [copiedValue, setCopiedValue] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as Partial<RuntimeReviewContext>;
      if (parsed.baseUrl) {
        setBaseUrl(parsed.baseUrl);
      }
      if (parsed.namespaceId) {
        setNamespaceId(parsed.namespaceId);
      }
      if (parsed.agentId) {
        setAgentId(parsed.agentId);
      }
      if (parsed.sessionId) {
        setSessionId(parsed.sessionId);
      }
    } catch {
      // Ignore malformed local config and use defaults.
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        baseUrl,
        namespaceId,
        agentId,
        sessionId,
      })
    );
  }, [agentId, baseUrl, namespaceId, sessionId]);

  const context = useMemo<RuntimeReviewContext>(
    () => ({
      baseUrl,
      namespaceId,
      agentId,
      sessionId,
    }),
    [agentId, baseUrl, namespaceId, sessionId]
  );

  const selectedMemory = useMemo(
    () => memories.find((memory) => memory.id === selectedMemoryId) || null,
    [memories, selectedMemoryId]
  );

  const scopeStats = useMemo(() => {
    const privateCount = memories.filter((memory) => deriveScope(memory) === "private").length;
    const groupCount = memories.filter((memory) => deriveScope(memory) === "group").length;
    const sensitiveCount = memories.filter((memory) => isSensitive(memory)).length;
    return {
      total: memories.length,
      privateCount,
      groupCount,
      sensitiveCount,
    };
  }, [memories]);

  const isDirty = selectedMemory !== null && editText !== selectedMemory.memory;
  const selectedMetadata = useMemo(
    () => (selectedMemory ? getMetadataEntries(selectedMemory) : []),
    [selectedMemory]
  );

  const filteredMemories = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    return memories.filter((memory) => {
      if (scopeFilter !== "all" && deriveScope(memory) !== scopeFilter) {
        return false;
      }
      if (!query) {
        return true;
      }
      return (
        memory.memory.toLowerCase().includes(query) ||
        memory.id.toLowerCase().includes(query) ||
        memory.resource_kind.toLowerCase().includes(query) ||
        memory.space_type.toLowerCase().includes(query)
      );
    });
  }, [memories, scopeFilter, searchText]);

  useEffect(() => {
    if (!selectedMemory) {
      setEditText("");
      setEditReason("");
      setIsEditing(false);
      return;
    }
    setEditText(selectedMemory.memory);
    setEditReason("");
  }, [selectedMemory]);

  async function handleCopy(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedValue(label);
      toast.success(`${label} copied`);
      window.setTimeout(() => {
        setCopiedValue((current) => (current === label ? null : current));
      }, 1500);
    } catch {
      toast.error(`Failed to copy ${label.toLowerCase()}`);
    }
  }

  function handleResetContext() {
    setNamespaceId("");
    setAgentId("");
    setSessionId("");
    setSearchText("");
    setMemories([]);
    setSelectedMemoryId(null);
    setEditReason("");
    setEditText("");
    setIsEditing(false);
    toast.success("Runtime review context cleared");
  }

  async function handleLoadMemories() {
    if (!namespaceId.trim()) {
      toast.error("Namespace ID is required");
      return;
    }
    try {
      const results = await listMemories(context);
      setMemories(results);
      setSelectedMemoryId(results[0]?.id || null);
      setIsEditing(false);
      toast.success(`Loaded ${results.length} memories`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load memories");
    }
  }

  async function handleRefreshSelected(memoryId: string) {
    try {
      const refreshed = await getMemory(context, memoryId);
      setMemories((current) =>
        current.map((memory) => (memory.id === refreshed.id ? refreshed : memory))
      );
      setSelectedMemoryId(refreshed.id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to refresh memory");
    }
  }

  async function handleSave() {
    if (!selectedMemory) {
      return;
    }
    if (!editText.trim()) {
      toast.error("Memory text cannot be empty");
      return;
    }
    try {
      const updated = await updateMemory(
        context,
        selectedMemory.id,
        editText,
        editReason
      );
      setMemories((current) =>
        current.map((memory) => (memory.id === updated.id ? updated : memory))
      );
      setSelectedMemoryId(updated.id);
      setIsEditing(false);
      setEditReason("");
      toast.success("Memory updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update memory");
    }
  }

  async function handleForget() {
    if (!selectedMemory) {
      return;
    }
    if (!window.confirm("Forget this memory and remove it from the active review surface?")) {
      return;
    }
    try {
      const nextSelectedId =
        memories.find((memory) => memory.id !== selectedMemory.id)?.id || null;
      await forgetMemory(context, selectedMemory.id);
      setMemories((current) => current.filter((memory) => memory.id !== selectedMemory.id));
      setSelectedMemoryId(nextSelectedId);
      toast.success("Memory forgotten");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to forget memory");
    }
  }

  async function handleMarkIncorrect() {
    if (!selectedMemory) {
      return;
    }
    if (!window.confirm("Mark this memory as incorrect and remove it from active recall?")) {
      return;
    }
    try {
      await markIncorrect(context, selectedMemory.id, editReason);
      const remaining = memories.filter((memory) => memory.id !== selectedMemory.id);
      setMemories(remaining);
      setSelectedMemoryId(remaining[0]?.id || null);
      setIsEditing(false);
      setEditReason("");
      toast.success("Memory marked incorrect");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to mark memory incorrect"
      );
    }
  }

  return (
    <main className="flex-1 py-6">
      <div className="container space-y-6">
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader>
            <CardTitle className="text-white">mem0plus Review</CardTitle>
            <CardDescription>
              Builder-facing review surface for the `mem0plus` adapter contract.
              Use it to inspect, update, forget, and mark memories incorrect across
              `private` and `group` scopes.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="grid gap-2">
              <Label htmlFor="runtime-base-url">Runtime URL</Label>
              <Input
                id="runtime-base-url"
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="http://localhost:8080"
                className="bg-zinc-950 border-zinc-800"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="runtime-namespace-id">Namespace ID</Label>
              <Input
                id="runtime-namespace-id"
                value={namespaceId}
                onChange={(event) => setNamespaceId(event.target.value)}
                placeholder="namespace UUID"
                className="bg-zinc-950 border-zinc-800"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="runtime-agent-id">Agent ID</Label>
              <Input
                id="runtime-agent-id"
                value={agentId}
                onChange={(event) => setAgentId(event.target.value)}
                placeholder="agent UUID"
                className="bg-zinc-950 border-zinc-800"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="runtime-session-id">Session ID (optional)</Label>
              <Input
                id="runtime-session-id"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                placeholder="session id for scratchpad review"
                className="bg-zinc-950 border-zinc-800"
              />
            </div>
            <div className="flex flex-wrap items-end gap-2 md:col-span-2 xl:col-span-4">
              <Button onClick={handleLoadMemories} disabled={isLoading}>
                {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Eye className="w-4 h-4 mr-2" />}
                Load mem0plus Surface
              </Button>
              <Button
                variant="outline"
                className="border-zinc-700 bg-zinc-950"
                onClick={handleResetContext}
                disabled={isLoading}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Clear Context
              </Button>
              <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                {sessionId.trim() ? "Session review mode" : "Long-term review mode"}
              </Badge>
              <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                Adapter: OpenClaw
              </Badge>
              {error ? (
                <Badge variant="destructive" className="ml-auto">
                  {error}
                </Badge>
              ) : null}
            </div>
            <div className="md:col-span-2 xl:col-span-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-xs uppercase tracking-wide text-zinc-500">Loaded</p>
                <p className="mt-2 text-2xl font-semibold text-white">{scopeStats.total}</p>
                <p className="mt-1 text-xs text-zinc-400">Visible review items in current context</p>
              </div>
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-xs uppercase tracking-wide text-zinc-500">Private</p>
                <p className="mt-2 text-2xl font-semibold text-white">{scopeStats.privateCount}</p>
                <p className="mt-1 text-xs text-zinc-400">Agent-specific memory items</p>
              </div>
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-xs uppercase tracking-wide text-zinc-500">Group</p>
                <p className="mt-2 text-2xl font-semibold text-white">{scopeStats.groupCount}</p>
                <p className="mt-1 text-xs text-zinc-400">Project-shared memory items</p>
              </div>
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-xs uppercase tracking-wide text-zinc-500">Sensitive</p>
                <p className="mt-2 text-2xl font-semibold text-white">{scopeStats.sensitiveCount}</p>
                <p className="mt-1 text-xs text-zinc-400">Require masking-aware review</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
          <Card className="border-zinc-800 bg-zinc-900">
            <CardHeader className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-white text-xl">Memory Items</CardTitle>
                  <CardDescription>
                    Filter by scope and inspect active runtime-visible memories.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-zinc-700 bg-zinc-950"
                  onClick={handleLoadMemories}
                  disabled={isLoading}
                >
                  <RefreshCcw className="w-4 h-4 mr-2" />
                  Refresh
                </Button>
              </div>
              <div className="grid gap-3">
                <Input
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                  placeholder="Search memory text, ids, or types"
                  className="bg-zinc-950 border-zinc-800"
                />
                <div className="flex gap-2">
                  {(["all", "private", "group"] as ScopeFilter[]).map((filter) => (
                    <Button
                      key={filter}
                      variant={scopeFilter === filter ? "default" : "outline"}
                      size="sm"
                      className={scopeFilter === filter ? "" : "border-zinc-700 bg-zinc-950"}
                      onClick={() => setScopeFilter(filter)}
                    >
                      {filter === "all" ? "All" : filter === "private" ? "Private" : "Group"}
                    </Button>
                  ))}
                </div>
                <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-400">
                  <span className="font-medium text-zinc-200">
                    {scopeFilter === "all" ? "All scopes" : scopeFilter === "private" ? "Private scope" : "Group scope"}
                  </span>
                  {` - ${getScopeDescription(scopeFilter)}`}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[520px] pr-4">
                <div className="space-y-3">
                  {filteredMemories.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-950 p-6 text-sm text-zinc-400">
                      No memories loaded for the current mem0plus review context.
                    </div>
                  ) : (
                    filteredMemories.map((memory) => {
                      const selected = memory.id === selectedMemoryId;
                      const scope = deriveScope(memory);
                      return (
                        <button
                          key={memory.id}
                          type="button"
                          onClick={() => setSelectedMemoryId(memory.id)}
                          className={`w-full rounded-lg border p-4 text-left transition ${
                            selected
                              ? "border-primary bg-zinc-800/90"
                              : "border-zinc-800 bg-zinc-950 hover:bg-zinc-900"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="space-y-2">
                              <p className="text-sm font-medium text-white line-clamp-3">
                                {memory.memory}
                              </p>
                              <p className="text-xs text-zinc-500">
                                Updated {formatDate(memory.updated_at || memory.created_at)}
                              </p>
                              <div className="flex flex-wrap gap-2">
                                <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                                  {scope}
                                </Badge>
                                <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                                  {memory.resource_kind}
                                </Badge>
                                <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                                  {memory.space_type}
                                </Badge>
                                {isSensitive(memory) ? (
                                  <Badge variant="destructive" className="gap-1">
                                    <ShieldAlert className="w-3 h-3" />
                                    Sensitive
                                  </Badge>
                                ) : null}
                              </div>
                            </div>
                            <span className="text-xs text-zinc-500">
                              {memory.id.slice(0, 8)}
                            </span>
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-900">
            <CardHeader>
              <CardTitle className="text-white text-xl">Review Detail</CardTitle>
              <CardDescription>
                Update text, forget transient noise, or mark incorrect durable memory out
                of the active runtime surface.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedMemory ? (
                <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-950 p-8 text-sm text-zinc-400">
                  Select a memory item to review it.
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex flex-col gap-4 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                          {deriveScope(selectedMemory)}
                        </Badge>
                        <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                          {selectedMemory.resource_kind}
                        </Badge>
                        <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                          {selectedMemory.space_type}
                        </Badge>
                        {isSensitive(selectedMemory) ? (
                          <Badge variant="destructive" className="gap-1">
                            <ShieldAlert className="w-3 h-3" />
                            Sensitive
                          </Badge>
                        ) : null}
                        {isMasked(selectedMemory) ? (
                          <Badge variant="outline" className="border-amber-700 text-amber-300">
                            Masked by policy
                          </Badge>
                        ) : null}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-zinc-700 bg-zinc-900"
                        onClick={() => handleCopy(selectedMemory.id, "Memory ID")}
                      >
                        {copiedValue === "Memory ID" ? (
                          <Check className="w-4 h-4 mr-2" />
                        ) : (
                          <Copy className="w-4 h-4 mr-2" />
                        )}
                        Copy ID
                      </Button>
                    </div>
                    <p className="text-sm text-zinc-300">
                      {deriveScope(selectedMemory) === "group"
                        ? "This item is visible to agents that share the same project memory scope."
                        : "This item belongs to the private agent-facing memory scope."}
                    </p>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-xs uppercase tracking-wide text-zinc-500">Memory ID</p>
                      <p className="text-sm text-zinc-200 break-all">{selectedMemory.id}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs uppercase tracking-wide text-zinc-500">Status</p>
                      <p className="text-sm text-zinc-200">
                        {String(selectedMemory.metadata.status || "active")}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs uppercase tracking-wide text-zinc-500">Created</p>
                      <p className="text-sm text-zinc-200">{formatDate(selectedMemory.created_at)}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs uppercase tracking-wide text-zinc-500">Updated</p>
                      <p className="text-sm text-zinc-200">{formatDate(selectedMemory.updated_at)}</p>
                    </div>
                  </div>

                  {selectedMetadata.length > 0 ? (
                    <>
                      <Separator className="bg-zinc-800" />
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-zinc-500">Metadata</p>
                          <p className="mt-1 text-sm text-zinc-400">
                            Runtime review uses these flags to keep scope, sensitive handling, and status visible.
                          </p>
                        </div>
                        <div className="grid gap-3 md:grid-cols-2">
                          {selectedMetadata.map(([key, value]) => (
                            <div
                              key={key}
                              className="rounded-lg border border-zinc-800 bg-zinc-950 p-3"
                            >
                              <p className="text-xs uppercase tracking-wide text-zinc-500">{key}</p>
                              <p className="mt-1 text-sm text-zinc-200 break-all">{value}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : null}

                  <Separator className="bg-zinc-800" />

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="review-memory-text" className="text-sm text-zinc-300">
                        Memory Text
                      </Label>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="border-zinc-700 bg-zinc-950"
                          onClick={() => handleRefreshSelected(selectedMemory.id)}
                          disabled={isLoading}
                        >
                          <RefreshCcw className="w-4 h-4 mr-2" />
                          Refresh Item
                        </Button>
                        <Button
                          variant={isEditing ? "default" : "outline"}
                          size="sm"
                          className={isEditing ? "" : "border-zinc-700 bg-zinc-950"}
                          onClick={() => {
                            setIsEditing((value) => !value);
                            setEditText(selectedMemory.memory);
                          }}
                        >
                          <Pencil className="w-4 h-4 mr-2" />
                          {isEditing ? "Stop editing" : "Edit"}
                        </Button>
                        {isEditing ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="border-zinc-700 bg-zinc-950"
                            onClick={() => {
                              setEditText(selectedMemory.memory);
                              setEditReason("");
                              setIsEditing(false);
                            }}
                          >
                            <RotateCcw className="w-4 h-4 mr-2" />
                            Discard
                          </Button>
                        ) : null}
                      </div>
                    </div>
                    <Textarea
                      id="review-memory-text"
                      value={editText}
                      onChange={(event) => setEditText(event.target.value)}
                      readOnly={!isEditing}
                      className={`min-h-[180px] border-zinc-800 ${
                        isEditing ? "bg-zinc-950" : "bg-zinc-900"
                      }`}
                    />
                    <div className="grid gap-2">
                      <Label htmlFor="review-memory-reason" className="text-sm text-zinc-300">
                        Review Reason (optional)
                      </Label>
                      <Input
                        id="review-memory-reason"
                        value={editReason}
                        onChange={(event) => setEditReason(event.target.value)}
                        placeholder="Why are you changing or disabling this memory?"
                        className="bg-zinc-950 border-zinc-800"
                      />
                    </div>
                    {isSensitive(selectedMemory) ? (
                      <p className="text-xs text-zinc-500">
                        Sensitive items may stay masked here depending on runtime policy. Review
                        actions still work on the underlying memory object.
                      </p>
                    ) : null}
                    {isEditing && isDirty ? (
                      <p className="text-xs text-amber-300">
                        Unsaved change detected. Saving will overwrite the current active memory text.
                      </p>
                    ) : null}
                  </div>

                  <Separator className="bg-zinc-800" />

                  <div className="flex flex-wrap gap-3">
                    <Button onClick={handleSave} disabled={!isEditing || !isDirty || isLoading}>
                      {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Pencil className="w-4 h-4 mr-2" />}
                      Save Update
                    </Button>
                    <Button
                      variant="outline"
                      className="border-zinc-700 bg-zinc-950"
                      onClick={handleForget}
                      disabled={isLoading}
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Forget
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleMarkIncorrect}
                      disabled={isLoading}
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Mark Incorrect
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}

export default RuntimeReviewPage;
