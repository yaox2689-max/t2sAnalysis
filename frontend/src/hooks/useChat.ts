import { useState, useRef, useEffect, useCallback } from "react";
import { message } from "antd";
import {
  sendChatStream,
  createSession,
  getSessionMessages,
  MessageInfo,
} from "../services/api";

/**
 * Manages chat state (messages, loading, session init) and SSE streaming.
 *
 * @param sessionId - current session id from URL params (may be null)
 * @param onSessionCreated - called when a new session is created so the
 *   parent can update the URL
 */
export function useChat(
  sessionId: string | null,
  onSessionCreated: (id: string) => void,
) {
  const [messages, setMessages] = useState<MessageInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [progressLabel, setProgressLabel] = useState<string | undefined>(
    undefined,
  );
  const [initLoading, setInitLoading] = useState(true);

  const loadingRef = useRef(false);
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const sendAbortRef = useRef<AbortController | null>(null);

  // Scroll helper
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  // Initialise session / load history
  useEffect(() => {
    const controller = new AbortController();
    const init = async () => {
      setInitLoading(true);
      try {
        let sid = sessionId;
        if (!sid) {
          const res = await createSession();
          if (controller.signal.aborted) return;
          sid = res.session_id;
          onSessionCreated(sid);
        } else {
          const res = await getSessionMessages(sid);
          if (controller.signal.aborted) return;
          setMessages(res.messages);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error("Init error:", err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setInitLoading(false);
        }
      }
    };
    init();
    return () => controller.abort();
  }, [sessionId, onSessionCreated]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => sendAbortRef.current?.abort();
  }, []);

  /** Send a chat message via SSE stream. */
  const handleSend = useCallback(
    async (text?: string, inputRef?: React.MutableRefObject<string>) => {
      const question = (text ?? inputRef?.current ?? "").trim();
      const sid = sessionIdRef.current;
      if (!question || loadingRef.current || !sid) return;

      loadingRef.current = true;
      setLoading(true);
      setProgressLabel("AI 正在分析您的问题");

      let finished = false;
      const finish = () => {
        if (finished) return;
        finished = true;
        loadingRef.current = false;
        setLoading(false);
        setProgressLabel(undefined);
      };

      // Safety timeout: if stream hangs for 3 minutes, force finish
      const safetyTimer = setTimeout(finish, 180000);

      const controller = sendChatStream(
        { question, session_id: sid },
        (event) => {
          if (event.type === "progress" && event.label) {
            setProgressLabel(`${event.label}...`);
          }
        },
        (err) => {
          clearTimeout(safetyTimer);
          message.error(err.message || "请求失败，请稍后重试");
          finish();
        },
        async () => {
          clearTimeout(safetyTimer);
          try {
            const updated = await getSessionMessages(sid);
            setMessages(updated.messages);
          } catch {
            // ignore
          }
          finish();
        },
      );
      sendAbortRef.current = controller;
    },
    [],
  );

  return {
    messages,
    loading,
    progressLabel,
    initLoading,
    messagesEndRef,
    handleSend,
  };
}
