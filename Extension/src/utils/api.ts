import { ApiKeys, ChatMessage, ChatSession } from "./storage";

type BackendSession = {
  id: number;
  user_id: string;
  title: string;
  created_at: string;
};

type BackendMessage = {
  id: number;
  session_id: number;
  sender: string;
  message: string;
  timestamp: string;
};

const DEFAULT_BASE_URL =
  "https://locks-impacts-transparent-realized.trycloudflare.com";
const CHAT_BASE_PATH = "/chat";

const API_BASE_URL =
  (typeof window !== "undefined" &&
    (window as unknown as { CANVAI_API_BASE_URL?: string })
      .CANVAI_API_BASE_URL) ||
  DEFAULT_BASE_URL;

const NORMALIZED_BASE_URL = API_BASE_URL.replace(/\/$/, "");

const buildUrl = (path: string) =>
  `${NORMALIZED_BASE_URL}${CHAT_BASE_PATH}${path}`;

const buildRootUrl = (path: string) => `${NORMALIZED_BASE_URL}${path}`;

export const buildBackendUrl = (path: string) => buildRootUrl(path);

type ApiKeyField = keyof ApiKeys;

const API_KEY_FIELDS: ApiKeyField[] = [
  "canvas_key",
  "gemini_key",
  "canvas_base_url",
  "elevenlabs_api_key",
  "openrouter_api_key",
];

const normalizeApiKeys = (
  payload: Partial<Record<ApiKeyField, unknown>> | null | undefined
): ApiKeys => {
  const record: Partial<Record<ApiKeyField, string>> = {};
  API_KEY_FIELDS.forEach((field) => {
    const raw = payload?.[field];
    record[field] =
      typeof raw === "string" ? raw : raw == null ? "" : String(raw);
  });
  return record as ApiKeys;
};

const toChatSession = (session: BackendSession): ChatSession => {
  const createdAt = session.created_at ?? new Date().toISOString();
  return {
    id: String(session.id),
    title: session.title ?? "New Conversation",
    createdAt,
    updatedAt: createdAt,
    messages: [],
  };
};

const toChatMessage = (message: BackendMessage): ChatMessage => {
  const role =
    message.sender === "assistant" ||
    message.sender === "system" ||
    message.sender === "user"
      ? (message.sender as ChatMessage["role"])
      : "system";

  return {
    id: String(message.id),
    role,
    content: message.message ?? "",
    createdAt: message.timestamp ?? new Date().toISOString(),
  };
};

const readJson = async <T>(response: Response): Promise<T> => {
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new Error(`Invalid JSON payload: ${(error as Error).message}`);
  }
};

export const backendApi = {
  async devSearch(query: string): Promise<unknown> {
    try {
      const url = buildRootUrl(`/search?query=${encodeURIComponent(query)}`);
      const response = await fetch(url, {
        method: "GET",
        headers: { accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`Search request failed (${response.status})`);
      }

      const body = await response.text();
      if (!body) {
        return {};
      }

      try {
        return JSON.parse(body) as unknown;
      } catch {
        return body;
      }
    } catch (error) {
      console.error("[CanvAI] Dev search request failed", error);
      throw error;
    }
  },

  async fetchUserKeys(): Promise<ApiKeys> {
    try {
      const response = await fetch(buildRootUrl("/user/keys"), {
        method: "GET",
        headers: { accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch user keys (${response.status})`);
      }

      const payload = await readJson<{
        keys?: Partial<Record<ApiKeyField, unknown>>;
      }>(response);
      return normalizeApiKeys(payload.keys);
    } catch (error) {
      console.error("[CanvAI] Unable to fetch user keys", error);
      return normalizeApiKeys(null);
    }
  },

  async updateUserKey(
    field: ApiKeyField,
    value: string
  ): Promise<string | null> {
    try {
      const response = await fetch(
        buildRootUrl(`/user/${encodeURIComponent(field)}`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update ${field} (${response.status})`);
      }

      const payload = await readJson<Partial<Record<ApiKeyField, unknown>>>(
        response
      );
      const nextValue = payload[field];
      if (typeof nextValue === "string") {
        return nextValue;
      }
      return value;
    } catch (error) {
      console.error(`[CanvAI] Unable to update ${field}`, error);
      return null;
    }
  },

  async fetchSessions(): Promise<ChatSession[]> {
    try {
      const response = await fetch(buildUrl("/sessions"), {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch sessions (${response.status})`);
      }

      const payload = await readJson<{ sessions?: BackendSession[] }>(response);
      const sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
      return sessions.map(toChatSession);
    } catch (error) {
      console.error("[CanvAI] Unable to fetch sessions from backend", error);
      return [];
    }
  },

  async fetchSessionMessages(sessionId: string): Promise<ChatMessage[]> {
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

      const payload = await readJson<{ messages?: BackendMessage[] }>(response);
      const messages = Array.isArray(payload.messages) ? payload.messages : [];
      return messages.map(toChatMessage);
    } catch (error) {
      console.error(
        `[CanvAI] Unable to load messages for session ${sessionId}`,
        error
      );
      return [];
    }
  },

  async createSession(options: {
    userId: string;
    title: string;
  }): Promise<ChatSession | null> {
    try {
      const response = await fetch(buildUrl("/sessions"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: options.userId,
          title: options.title,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create session (${response.status})`);
      }

      const payload = await readJson<{ session?: BackendSession }>(response);
      if (!payload.session) {
        throw new Error("Backend did not return a session payload");
      }

      return toChatSession(payload.session);
    } catch (error) {
      console.error("[CanvAI] Unable to create chat session", error);
      return null;
    }
  },

  async updateSessionTitle(sessionId: string, title: string): Promise<void> {
    try {
      const response = await fetch(
        buildUrl(`/sessions/${encodeURIComponent(sessionId)}`),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update session (${response.status})`);
      }
    } catch (error) {
      console.error(
        `[CanvAI] Unable to update session ${sessionId} title`,
        error
      );
    }
  },

  async deleteSession(sessionId: string): Promise<void> {
    try {
      const response = await fetch(
        buildUrl(`/sessions/${encodeURIComponent(sessionId)}`),
        {
          method: "DELETE",
        }
      );

      if (!response.ok && response.status !== 404) {
        throw new Error(`Failed to delete session (${response.status})`);
      }
    } catch (error) {
      console.error(`[CanvAI] Unable to delete session ${sessionId}`, error);
    }
  },

  async appendMessage(
    sessionId: string,
    message: ChatMessage
  ): Promise<ChatMessage | null> {
    try {
      const response = await fetch(
        buildUrl(`/sessions/${encodeURIComponent(sessionId)}/messages`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sender: message.role,
            message: message.content,
            timestamp: message.createdAt,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to append message (${response.status})`);
      }

      const payload = await readJson<{ message?: BackendMessage }>(response);
      if (!payload.message) {
        throw new Error("Backend did not return a message payload");
      }

      return toChatMessage(payload.message);
    } catch (error) {
      console.error(
        `[CanvAI] Unable to append message ${message.id} for session ${sessionId}`,
        error
      );
      return null;
    }
  },

  async requestAssistantResponse(
    sessionId: string
  ): Promise<ChatMessage | null> {
    try {
      const response = await fetch(
        buildUrl(`/sessions/${encodeURIComponent(sessionId)}/assistant`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (response.status === 404) {
        return null;
      }

      if (!response.ok) {
        throw new Error(
          `Failed to request assistant response (${response.status})`
        );
      }

      const payload = await readJson<{ message?: BackendMessage }>(response);
      if (!payload.message) {
        return null;
      }

      return toChatMessage(payload.message);
    } catch (error) {
      console.error(
        `[CanvAI] Unable to fetch assistant response for session ${sessionId}`,
        error
      );
      return null;
    }
  },
};
