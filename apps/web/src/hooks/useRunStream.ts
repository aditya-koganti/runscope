import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { apiUrl } from "../api/client";

export type StreamState = "connecting" | "connected" | "reconnecting" | "offline";

interface StreamEvent {
  event_id: string;
  event_type: string;
}

export function parseSseBlock(block: string): StreamEvent | null {
  const data = block
    .split("\n")
    .find((line) => line.startsWith("data: "))
    ?.slice(6);
  if (!data) return null;
  try {
    return JSON.parse(data) as StreamEvent;
  } catch {
    return null;
  }
}

export function useRunStream(runId: string, accessToken: string | null): StreamState {
  const queryClient = useQueryClient();
  const [state, setState] = useState<StreamState>("connecting");

  useEffect(() => {
    if (!runId || !accessToken) {
      return;
    }
    const controller = new AbortController();
    const seen = new Set<string>();

    async function invalidateRunData() {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["run", runId] }),
        queryClient.invalidateQueries({ queryKey: ["run-metrics", runId] }),
        queryClient.invalidateQueries({ queryKey: ["run-logs", runId] }),
        queryClient.invalidateQueries({ queryKey: ["run-events", runId] }),
        queryClient.invalidateQueries({ queryKey: ["run-artifacts", runId] }),
      ]);
    }

    async function connect() {
      let firstAttempt = true;
      while (!controller.signal.aborted) {
        setState(firstAttempt ? "connecting" : "reconnecting");
        try {
          const response = await fetch(apiUrl(`/runs/${runId}/stream`), {
            headers: {
              Accept: "text/event-stream",
              Authorization: `Bearer ${accessToken}`,
            },
            signal: controller.signal,
          });
          if (!response.ok || !response.body) throw new Error("SSE unavailable");
          setState("connected");
          firstAttempt = false;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (!controller.signal.aborted) {
            const result = await reader.read();
            if (result.done) break;
            buffer += decoder.decode(result.value, { stream: true }).replaceAll("\r\n", "\n");
            let boundary = buffer.indexOf("\n\n");
            while (boundary >= 0) {
              const parsed = parseSseBlock(buffer.slice(0, boundary));
              buffer = buffer.slice(boundary + 2);
              boundary = buffer.indexOf("\n\n");
              if (!parsed || parsed.event_type === "stream.heartbeat") continue;
              if (seen.has(parsed.event_id)) continue;
              seen.add(parsed.event_id);
              if (seen.size > 500) seen.delete(seen.values().next().value ?? "");
              await invalidateRunData();
            }
          }
        } catch {
          if (controller.signal.aborted) return;
          setState("reconnecting");
        }
        await new Promise((resolve) => window.setTimeout(resolve, 2_000));
      }
    }

    void connect();
    return () => controller.abort();
  }, [accessToken, queryClient, runId]);

  return !runId || !accessToken ? "offline" : state;
}
