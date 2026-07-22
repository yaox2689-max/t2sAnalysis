import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 15000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error);
    return Promise.reject(error);
  },
);

// ── Types ──────────────────────────────────────────────

export interface ChatRequest {
  question: string;
  session_id: string;
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
  elapsed_ms: number;
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

export default api;
