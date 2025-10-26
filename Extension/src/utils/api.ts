import { ChatMessage, ChatSession } from "./storage";

// Placeholder base URL for the local backend; update when wiring real endpoints.
const API_BASE_URL =
  (typeof window !== "undefined" &&
    (window as unknown as { CANVAI_API_BASE_URL?: string })
      .CANVAI_API_BASE_URL) ||
  "http://localhost:8000/api";

const buildUrl = (path: string) => `${API_BASE_URL}${path}`;

const parseSessions = (payload: unknown): ChatSession[] => {
  if (!payload) return [];
  if (Array.isArray(payload)) {
    return payload as ChatSession[];
  }
  if (typeof payload === "object" && "sessions" in (payload as Record<string, unknown>)) {
    const { sessions } = payload as { sessions?: ChatSession[] };
    return Array.isArray(sessions) ? sessions : [];
  }
  return [];
};

export const backendApi = {
  async fetchSessions(): Promise<ChatSession[]> {
    try {
      const response = await fetch(buildUrl("/sessions"), {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions (${response.status})`);
      }

      const payload = (await response.json()) as unknown;
      return parseSessions(payload);
    } catch (error) {
      console.error("[CanvAI] Unable to fetch sessions from backend", error);
      return [];
    }
  },

  async upsertSession(session: ChatSession): Promise<void> {
    try {
      await fetch(buildUrl(`/sessions/${encodeURIComponent(session.id)}`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session }),
      });
    } catch (error) {
      console.error(
        `[CanvAI] Unable to upsert session ${session.id} in backend`,
        error
      );
    }
  },

  async deleteSession(sessionId: string): Promise<void> {
    try {
      await fetch(buildUrl(`/sessions/${encodeURIComponent(sessionId)}`), {
        method: "DELETE",
      });
    } catch (error) {
      console.error(`[CanvAI] Unable to delete session ${sessionId}`, error);
    }
  },

  async fetchSessionMessages(
    sessionId: string
  ): Promise<ChatMessage[]> {
    try {
      const response = await fetch(
        buildUrl(`/sessions/${encodeURIComponent(sessionId)}/messages`),
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Failed to fetch messages for session (${response.status})`
        );
      }

      const payload = (await response.json()) as unknown;
      if (Array.isArray(payload)) {
        return payload as ChatMessage[];
      }
      if (
        payload &&
        typeof payload === "object" &&
        "messages" in (payload as Record<string, unknown>)
      ) {
        const { messages } = payload as { messages?: ChatMessage[] };
        return Array.isArray(messages) ? messages : [];
      }
      return [];
    } catch (error) {
      console.error(
        `[CanvAI] Unable to load messages for session ${sessionId}`,
        error
      );
      return [];
    }
  },

  async appendMessage(
    sessionId: string,
    message: ChatMessage
  ): Promise<void> {
    try {
      await fetch(buildUrl(`/sessions/${encodeURIComponent(sessionId)}/messages`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
    } catch (error) {
      console.error(
        `[CanvAI] Unable to append message ${message.id} for session ${sessionId}`,
        error
      );
    }
  },

  async requestAssistantResponse(
    sessionId: string
  ): Promise<ChatMessage | null> {
    try {
      const response = await fetch(
        buildUrl(`/sessions/${encodeURIComponent(sessionId)}/response`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to request assistant response (${response.status})`);
      }

      const payload = (await response.json()) as unknown;
      if (
        payload &&
        typeof payload === "object" &&
        "message" in (payload as Record<string, unknown>)
      ) {
        return (payload as { message: ChatMessage | null }).message ?? null;
      }
      return null;
    } catch (error) {
      console.error(
        `[CanvAI] Unable to fetch assistant response for session ${sessionId}`,
        error
      );
      return null;
    }
  },
};
