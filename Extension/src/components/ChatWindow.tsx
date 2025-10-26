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
import { backendApi } from "../utils/api";

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

const SidebarIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M9 3v18" />
  </svg>
);

const PencilIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
    <path d="m15 5 4 4" />
  </svg>
);

const TrashIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M3 6h18" />
    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
    <line x1="10" x2="10" y1="11" y2="17" />
    <line x1="14" x2="14" y1="11" y2="17" />
  </svg>
);

export interface ChatWindowProps {
  onDragHandleDown: (event: React.PointerEvent<HTMLDivElement>) => void;
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

const createLocalSession = (): ChatSession => {
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

const selectActiveSessionId = (
  sessionsMap: Record<string, ChatSession>,
  preferredId?: string | null
): string => {
  if (preferredId && sessionsMap[preferredId]) {
    return preferredId;
  }
  const [latest] = Object.values(sessionsMap).sort((a, b) =>
    a.updatedAt < b.updatedAt ? 1 : -1
  );
  return latest?.id ?? storageDefaults.session.id;
};

const DEFAULT_USER_ID = "local-user";

export const ChatWindow: React.FC<ChatWindowProps> = ({
  onDragHandleDown,
  onMinimize,
  onOpenSettings,
  onClose,
}) => {
  const [sessions, setSessions] = useState<Record<string, ChatSession>>({});
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [inputValue, setInputValue] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [devSearchLoading, setDevSearchLoading] = useState(false);
  const activeSessionRef = useRef<string>("");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const activeSession = useMemo(
    () => sessions[activeSessionId],
    [sessions, activeSessionId]
  );

  useEffect(() => {
    activeSessionRef.current = activeSessionId;
  }, [activeSessionId]);

  useEffect(() => {
    let isMounted = true;

    const hydrateSessions = async () => {
      await storage.ensureInitialized();

      const { chats, lastSessionId } = await storage.getMany([
        "chats",
        "lastSessionId",
      ]);

      const initialActiveId = selectActiveSessionId(chats, lastSessionId);

      if (isMounted) {
        setSessions(chats);
        setActiveSessionId(initialActiveId);
      }
      activeSessionRef.current = initialActiveId;

      const remoteSessions = await backendApi.fetchSessions();
      if (!isMounted || remoteSessions.length === 0) {
        return;
      }

      const remoteMap = remoteSessions.reduce<Record<string, ChatSession>>(
        (acc, session) => {
          const existing = chats[session.id];
          acc[session.id] = {
            ...session,
            messages: existing?.messages?.length
              ? existing.messages
              : session.messages ?? [],
            updatedAt:
              existing?.updatedAt ?? session.updatedAt ?? session.createdAt,
          };
          return acc;
        },
        { ...chats }
      );

      const resolvedActiveId = selectActiveSessionId(
        remoteMap,
        activeSessionRef.current
      );

      await storage.setMany({
        chats: remoteMap,
        lastSessionId: resolvedActiveId,
      });

      if (!isMounted) {
        return;
      }

      setSessions(remoteMap);
      setActiveSessionId(resolvedActiveId);
      activeSessionRef.current = resolvedActiveId;
    };

    void hydrateSessions();

    return () => {
      isMounted = false;
    };
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

  const orderedSessions = useMemo<ChatSession[]>(() => {
    const values = Object.values(sessions);
    values.sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
    return values;
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

  const handleRunDevSearch = useCallback(async () => {
    setDevSearchLoading(true);
    try {
      const result = await backendApi.devSearch("what are my classes.");
      console.info("[CanvAI] Dev search response:", result);
    } catch (error) {
      console.error("[CanvAI] Dev search request failed", error);
    } finally {
      setDevSearchLoading(false);
    }
  }, []);

  const handleSelectSession = useCallback(
    (sessionId: string) => {
      if (!sessions[sessionId]) return;

      if (sessionId !== activeSessionId) {
        setActiveSessionId(sessionId);
        activeSessionRef.current = sessionId;
        void storage.set("lastSessionId", sessionId);
      }

      void (async () => {
        if (!/^\d+$/.test(sessionId)) return;
        try {
          const remoteMessages =
            await backendApi.fetchSessionMessages(sessionId);

          setSessions((prev) => {
            const target = prev[sessionId];
            if (!target) return prev;

            const nextSession: ChatSession = {
              ...target,
              messages: remoteMessages,
              updatedAt:
                remoteMessages[remoteMessages.length - 1]?.createdAt ??
                target.updatedAt ??
                target.createdAt,
            };

            const nextSessions = {
              ...prev,
              [sessionId]: nextSession,
            };

            void storage.set("chats", nextSessions);
            return nextSessions;
          });
        } catch (error) {
          console.error(
            `[CanvAI] Unable to load messages for session ${sessionId}`,
            error
          );
        }
      })();
    },
    [activeSessionId, sessions]
  );

  const handleCreateSession = useCallback(() => {
    void (async () => {
      const remoteSession = await backendApi.createSession({
        userId: DEFAULT_USER_ID,
        title: "New Conversation",
      });

      const session = remoteSession ?? createLocalSession();

      setSessions((prev) => {
        const next = { ...prev, [session.id]: session };
        setActiveSessionId(session.id);
        activeSessionRef.current = session.id;
        void persistSessions(next, session.id);
        return next;
      });
    })();
  }, [persistSessions]);

  const handleDeleteSession = useCallback(
    (sessionId: string) => {
      if (Object.keys(sessions).length === 1) return;
      setSessions((prev) => {
        const next = { ...prev };
        delete next[sessionId];
        const fallbackId =
          sessionId === activeSessionId
            ? selectActiveSessionId(next, null)
            : activeSessionId;
        setActiveSessionId(fallbackId);
        activeSessionRef.current = fallbackId;
        void persistSessions(next, fallbackId);
        return next;
      });
      if (/^\d+$/.test(sessionId)) {
        void backendApi.deleteSession(sessionId);
      }
    },
    [activeSessionId, persistSessions, sessions]
  );

  const handleUpdateSessionTitle = useCallback(
    (sessionId: string, title: string) => {
      let updatedSession: ChatSession | null = null;
      setSessions((prev) => {
        const target = prev[sessionId];
        if (!target) return prev;
        const next: Record<string, ChatSession> = {
          ...prev,
          [sessionId]: { ...target, title },
        };
        updatedSession = next[sessionId];
        void storage.set("chats", next);
        return next;
      });
      if (updatedSession) {
        if (/^\d+$/.test(sessionId)) {
          void backendApi.updateSessionTitle(sessionId, title);
        }
      }
    },
    []
  );

  const handleStartEditingTitle = useCallback(
    (sessionId: string, currentTitle: string) => {
      setEditingSessionId(sessionId);
      setEditingTitle(currentTitle);
    },
    []
  );

  const handleSaveEditingTitle = useCallback(() => {
    if (editingSessionId && editingTitle.trim()) {
      handleUpdateSessionTitle(editingSessionId, editingTitle.trim());
    }
    setEditingSessionId(null);
    setEditingTitle("");
  }, [editingSessionId, editingTitle, handleUpdateSessionTitle]);

  const handleCancelEditingTitle = useCallback(() => {
    setEditingSessionId(null);
    setEditingTitle("");
  }, []);

  const handleSendMessage = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;

    setInputValue("");

    const now = new Date().toISOString();
    const provisionalMessage: ChatMessage = {
      id: `msg-${generateId()}`,
      role: "user",
      content: trimmed,
      createdAt: now,
    };

    void (async () => {
      let currentSessionId = activeSessionId;
      let workingSession =
        (currentSessionId && sessions[currentSessionId]) || null;

      if (!workingSession) {
        workingSession = createLocalSession();
        currentSessionId = workingSession.id;
      }

      const originalSessionId = workingSession.id;
      const initialTitle = workingSession.title;
      const shouldDeriveTitle =
        workingSession.messages.length === 0 &&
        initialTitle === "New Conversation";
      const derivedTitle = shouldDeriveTitle
        ? formatTitle(trimmed)
        : initialTitle;
      const titleChanged = derivedTitle !== initialTitle;

      let remoteSessionId = originalSessionId;

      if (!/^\d+$/.test(remoteSessionId)) {
        try {
          const createdSession = await backendApi.createSession({
            userId: DEFAULT_USER_ID,
            title: derivedTitle || "New Conversation",
          });

          if (createdSession) {
            remoteSessionId = createdSession.id;
            workingSession = {
              ...createdSession,
              messages: workingSession.messages,
              updatedAt:
                createdSession.updatedAt ?? createdSession.createdAt,
            };
          }
        } catch (error) {
          console.error("[CanvAI] Failed to create remote session", error);
        }
      }

      const nextSession: ChatSession = {
        ...workingSession,
        id: remoteSessionId,
        title: derivedTitle,
        messages: [...(workingSession.messages ?? []), provisionalMessage],
        updatedAt: now,
      };

      let snapshot: Record<string, ChatSession> | null = null;
      setSessions((prev) => {
        const updated = { ...prev };
        if (originalSessionId !== remoteSessionId) {
          delete updated[originalSessionId];
        }
        updated[remoteSessionId] = nextSession;
        snapshot = updated;
        return updated;
      });

      setActiveSessionId(remoteSessionId);
      activeSessionRef.current = remoteSessionId;

      if (snapshot) {
        await persistSessions(snapshot, remoteSessionId);
      }

      const canSync = /^\d+$/.test(remoteSessionId);

      if (canSync) {
        try {
          const storedMessage = await backendApi.appendMessage(
            remoteSessionId,
            provisionalMessage
          );

          if (storedMessage) {
            setSessions((prev) => {
              const target = prev[remoteSessionId];
              if (!target) return prev;

              const replaceIndex = target.messages.findIndex(
                (message) => message.id === provisionalMessage.id
              );

              const nextMessages =
                replaceIndex >= 0
                  ? [
                      ...target.messages.slice(0, replaceIndex),
                      storedMessage,
                      ...target.messages.slice(replaceIndex + 1),
                    ]
                  : [...target.messages, storedMessage];

              const updatedSession: ChatSession = {
                ...target,
                messages: nextMessages,
                updatedAt:
                  storedMessage.createdAt ?? target.updatedAt,
              };

              const updatedSessions = {
                ...prev,
                [remoteSessionId]: updatedSession,
              };

              void storage.set("chats", updatedSessions);
              return updatedSessions;
            });
          }

          if (titleChanged) {
            await backendApi.updateSessionTitle(
              remoteSessionId,
              derivedTitle
            );
          }
        } catch (error) {
          console.error(
            `[CanvAI] Failed to sync message for session ${remoteSessionId}`,
            error
          );
        }

        void (async () => {
          try {
            const assistantMessage =
              await backendApi.requestAssistantResponse(
                remoteSessionId
              );
            if (!assistantMessage) return;

            setSessions((prev) => {
              const target = prev[remoteSessionId];
              if (!target) return prev;

              const updatedSession: ChatSession = {
                ...target,
                messages: [...target.messages, assistantMessage],
                updatedAt:
                  assistantMessage.createdAt ?? target.updatedAt,
              };

              const updatedSessions = {
                ...prev,
                [remoteSessionId]: updatedSession,
              };

              void storage.set("chats", updatedSessions);
              return updatedSessions;
            });
          } catch (error) {
            console.error(
              `[CanvAI] Unable to fetch assistant response for session ${remoteSessionId}`,
              error
            );
          }
        })();
      }
    })();
  }, [activeSessionId, inputValue, persistSessions, sessions]);

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
            className="flex h-full shrink-0 flex-col bg-gradient-to-b from-[rgba(40,39,45,0.98)] to-[rgba(31,30,36,0.95)] border-r border-white/10 backdrop-blur-xl shadow-[4px_0_24px_rgba(0,0,0,0.5),inset_-1px_0_0_rgba(255,255,255,0.05)]"
          >
            <div className="flex items-center justify-between px-4 py-4 border-b border-white/10 bg-black/20">
              <span className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-100">
                Sessions
              </span>
            </div>
            <div className="canvai-scrollbar flex-1 overflow-y-auto px-2 pb-4">
              {orderedSessions.map((session) => {
                const isActive = session.id === activeSessionId;
                const isEditing = editingSessionId === session.id;
                return (
                  <motion.div
                    key={session.id}
                    className={`group relative flex w-full flex-col rounded-2xl border px-4 py-3.5 text-left transition-all duration-300 ${
                      isActive
                        ? "bg-[#4A4A4E] border-[#5E5E62] shadow-[0_4px_16px_rgba(0,0,0,0.4)]"
                        : "bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/15 hover:shadow-[0_4px_16px_rgba(255,255,255,0.05)]"
                    }`}
                    whileHover={!isEditing ? { x: 3, scale: 1.02 } : {}}
                    whileTap={!isEditing ? { scale: 0.98 } : {}}
                    onClick={() =>
                      !isEditing && handleSelectSession(session.id)
                    }
                  >
                    {isEditing ? (
                      <div className="mb-1.5 flex items-center justify-center">
                        <input
                          type="text"
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleSaveEditingTitle();
                            } else if (e.key === "Escape") {
                              e.preventDefault();
                              handleCancelEditingTitle();
                            }
                          }}
                          onBlur={handleSaveEditingTitle}
                          autoFocus
                          className="w-full text-sm font-semibold bg-[#28272D] border-2 border-[#00ADB5] rounded-xl px-3 py-2 text-[#EEEEEE] outline-none shadow-[0_0_20px_rgba(0,173,181,0.25)] placeholder:text-slate-500 transition-all duration-300 focus:border-[#33BFCA] focus:shadow-[0_0_30px_rgba(0,173,181,0.4)]"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                    ) : (
                      <span
                        className={`text-sm font-semibold mb-1.5 ${
                          isActive ? "text-slate-50" : "text-slate-300"
                        }`}
                      >
                        {session.title}
                      </span>
                    )}
                    <span
                      className={`text-[10px] font-mono uppercase tracking-[0.25em] ${
                        isActive ? "text-cyan-300/70" : "text-slate-500"
                      }`}
                    >
                      {new Date(session.updatedAt).toLocaleString(undefined, {
                        hour: "2-digit",
                        minute: "2-digit",
                        month: "short",
                        day: "2-digit",
                      })}
                    </span>
                    {!isEditing && (
                      <div className="pointer-events-auto absolute right-3 top-3 flex gap-1 opacity-0 transition group-hover:opacity-100">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleStartEditingTitle(session.id, session.title);
                          }}
                          aria-label="Edit conversation title"
                          className="flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-white/5 backdrop-blur-sm text-slate-300 hover:border-cyan-400/40 hover:bg-cyan-400/10 hover:text-cyan-200 transition-all duration-200"
                        >
                          <PencilIcon className="h-3.5 w-3.5" />
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
                          aria-label="Delete conversation"
                          className="flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-white/5 backdrop-blur-sm text-slate-300 hover:border-red-400/40 hover:bg-red-400/10 hover:text-red-300 transition-all duration-200"
                        >
                          <TrashIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>
            <div className="border-t border-white/10 p-3 bg-gradient-to-t from-black/30 to-transparent">
              <button
                type="button"
                onClick={handleCreateSession}
                className="flex w-full items-center justify-center gap-2.5 rounded-full bg-white/10 border border-white/20 px-4 py-2.5 text-sm font-semibold text-slate-200 shadow-[0_4px_16px_rgba(255,255,255,0.08)] backdrop-blur-sm transition-all duration-300 hover:bg-cyan-500/20 hover:border-cyan-400/40 hover:text-cyan-200 hover:shadow-[0_6px_24px_rgba(0,173,181,0.2)] hover:scale-[1.02] active:scale-[0.98]"
              >
                <span className="text-xl leading-none font-light">+</span>
                <span className="font-mono text-xs uppercase tracking-[0.2em]">
                  New chat
                </span>
              </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="relative flex min-w-0 flex-1 flex-col">
        <div
          className="canvai-window-header flex cursor-pointer items-center justify-between border-b border-white/10 bg-gradient-to-b from-white/5 to-transparent backdrop-blur-xl px-5 py-3.5"
          onPointerDown={onDragHandleDown}
        >
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setSidebarOpen((prev) => !prev)}
              aria-label={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-200 shadow-sm backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/40 hover:bg-cyan-400/10 hover:text-cyan-300 hover:shadow-[0_4px_16px_rgba(0,173,181,0.2)] hover:scale-105 active:scale-95"
            >
              <SidebarIcon className="h-4 w-4" />
            </button>
            <div className="flex flex-col">
              <span className="text-base font-bold uppercase tracking-[0.35em] text-slate-100">
                CanvAI
              </span>
              <span className="text-[10px] font-mono uppercase tracking-[0.3em] text-cyan-300/60">
                PSU Companion
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleRunDevSearch}
              disabled={devSearchLoading}
              aria-label="Run development search request"
              className="flex h-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-3 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-200 shadow-sm backdrop-blur-sm transition-all duration-300 hover:border-green-400/40 hover:bg-green-400/10 hover:text-green-300 hover:shadow-[0_4px_16px_rgba(34,197,94,0.25)] hover:scale-105 active:scale-95 disabled:pointer-events-none disabled:opacity-60"
            >
              {devSearchLoading ? "Running..." : "Dev Search"}
            </button>
            <button
              type="button"
              onClick={onOpenSettings}
              aria-label="Open settings"
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-200 shadow-sm backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/40 hover:bg-cyan-400/10 hover:text-cyan-300 hover:shadow-[0_4px_16px_rgba(0,173,181,0.2)] hover:scale-105 active:scale-95"
            >
              <GearIcon className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close window"
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-base font-bold text-slate-300 shadow-sm backdrop-blur-sm transition-all duration-300 hover:border-red-400/40 hover:bg-red-400/15 hover:text-red-300 hover:shadow-[0_4px_16px_rgba(239,68,68,0.2)] hover:scale-105 active:scale-95"
            >
              X
            </button>
          </div>
        </div>

        <div className="relative flex min-h-0 flex-1 flex-col">
          <div
            ref={scrollRef}
            className="canvai-scrollbar flex-1 overflow-y-auto px-6 py-5 pb-32"
          >
            <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
              <AnimatePresence initial={false}>
                {(activeSession?.messages ?? []).map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 16, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -16, scale: 0.95 }}
                    transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                    className={`w-full rounded-2xl border backdrop-blur-md px-6 py-4 shadow-lg ${
                      message.role === "user"
                        ? "bg-gradient-to-br from-cyan-500/25 to-cyan-400/15 border-cyan-400/40 text-slate-50 shadow-[0_8px_32px_rgba(0,173,181,0.3),0_4px_16px_rgba(0,173,181,0.2),0_0_0_1px_rgba(0,173,181,0.2)_inset]"
                        : "bg-white/5 border-white/10 text-slate-200 shadow-[0_4px_20px_rgba(0,0,0,0.1)]"
                    }`}
                  >
                    <span
                      className={`mb-2 block text-[10px] font-mono uppercase tracking-[0.35em] ${
                        message.role === "user"
                          ? "text-cyan-300/70"
                          : "text-slate-400"
                      }`}
                    >
                      {message.role}
                    </span>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {message.content}
                    </p>
                  </motion.div>
                ))}
              </AnimatePresence>
              {!activeSession?.messages.length && (
                <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md px-8 py-10 text-center shadow-lg">
                  <p className="text-base leading-relaxed text-slate-300 mb-2">
                    Start the conversation by introducing yourself or pasting a
                    Canvas task.
                  </p>
                  <p className="text-xs font-mono text-cyan-300/60 uppercase tracking-[0.2em]">
                    I&apos;ll remember this chat for you
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Floating Input Box */}
          <div className="absolute bottom-0 left-0 right-0 px-6 pb-6 pt-8 pointer-events-none bg-gradient-to-t from-[rgba(13,12,17,0.98)] via-[rgba(13,12,17,0.92)] to-transparent">
            <div className="mx-auto w-full max-w-3xl pointer-events-auto">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  handleSendMessage();
                }}
              >
                <div className="relative">
                  <textarea
                    value={inputValue}
                    onChange={(event) => setInputValue(event.target.value)}
                    onKeyDown={handleInputKeyDown}
                    rows={1}
                    placeholder="Ask anything..."
                    className="canvai-scrollbar w-full resize-none rounded-full border-2 border-white/20 bg-[rgba(40,39,45,0.97)] backdrop-blur-2xl px-6 py-4 pr-14 text-base text-[#EEEEEE] shadow-[0_12px_48px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.08)_inset,0_0_60px_rgba(0,173,181,0.1)] placeholder:text-slate-400 transition-all duration-300 focus:border-[#00ADB5] focus:bg-[rgba(40,39,45,0.99)] focus:outline-none focus:shadow-[0_16px_64px_rgba(0,173,181,0.4),0_0_0_1px_rgba(0,173,181,0.3)_inset,0_0_80px_rgba(0,173,181,0.2)] hover:border-white/30 hover:shadow-[0_14px_56px_rgba(0,0,0,0.7),0_0_0_1px_rgba(255,255,255,0.12)_inset]"
                    style={{
                      minHeight: "56px",
                      maxHeight: "200px",
                      overflowY: "auto",
                    }}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      target.style.height = "56px";
                      const newHeight = Math.min(target.scrollHeight, 200);
                      target.style.height = newHeight + "px";
                    }}
                  />
                  <div className="absolute right-4 bottom-4 flex items-center gap-2">
                    <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-slate-500">
                      ↵ Send
                    </span>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
