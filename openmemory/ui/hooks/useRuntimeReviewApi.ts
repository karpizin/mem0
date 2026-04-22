"use client";

import { useMemo, useState } from "react";
import axios from "axios";

export interface RuntimeReviewContext {
  baseUrl: string;
  namespaceId: string;
  agentId?: string;
  sessionId?: string;
}

export interface RuntimeReviewMemory {
  id: string;
  memory: string;
  resource_kind: string;
  space_type: string;
  score?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  metadata: Record<string, string | number | boolean | null>;
}

interface RuntimeReviewListResponse {
  results: RuntimeReviewMemory[];
}

const DEFAULT_RUNTIME_URL = "http://localhost:8080";

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, "");
}

function buildAdapterBaseUrl(baseUrl: string): string {
  return `${normalizeBaseUrl(baseUrl)}/v1/adapters/openclaw`;
}

function buildQuery(context: RuntimeReviewContext): URLSearchParams {
  const params = new URLSearchParams({
    namespace_id: context.namespaceId.trim(),
  });
  if (context.agentId?.trim()) {
    params.set("agent_id", context.agentId.trim());
  }
  if (context.sessionId?.trim()) {
    params.set("session_id", context.sessionId.trim());
  }
  return params;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail =
      typeof error.response?.data?.detail === "string"
        ? error.response.data.detail
        : null;
    if (detail) {
      return detail;
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected runtime review error";
}

export function useRuntimeReviewApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const defaultBaseUrl = useMemo(
    () => process.env.NEXT_PUBLIC_MEMORY_RUNTIME_URL || DEFAULT_RUNTIME_URL,
    []
  );

  const listMemories = async (
    context: RuntimeReviewContext
  ): Promise<RuntimeReviewMemory[]> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get<RuntimeReviewListResponse>(
        `${buildAdapterBaseUrl(context.baseUrl)}/memories?${buildQuery(context).toString()}`
      );
      return response.data.results;
    } catch (error) {
      const message = getErrorMessage(error);
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const getMemory = async (
    context: RuntimeReviewContext,
    memoryId: string
  ): Promise<RuntimeReviewMemory> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get<RuntimeReviewMemory>(
        `${buildAdapterBaseUrl(context.baseUrl)}/memories/${memoryId}?${buildQuery(context).toString()}`
      );
      return response.data;
    } catch (error) {
      const message = getErrorMessage(error);
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const updateMemory = async (
    context: RuntimeReviewContext,
    memoryId: string,
    content: string,
    reason?: string
  ): Promise<RuntimeReviewMemory> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.patch<RuntimeReviewMemory>(
        `${buildAdapterBaseUrl(context.baseUrl)}/memories/${memoryId}?${buildQuery(context).toString()}`,
        {
          content,
          reason: reason?.trim() || undefined,
        }
      );
      return response.data;
    } catch (error) {
      const message = getErrorMessage(error);
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const markIncorrect = async (
    context: RuntimeReviewContext,
    memoryId: string,
    reason?: string
  ): Promise<RuntimeReviewMemory> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.patch<RuntimeReviewMemory>(
        `${buildAdapterBaseUrl(context.baseUrl)}/memories/${memoryId}?${buildQuery(context).toString()}`,
        {
          mark_incorrect: true,
          reason: reason?.trim() || undefined,
        }
      );
      return response.data;
    } catch (error) {
      const message = getErrorMessage(error);
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const forgetMemory = async (
    context: RuntimeReviewContext,
    memoryId: string
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      await axios.delete(
        `${buildAdapterBaseUrl(context.baseUrl)}/memories/${memoryId}?${buildQuery(context).toString()}`
      );
    } catch (error) {
      const message = getErrorMessage(error);
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    defaultBaseUrl,
    isLoading,
    error,
    listMemories,
    getMemory,
    updateMemory,
    markIncorrect,
    forgetMemory,
  };
}
