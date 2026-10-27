export type StepStatus = "pending" | "running" | "completed" | "error";

export interface StepDetail {
  text?: string;
  headline?: string;
  items?: Record<string, string[]>;
  issues?: Issue[];
}

export interface Step {
  id: number;
  title: string;
  description: string;
  activity: number | null;
  status: StepStatus;
  detail: StepDetail | null;
  error: string | null;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  kind?: string;
}

export interface VersionMeta {
  number: number;
  source: "agent" | "example" | "upload";
  label: string;
  createdAt: string;
  valid: boolean;
  errors: number;
  warnings: number;
}

export interface Issue {
  severity: "error" | "warning";
  code: string;
  message: string;
  element: string | null;
  hint: string | null;
}

export interface ModelNode {
  id: string;
  cls: string;
  supertypes: string[];
  name: string;
  parent: string | null;
  feature: string | null;
  attrs: Record<string, unknown>;
  refs: Record<string, string[]>;
}

export interface VersionData extends VersionMeta {
  validation: { valid: boolean; errors: number; warnings: number; issues: Issue[] };
  summary: Record<string, unknown>;
  model: { nodes: ModelNode[] };
  xmi: string;
}

export interface SessionData {
  id: string;
  caseName: string;
  messages: Message[];
  steps: Step[];
  versions: VersionMeta[];
}

export interface Health {
  agentMode: "glm" | "demo";
  llm: string | null;
}

export type AgentEvent =
  | { type: "step"; id: number; status: StepStatus; detail: StepDetail | null; error: string | null }
  | { type: "message"; role: Message["role"]; content: string; kind?: string }
  | { type: "version"; version: { number: number } }
  | { type: "error"; message: string; retryable: boolean }
  | { type: "done" };

async function asJson<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `Error ${r.status}`;
    try {
      const body = await r.json();
      if (body.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

export const api = {
  health: () => fetch("/api/health").then((r) => asJson<Health>(r)),
  createSession: () => fetch("/api/sessions", { method: "POST" }).then((r) => asJson<SessionData>(r)),
  getSession: (sid: string) => fetch(`/api/sessions/${sid}`).then((r) => asJson<SessionData>(r)),
  getVersion: (sid: string, n: number) => fetch(`/api/sessions/${sid}/versions/${n}`).then((r) => asJson<VersionData>(r)),
  uploadXmi: (sid: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`/api/sessions/${sid}/xmi`, { method: "POST", body: fd }).then((r) =>
      asJson<{ session: SessionData; version: VersionMeta }>(r),
    );
  },
  downloadUrl: (sid: string, n: number, ext: "MonitorIoT" | "xmi") =>
    `/api/sessions/${sid}/versions/${n}/download?ext=${ext}`,
};

/** Envía una petición y entrega cada evento del agente en cuanto llega (RF-16). */
export async function streamEvents(url: string, body: unknown, onEvent: (e: AgentEvent) => void): Promise<void> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok || !r.body) {
    await asJson(r);
    return;
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)) as AgentEvent);
    }
  }
}
