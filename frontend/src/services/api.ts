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

export default api;
