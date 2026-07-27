import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 15000,
});

// Inject JWT token into every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth_token");
      window.location.reload();
    }
    console.error("API Error:", error);
    return Promise.reject(error);
  },
);

// ── Types ──────────────────────────────────────────────

export interface ChatRequest {
  question: string;
  session_id: string;
}

export interface EvidenceItem {
  claim: string;
  data: string[];
  source: string;
  strength: number | null;
}

export interface EvidenceReport {
  conclusion: string;
  evidence_chain: EvidenceItem[];
  suggestions: string[];
  limitations: string[];
}

export interface ChatResponse {
  message_id: number;
  session_id: string;
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  chart_type: string;
  echarts_option: Record<string, unknown>;
  insight: string;
  evidence: EvidenceReport | null;
  elapsed_ms: number | null;
  error: string | null;
}

export interface SessionInfo {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface MessageInfo {
  id: number;
  role: "user" | "assistant";
  content: string;
  sql_text: string | null;
  chart_type: string | null;
  echarts_option: Record<string, unknown> | null;
  insight: string | null;
  evidence: EvidenceReport | null;
  columns: string[] | null;
  rows_data: Record<string, unknown>[] | null;
  elapsed_ms: number | null;
  created_at: string;
}

// ── API ────────────────────────────────────────────────

export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>("/chat", req, { timeout: 120000 });
  return res.data;
}

// ── SSE Streaming ────────────────────────────────────

export interface StreamEvent {
  type: "progress" | "result" | "error";
  node?: string;
  label?: string;
  task_type?: string;
  row_count?: number;
  // result fields
  message_id?: number;
  session_id?: string;
  sql?: string;
  columns?: string[];
  rows?: Record<string, unknown>[];
  chart_type?: string;
  echarts_option?: Record<string, unknown>;
  insight?: string;
  evidence?: EvidenceReport | null;
  elapsed_ms?: number;
  message?: string;
}

export function sendChatStream(
  req: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const token = localStorage.getItem("auth_token");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers,
        body: JSON.stringify(req),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6)) as StreamEvent;
            onEvent(data);
          }
        }
      }
      onComplete();
    } catch (err) {
      if (!controller.signal.aborted) {
        onError(err instanceof Error ? err : new Error("Stream failed"));
      }
    }
  })();

  return controller;
}

export async function createSession(): Promise<{ session_id: string }> {
  const res = await api.post("/sessions");
  return res.data;
}

export async function listSessions(): Promise<{ sessions: SessionInfo[] }> {
  const res = await api.get("/sessions");
  return res.data;
}

export async function getSessionMessages(
  sessionId: string
): Promise<{ messages: MessageInfo[] }> {
  const res = await api.get(`/sessions/${sessionId}`);
  return res.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/sessions/${sessionId}`);
}

// ── Dataset API ─────────────────────────────────────

export interface DatasetColumn {
  name: string;
  type: string;
  semantic_type?: string;
  original_name?: string;
}

export interface DatasetPreview {
  dataset_id: string;
  table_name: string;
  name: string;
  source_type: string;
  sheet_name: string | null;
  row_count: number;
  column_count: number;
  columns: DatasetColumn[];
  preview_rows: Record<string, unknown>[];
}

export interface DatasetInfo {
  table_name: string;
  name: string;
  source_type: string;
  row_count: number;
  column_count: number;
  columns: DatasetColumn[];
}

export async function uploadDataset(
  file: File,
  sessionId: string
): Promise<{ datasets: DatasetPreview[]; count: number }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);
  const res = await api.post("/datasets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  });
  return res.data;
}

export async function listDatasets(
  sessionId: string
): Promise<{ datasets: DatasetInfo[]; count: number }> {
  const res = await api.get(`/datasets?session_id=${sessionId}`);
  return res.data;
}

export async function deleteDataset(tableName: string): Promise<void> {
  await api.delete(`/datasets/${tableName}`);
}

// ── Connection API ─────────────────────────────────────

export interface ConnectionConfig {
  display_name: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
}

export interface ConnectionInfo {
  id: string;
  display_name: string;
  host: string;
  port: number;
  database: string;
  status: string;
  table_count: number;
  created_at: string;
}

export async function testConnection(
  config: ConnectionConfig,
): Promise<{ success: boolean; count?: number; error?: string }> {
  const res = await api.post("/connections/test", config);
  return res.data;
}

export async function saveConnection(
  config: ConnectionConfig,
): Promise<ConnectionInfo & { count: number }> {
  const res = await api.post("/connections", config);
  return res.data;
}

export async function listConnections(): Promise<{
  connections: ConnectionInfo[];
}> {
  const res = await api.get("/connections");
  return res.data;
}

export async function deleteConnection(id: string): Promise<void> {
  await api.delete(`/connections/${id}`);
}

// ── Auth API ───────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  user: UserInfo;
}

export interface UserInfo {
  id: string;
  username: string;
  display_name: string | null;
}

export async function login(
  username: string,
  password: string,
): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/login", {
    username,
    password,
  });
  return res.data;
}

export async function register(
  username: string,
  password: string,
  displayName?: string,
): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/register", {
    username,
    password,
    display_name: displayName,
  });
  return res.data;
}

export async function getMe(): Promise<UserInfo> {
  const res = await api.get<UserInfo>("/auth/me");
  return res.data;
}

export default api;
