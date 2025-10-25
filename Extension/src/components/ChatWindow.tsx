import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChatMessage,
  ChatSession,
  storage,
  storageDefaults,
} from "../utils/storage";

const GearIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
    <path d="m19.4 15-.8 1.4a2 2 0 0 1-2.1.9l-.6-.2a5.3 5.3 0 0 0-1.8 1l-.1.6a2 2 0 0 1-2 1.6h-1.6a2 2 0 0 1-2-1.6l-.1-.6a5.3 5.3 0 0 0-1.8-1l-.6.2a2 2 0 0 1-2.1-.9L4.6 15a2 2 0 0 1 .5-2.5l.5-.4a5.3 5.3 0 0 0 0-2l-.5-.4a2 2 0 0 1-.5-2.5l.8-1.4a2 2 0 0 1 2.1-.9l.6.2a5.3 5.3 0 0 0 1.8-1l.1-.6a2 2 0 0 1 2-1.6h1.6a2 2 0 0 1 2 1.6l.1.6a5.3 5.3 0 0 0 1.8 1l.6-.2a2 2 0 0 1 2.1.9L19.4 9a2 2 0 0 1-.5 2.5l-.5.4a5.3 5.3 0 0 0 0 2l.5.4a2 2 0 0 1 .5 2.5Z" />
  </svg>
);

export interface ChatWindowProps {
  onDragHandleDown: (event: React.PointerEvent<HTMLDivElement>) => void;
  onResizeHandleDown: (event: React.PointerEvent<HTMLDivElement>) => void;
  onMinimize: () => void;
  onOpenSettings: () => void;
  onClose: () => void;
}

const generateId = () => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const createSession = (): ChatSession => {
  const now = new Date().toISOString();
  return {
    id: `session-${generateId()}`,
    title: "New Conversation",
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
};

const formatTitle = (content: string): string => {
  const base = content.split("\n")[0].slice(0, 28).trim();
  return base.length
    ? `${base}${content.length > 28 ? "..." : ""}`
    : "Untitled";
};

export const ChatWindow: React.FC<ChatWindowProps> = ({
  onDragHandleDown,
  onResizeHandleDown,
  onMinimize,
  onOpenSettings,
  onClose,
}) => {
  const [sessions, setSessions] = useState<Record<string, ChatSession>>({});
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [inputValue, setInputValue] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const activeSession = useMemo(
    () => sessions[activeSessionId],
    [sessions, activeSessionId]
  );

  useEffect(() => {
    void storage.ensureInitialized().then(async () => {
      const { chats, lastSessionId } = await storage.getMany([
        "chats",
        "lastSessionId",
      ]);
      setSessions(chats);
      if (lastSessionId && chats[lastSessionId]) {
        setActiveSessionId(lastSessionId);
      } else {
        const firstSessionId =
          Object.keys(chats)[0] ?? storageDefaults.session.id;
        setActiveSessionId(firstSessionId);
      }
    });
  }, []);

  useEffect(() => {
    return storage.subscribe((changes) => {
      if (changes.chats) {
        setSessions(changes.chats);
      }
      if (
        typeof changes.lastSessionId === "string" &&
        changes.lastSessionId !== activeSessionId
      ) {
        setActiveSessionId(changes.lastSessionId);
      }
    });
  }, [activeSessionId]);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [activeSession?.messages.length]);

  const orderedSessions = useMemo(() => {
    return Object.values(sessions).sort((a, b) =>
      a.updatedAt < b.updatedAt ? 1 : -1
    );
  }, [sessions]);

  const persistSessions = useCallback(
    async (nextSessions: Record<string, ChatSession>, selectedId: string) => {
      await storage.setMany({
        chats: nextSessions,
        lastSessionId: selectedId,
      });
    },
    []
  );

  const handleSelectSession = useCallback(
    (sessionId: string) => {
      if (sessionId === activeSessionId) return;
      if (!sessions[sessionId]) return;
      setActiveSessionId(sessionId);
      void storage.set("lastSessionId", sessionId);
    },
    [activeSessionId, sessions]
  );

  const handleCreateSession = useCallback(() => {
    setSessions((prev) => {
      const next = { ...prev };
      const newSession = createSession();
      next[newSession.id] = newSession;
      setActiveSessionId(newSession.id);
      void persistSessions(next, newSession.id);
      return next;
    });
  }, [persistSessions]);

  const handleDeleteSession = useCallback(
    (sessionId: string) => {
      if (Object.keys(sessions).length === 1) return;
      setSessions((prev) => {
        const next = { ...prev };
        delete next[sessionId];
        const fallbackId =
          sessionId === activeSessionId
            ? Object.values(next).sort((a, b) =>
                a.updatedAt < b.updatedAt ? 1 : -1
              )[0]?.id ?? storageDefaults.session.id
            : activeSessionId;
        setActiveSessionId(fallbackId);
        void persistSessions(next, fallbackId);
        return next;
      });
    },
    [activeSessionId, persistSessions, sessions]
  );

  const handleUpdateSessionTitle = useCallback(
    (sessionId: string, title: string) => {
      setSessions((prev) => {
        const target = prev[sessionId];
        if (!target) return prev;
        const next: Record<string, ChatSession> = {
          ...prev,
          [sessionId]: { ...target, title },
        };
        void storage.set("chats", next);
        return next;
      });
    },
    []
  );

  const handleSendMessage = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;

    setInputValue("");

    setSessions((prev) => {
      const now = new Date().toISOString();
      const sessionId =
        activeSessionId && prev[activeSessionId]
          ? activeSessionId
          : createSession().id;

      const baseSession = prev[sessionId] ?? {
        ...createSession(),
        id: sessionId,
      };

      const userMessage: ChatMessage = {
        id: `msg-${generateId()}`,
        role: "user",
        content: trimmed,
        createdAt: now,
      };

      const nextSession: ChatSession = {
        ...baseSession,
        messages: [...baseSession.messages, userMessage],
        updatedAt: now,
        title:
          baseSession.messages.length === 0 &&
          baseSession.title === "New Conversation"
            ? formatTitle(trimmed)
            : baseSession.title,
      };

      const updatedSessions = {
        ...prev,
        [sessionId]: nextSession,
      };

      setActiveSessionId(sessionId);
      void persistSessions(updatedSessions, sessionId);

      return updatedSessions;
    });
  }, [activeSessionId, inputValue, persistSessions]);

  const handleInputKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );

  return (
    <div className="flex h-full min-h-0 w-full min-w-0">
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.aside
            key="sidebar"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 240, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="flex h-full flex-shrink-0 flex-col bg-[rgba(28,27,34,0.85)]/90 backdrop-blur-xl"
          >
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-slate-300">
                Sessions
              </span>
              <button
                type="button"
                onClick={() => setSidebarOpen(false)}
                className="rounded-full border border-transparent px-3 py-1 text-xs text-slate-400 transition hover:border-slate-700 hover:text-slate-200"
              >
                Hide
              </button>
            </div>
            <div className="canvai-scrollbar flex-1 overflow-y-auto px-2 pb-4">
              {orderedSessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <motion.button
                    key={session.id}
                    type="button"
                    onClick={() => handleSelectSession(session.id)}
                    className={`group relative flex w-full flex-col rounded-xl border border-transparent px-3 py-3 text-left transition ${
                      isActive
                        ? "bg-[rgba(0,173,181,0.12)] border-[rgba(0,173,181,0.45)]"
                        : "hover:bg-[rgba(40,39,45,0.65)]"
                    }`}
                    whileHover={{ x: 2 }}
                  >
                    <span className="text-sm font-semibold text-slate-100">
                      {session.title}
                    </span>
                    <span className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
                      {new Date(session.updatedAt).toLocaleString(undefined, {
                        hour: "2-digit",
                        minute: "2-digit",
                        month: "short",
                        day: "2-digit",
                      })}
                    </span>
                    <div className="pointer-events-auto absolute right-3 top-3 flex gap-1 opacity-0 transition group-hover:opacity-100">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          const newTitle = prompt(
                            "Rename conversation",
                            session.title
                          );
                          if (newTitle?.trim()) {
                            handleUpdateSessionTitle(
                              session.id,
                              newTitle.trim()
                            );
                          }
                        }}
                        className="rounded-full border border-transparent px-2 py-1 text-[11px] uppercase tracking-[0.2em] text-slate-400 hover:border-slate-600 hover:text-slate-100"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          if (
                            confirm(
                              "Delete this conversation? This action cannot be undone."
                            )
                          ) {
                            handleDeleteSession(session.id);
                          }
                        }}
                        className="rounded-full border border-transparent px-2 py-1 text-[11px] uppercase tracking-[0.2em] text-slate-400 hover:border-red-400 hover:text-red-300"
                      >
                        Del
                      </button>
                    </div>
                  </motion.button>
                );
              })}
            </div>
            <div className="border-t border-[rgba(40,39,45,0.5)] p-3">
              <button
                type="button"
                onClick={handleCreateSession}
                className="flex w-full items-center justify-center gap-2 rounded-full bg-[rgba(0,173,181,0.12)] px-4 py-2 text-sm font-medium text-[rgba(0,173,181,0.95)] transition hover:bg-[rgba(0,173,181,0.2)] hover:text-[rgba(0,173,181,1)]"
              >
                <span className="text-lg leading-none">+</span>
                <span>New chat</span>
              </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="relative flex min-w-0 flex-1 flex-col">
        <div
          className="canvai-window-header flex cursor-pointer items-center justify-between border-b border-[rgba(40,39,45,0.45)] px-5 py-3"
          onPointerDown={onDragHandleDown}
        >
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setSidebarOpen((prev) => !prev)}
              className="rounded-full border border-[rgba(40,39,45,0.7)] px-3 py-1 text-xs uppercase tracking-[0.25em] text-slate-300 transition hover:border-[rgba(0,173,181,0.5)] hover:text-[rgba(0,173,181,0.95)]"
            >
              {sidebarOpen ? "Hide" : "Show"} Sessions
            </button>
            <div className="flex flex-col">
              <span className="text-sm font-semibold uppercase tracking-[0.4em] text-slate-200">
                CanvAI
              </span>
              <span className="text-[11px] uppercase tracking-[0.3em] text-slate-500">
                PSU Companion
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onOpenSettings}
              aria-label="Open settings"
              className="flex h-8 w-8 items-center justify-center rounded-full border border-[rgba(40,39,45,0.6)] text-slate-300 transition hover:border-[rgba(0,173,181,0.5)] hover:text-[rgba(0,173,181,0.95)]"
            >
              <GearIcon className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={onMinimize}
              aria-label="Minimize window"
              className="flex h-8 w-8 items-center justify-center rounded-full border border-[rgba(40,39,45,0.6)] text-base font-semibold text-slate-300 transition hover:border-[rgba(0,173,181,0.5)] hover:text-[rgba(0,173,181,0.95)]"
            >
              -
            </button>
          </div>
        </div>

        <div className="flex min-h-0 flex-1 flex-col">
          <div
            ref={scrollRef}
            className="canvai-scrollbar flex-1 overflow-y-auto px-6 py-5"
          >
            <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
              <AnimatePresence initial={false}>
                {(activeSession?.messages ?? []).map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 12, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -12 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className={`w-full rounded-3xl border border-[rgba(255,255,255,0.05)] px-5 py-4 ${
                      message.role === "user"
                        ? "bg-[rgba(0,173,181,0.18)] text-slate-100"
                        : "bg-[rgba(28,27,34,0.9)] text-slate-300"
                    }`}
                  >
                    <span className="mb-1 block text-[11px] uppercase tracking-[0.3em] text-slate-400">
                      {message.role}
                    </span>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {message.content}
                    </p>
                  </motion.div>
                ))}
              </AnimatePresence>
              {!activeSession?.messages.length && (
                <div className="rounded-3xl border border-[rgba(40,39,45,0.6)] bg-[rgba(28,27,34,0.75)] px-6 py-8 text-center text-sm text-slate-400">
                  Start the conversation by introducing yourself or pasting a
                  Canvas task. I&apos;ll remember this chat for you.
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-[rgba(40,39,45,0.45)] px-6 pb-6 pt-4">
            <div className="mx-auto flex w-full max-w-2xl flex-col gap-3">
              <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.35em] text-slate-500">
                <span>Type your prompt</span>
                <span>Enter to send | Shift + Enter = New line</span>
              </div>
              <form
                className="flex items-end gap-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  handleSendMessage();
                }}
              >
                <textarea
                  value={inputValue}
                  onChange={(event) => setInputValue(event.target.value)}
                  onKeyDown={handleInputKeyDown}
                  rows={1}
                  placeholder="Ask CanvAI anything..."
                  className="h-14 w-full flex-1 resize-none rounded-full border border-[rgba(40,39,45,0.7)] bg-[rgba(20,19,26,0.9)] px-6 py-4 text-sm text-slate-100 shadow-[0_10px_30px_rgba(0,0,0,0.35)] transition focus:border-[rgba(0,173,181,0.5)] focus:outline-none focus:ring-2 focus:ring-[rgba(0,173,181,0.4)]"
                />
                <button
                  type="submit"
                  className="flex h-14 w-20 items-center justify-center rounded-full bg-[rgba(0,173,181,0.9)] text-xs font-semibold uppercase tracking-[0.35em] text-slate-900 transition hover:bg-[rgba(0,173,181,1)]"
                >
                  Send
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div
        role="button"
        tabIndex={-1}
        className="canvai-resize-handle"
        onPointerDown={onResizeHandleDown}
        onClick={(event) => event.stopPropagation()}
      />
    </div>
  );
};

export default ChatWindow;
