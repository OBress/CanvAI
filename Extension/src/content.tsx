import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { AnimatePresence, motion } from "framer-motion";
import ChatWindow from "./components/ChatWindow";
import Settings from "./components/Settings";
import { storage, storageDefaults, WindowState } from "./utils/storage";

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

const getInitialWindowState = (): WindowState => {
  const defaults = storageDefaults.window;
  if (typeof window === "undefined") {
    return defaults;
  }

  const padding = 24;
  const width = defaults.size.width;
  const height = defaults.size.height;
  const x = Math.max(window.innerWidth - width - padding, padding);
  const y = clamp(
    120,
    padding,
    Math.max(window.innerHeight - height - padding, padding)
  );

  return {
    ...defaults,
    position: { x, y },
    isOpen: false,
    isMinimized: false,
    size: { ...defaults.size }
  };
};

const FloatingChatApp: React.FC = () => {
  const [windowState, setWindowState] = useState<WindowState>(() =>
    getInitialWindowState()
  );
  const [hydrated, setHydrated] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const dragContext = useRef<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);

  const resizeContext = useRef<{
    startX: number;
    startY: number;
    originWidth: number;
    originHeight: number;
  } | null>(null);

  const stateRef = useRef(windowState);
  useEffect(() => {
    stateRef.current = windowState;
  }, [windowState]);

  useEffect(() => {
    void storage.ensureInitialized().then(async () => {
      const saved = await storage.get("windowState");
      if (saved) {
        setWindowState((prev) => ({
          ...prev,
          ...saved,
          position: {
            x: clamp(
              saved.position?.x ?? prev.position.x,
              16,
              Math.max(
                (typeof window !== "undefined" ? window.innerWidth : 1024) -
                  (saved.size?.width ?? prev.size.width) -
                  16,
                16
              )
            ),
            y: clamp(
              saved.position?.y ?? prev.position.y,
              16,
              Math.max(
                (typeof window !== "undefined" ? window.innerHeight : 768) -
                  (saved.size?.height ?? prev.size.height) -
                  16,
                16
              )
            )
          },
          size: {
            width: clamp(saved.size?.width ?? prev.size.width, 360, 640),
            height: clamp(saved.size?.height ?? prev.size.height, 400, 720)
          }
        }));
      }
      setHydrated(true);
    });
  }, []);

  useEffect(() => {
    return storage.subscribe((changes) => {
      if (changes.windowState) {
        setWindowState((prev) => ({
          ...prev,
          ...changes.windowState
        }));
      }
    });
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    void storage.set("windowState", windowState);
  }, [windowState, hydrated]);

  const openWindow = useCallback(() => {
    setWindowState((prev) => ({
      ...prev,
      isOpen: true,
      isMinimized: false
    }));
  }, []);

  const closeWindow = useCallback(() => {
    setWindowState((prev) => ({
      ...prev,
      isOpen: false,
      isMinimized: false
    }));
  }, []);

  const minimizeWindow = useCallback(() => {
    setWindowState((prev) => ({
      ...prev,
      isMinimized: true
    }));
  }, []);

  const restoreWindow = useCallback(() => {
    setWindowState((prev) => ({
      ...prev,
      isMinimized: false,
      isOpen: true
    }));
  }, []);

  const handleDragMove = useCallback((event: PointerEvent) => {
    if (!dragContext.current) return;
    event.preventDefault();

    const deltaX = event.clientX - dragContext.current.startX;
    const deltaY = event.clientY - dragContext.current.startY;

    const size = stateRef.current.size;

    const viewportWidth =
      typeof window !== "undefined" ? window.innerWidth : size.width + 32;
    const viewportHeight =
      typeof window !== "undefined" ? window.innerHeight : size.height + 32;

    const maxX = Math.max(viewportWidth - size.width - 16, 16);
    const maxY = Math.max(viewportHeight - size.height - 16, 16);

    const nextX = clamp(dragContext.current.originX + deltaX, 16, maxX);
    const nextY = clamp(dragContext.current.originY + deltaY, 16, maxY);

    setWindowState((prev) => ({
      ...prev,
      position: { x: nextX, y: nextY }
    }));
  }, []);

  const handleDragEnd = useCallback(() => {
    dragContext.current = null;
    window.removeEventListener("pointermove", handleDragMove);
    window.removeEventListener("pointerup", handleDragEnd);
  }, [handleDragMove]);

  const handleDragStart = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!windowState.isOpen || windowState.isMinimized) return;
      event.preventDefault();
      event.stopPropagation();

      dragContext.current = {
        startX: event.clientX,
        startY: event.clientY,
        originX: windowState.position.x,
        originY: windowState.position.y
      };

      window.addEventListener("pointermove", handleDragMove);
      window.addEventListener("pointerup", handleDragEnd);
    },
    [handleDragEnd, handleDragMove, windowState.isMinimized, windowState.isOpen, windowState.position.x, windowState.position.y]
  );

  const handleResizeMove = useCallback((event: PointerEvent) => {
    if (!resizeContext.current) return;
    event.preventDefault();

    const deltaX = event.clientX - resizeContext.current.startX;
    const deltaY = event.clientY - resizeContext.current.startY;

    const nextWidth = clamp(
      resizeContext.current.originWidth + deltaX,
      360,
      Math.min(
        (typeof window !== "undefined" ? window.innerWidth : 1440) -
          stateRef.current.position.x -
          16,
        720
      )
    );
    const nextHeight = clamp(
      resizeContext.current.originHeight + deltaY,
      420,
      Math.min(
        (typeof window !== "undefined" ? window.innerHeight : 900) -
          stateRef.current.position.y -
          16,
        820
      )
    );

    setWindowState((prev) => ({
      ...prev,
      size: { width: nextWidth, height: nextHeight }
    }));
  }, []);

  const handleResizeEnd = useCallback(() => {
    resizeContext.current = null;
    window.removeEventListener("pointermove", handleResizeMove);
    window.removeEventListener("pointerup", handleResizeEnd);
  }, [handleResizeMove]);

  const handleResizeStart = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      resizeContext.current = {
        startX: event.clientX,
        startY: event.clientY,
        originWidth: windowState.size.width,
        originHeight: windowState.size.height
      };

      window.addEventListener("pointermove", handleResizeMove);
      window.addEventListener("pointerup", handleResizeEnd);
    },
    [handleResizeEnd, handleResizeMove, windowState.size.height, windowState.size.width]
  );

  useEffect(() => {
    return () => {
      handleDragEnd();
      handleResizeEnd();
    };
  }, [handleDragEnd, handleResizeEnd]);

  return (
    <>
      <div
        style={{
          position: "fixed",
          top: "1.5rem",
          right: "1.5rem",
          pointerEvents: windowState.isOpen ? "none" : "auto",
          zIndex: 2147483646
        }}
      >
        <AnimatePresence>
          {!windowState.isOpen && (
            <motion.button
              key="canvai-trigger"
              type="button"
              className="canvai-floating-button"
              onClick={openWindow}
              initial={{ opacity: 0, scale: 0.9, y: -12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: -12 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              ai
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {windowState.isOpen && windowState.isMinimized && (
          <motion.div
            key="canvai-minimized"
            onClick={restoreWindow}
            initial={{ opacity: 0, scale: 0.92, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 12 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            style={{
              position: "fixed",
              top: `${windowState.position.y}px`,
              right: `${Math.max(
                16,
                (typeof window !== "undefined"
                  ? window.innerWidth - windowState.position.x - windowState.size.width - 16
                  : 24)
              )}px`,
              pointerEvents: "auto",
              zIndex: 2147483646
            }}
            className="flex cursor-pointer items-center gap-3 rounded-full border border-[rgba(40,39,45,0.55)] bg-[rgba(20,19,26,0.88)] px-5 py-3 text-sm text-slate-100 shadow-[0_18px_38px_rgba(0,0,0,0.45)]"
          >
            <span className="text-xs uppercase tracking-[0.35em] text-[rgba(0,173,181,0.85)]">
              CanvAI
            </span>
            <span className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
              Tap to resume
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {windowState.isOpen && !windowState.isMinimized && (
          <motion.div
            key="canvai-window"
            initial={{ opacity: 0, scale: 0.94, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 16 }}
            transition={{ duration: 0.28, ease: "easeOut" }}
            style={{
              position: "fixed",
              top: `${windowState.position.y}px`,
              left: `${windowState.position.x}px`,
              width: `${windowState.size.width}px`,
              height: `${windowState.size.height}px`,
              pointerEvents: "auto",
              zIndex: 2147483647
            }}
            className="canvai-window"
          >
            <ChatWindow
              onDragHandleDown={handleDragStart}
              onResizeHandleDown={handleResizeStart}
              onMinimize={minimizeWindow}
              onOpenSettings={() => setSettingsOpen(true)}
              onClose={closeWindow}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <Settings open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
};

const mount = () => {
  const existing = document.getElementById("canvai-extension-root");
  if (existing) {
    return;
  }

  const container = document.createElement("div");
  container.id = "canvai-extension-root";
  container.className = "canvai-root";
  document.body.appendChild(container);

  const root = createRoot(container);
  root.render(<FloatingChatApp />);
};

mount();
