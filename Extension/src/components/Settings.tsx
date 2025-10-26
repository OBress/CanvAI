import React, { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ApiKeys, storage } from "../utils/storage";
import { backendApi, buildBackendUrl } from "../utils/api";

const EyeIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
);

type ApiField = keyof ApiKeys;

interface SettingsProps {
  open: boolean;
  onClose: () => void;
}

interface ToastState {
  message: string;
  tone: "success" | "error";
}

const apiFields: Array<{
  name: ApiField;
  label: string;
  validateEndpoint?: string;
}> = [
  {
    name: "openrouter_api_key",
    label: "OpenRouter API Key",
    validateEndpoint: "/api/validate/openrouter",
  },
  {
    name: "canvas_key",
    label: "Canvas API Key",
    validateEndpoint: "/api/validate/canvas",
  },
  {
    name: "gemini_key",
    label: "Gemini API Key",
  },
  {
    name: "canvas_base_url",
    label: "Canvas Base URL",
  },
  {
    name: "elevenlabs_api_key",
    label: "ElevenLabs API Key",
  },
];

const apiFieldLabels = Object.fromEntries(
  apiFields.map(({ name, label }) => [name, label])
) as Record<ApiField, string>;

const Settings: React.FC<SettingsProps> = ({ open, onClose }) => {
  const [apiKeys, setApiKeys] = useState<ApiKeys>({
    canvas_key: "",
    gemini_key: "",
    canvas_base_url: "",
    elevenlabs_api_key: "",
    openrouter_api_key: "",
  });
  const [visibleFields, setVisibleFields] = useState<Record<ApiField, boolean>>(
    {
      canvas_key: false,
      gemini_key: false,
      canvas_base_url: false,
      elevenlabs_api_key: false,
      openrouter_api_key: false,
    }
  );
  const [toast, setToast] = useState<ToastState | null>(null);
  const [loadingField, setLoadingField] = useState<ApiField | null>(null);

  useEffect(() => {
    if (!open) return;
    let active = true;

    const hydrate = async () => {
      try {
        const values = await storage.getMany(["apiKeys"]);
        if (!active) return;
        setApiKeys((prev) => ({
          ...prev,
          ...values.apiKeys,
        }));

        const remoteKeys = await backendApi.fetchUserKeys();
        if (!active) return;
        setApiKeys(remoteKeys);
        await storage.set("apiKeys", remoteKeys);
      } catch (error) {
        console.error("[CanvAI] Unable to hydrate settings", error);
      }
    };

    void hydrate();

    return () => {
      active = false;
    };
  }, [open]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => {
      setToast(null);
    }, 3200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  const readyToSubmit = useMemo(() => {
    return Object.values(apiKeys).some((value) => value.trim().length > 0);
  }, [apiKeys]);

  const handleApiKeyChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setApiKeys((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const toggleVisibility = (field: ApiField) => {
    setVisibleFields((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const handleSave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const updates = await Promise.all(
        (Object.entries(apiKeys) as Array<[ApiField, string]>).map(
          async ([field, value]) => {
            const saved = await backendApi.updateUserKey(field, value);
            return {
              field,
              value: saved ?? value,
              ok: saved !== null,
            };
          }
        )
      );

      const nextKeys: ApiKeys = { ...apiKeys };
      const failedFields: ApiField[] = [];

      updates.forEach(({ field, value, ok }) => {
        nextKeys[field] = value;
        if (!ok) {
          failedFields.push(field);
        }
      });

      setApiKeys(nextKeys);
      await storage.set("apiKeys", nextKeys);

      if (failedFields.length > 0) {
        const labelList = failedFields
          .map((field) => apiFieldLabels[field] ?? field)
          .join(", ");
        setToast({
          message: `Saved with issues for: ${labelList}.`,
          tone: "error",
        });
      } else {
        setToast({
          message: "Settings synced securely.",
          tone: "success",
        });
      }
    } catch (error) {
      console.error("[CanvAI] Unable to save settings", error);
      setToast({
        message: "Unable to save right now. Try again later.",
        tone: "error",
      });
    }
  };

  const handleValidateKey = async (field: ApiField, endpoint?: string) => {
    if (!endpoint) {
      setToast({
        message: "Validation not available for this key yet.",
        tone: "error",
      });
      return;
    }

    const value = apiKeys[field];
    if (!value) {
      setToast({
        message: "Please enter a key before validating.",
        tone: "error",
      });
      return;
    }

    setLoadingField(field);
    try {
      const response = await fetch(buildBackendUrl(endpoint), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ apiKey: value }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const result = await response.json();
      const ok =
        typeof result.valid === "boolean"
          ? result.valid
          : response.status === 200;

      setToast({
        message: ok
          ? "API key validated successfully."
          : "Validation failed. Check your key.",
        tone: ok ? "success" : "error",
      });
    } catch (error) {
      console.error(error);
      setToast({
        message: "Unable to validate right now. Try again later.",
        tone: "error",
      });
    } finally {
      setLoadingField(null);
    }
  };

  if (typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          key="settings-overlay"
          className="canvai-overlay"
          style={{ zIndex: 2147483648 }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 32, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.94 }}
            transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
            className="relative flex h-auto w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[rgba(13,12,17,0.98)] via-[rgba(22,21,27,0.98)] to-[rgba(16,15,21,0.97)] text-slate-200 shadow-[0_40px_80px_rgba(0,0,0,0.5)] backdrop-blur-2xl"
            style={{
              maxHeight: "85vh",
              backgroundColor: "rgba(16, 15, 21, 0.97)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {toast && (
              <motion.div
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -20, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className={`absolute left-1/2 top-6 z-10 w-[85%] max-w-xl -translate-x-1/2 rounded-2xl border backdrop-blur-xl px-6 py-3.5 text-center text-sm font-semibold shadow-xl ${
                  toast.tone === "success"
                    ? "border-cyan-400/40 bg-gradient-to-r from-cyan-500/20 to-cyan-400/15 text-cyan-100 shadow-[0_8px_32px_rgba(0,173,181,0.25)]"
                    : "border-red-400/40 bg-gradient-to-r from-red-500/20 to-red-400/15 text-red-100 shadow-[0_8px_32px_rgba(239,68,68,0.25)]"
                }`}
              >
                {toast.message}
              </motion.div>
            )}

            <div className="flex flex-col gap-6 px-6 sm:px-10 pb-6 pt-10 sm:pt-12 border-b border-white/10 bg-gradient-to-b from-white/5 to-transparent">
              <div className="flex flex-wrap items-start justify-between gap-6">
                <div>
                  <p className="text-[15px] font-mono uppercase tracking-[0.4em] text-cyan-300/60 mb-3">
                    API Integrations
                  </p>
                  <h2 className="text-3xl font-bold text-slate-50 tracking-tight">
                    Configure your AI assistant connections
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm px-5 py-2.5 text-xs font-mono uppercase tracking-[0.3em] text-slate-300 shadow-sm transition-all duration-300 hover:border-red-400/40 hover:bg-red-400/10 hover:text-red-300 hover:scale-105 active:scale-95"
                >
                  Close
                </button>
              </div>
            </div>

            <form
              onSubmit={handleSave}
              className="flex flex-1 flex-col overflow-hidden px-6 pb-4 sm:px-10"
            >
              <div className="canvai-scrollbar flex-1 overflow-y-auto overflow-x-hidden pr-6">
                <div className="flex flex-col gap-8 max-w-full">
                  <section className="max-w-full">
                    <h3 className="text-sm font-bold uppercase tracking-[0.35em] text-slate-300 mb-1">
                      API Bridges
                    </h3>
                    <p className="text-xs text-slate-400 mb-4">
                      Keys sync to your backend vault and stay cached locally.
                      Add them once and validate to unlock full assistance.
                    </p>
                    <div className="mt-4 flex flex-col gap-6 max-w-full">
                      {apiFields.map(({ name, label, validateEndpoint }) => {
                        const visible = visibleFields[name];
                        const loading = loadingField === name;
                        return (
                          <div
                            key={name}
                            className="flex flex-col gap-3 max-w-full"
                          >
                            <label className="flex flex-col gap-2.5 max-w-full">
                              <span className="text-[10px] font-mono uppercase tracking-[0.35em] text-slate-400">
                                {label}
                              </span>
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center max-w-full">
                                <input
                                  type={visible ? "text" : "password"}
                                  name={name}
                                  value={apiKeys[name]}
                                  onChange={handleApiKeyChange}
                                  className="flex-1 rounded-2xl border-2 border-white/20 bg-[rgba(40,39,45,0.97)] backdrop-blur-2xl px-5 py-3.5 text-sm text-[#EEEEEE] shadow-[0_8px_32px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.08)_inset,0_0_40px_rgba(0,173,181,0.08)] placeholder:text-slate-600 transition-all duration-300 focus:border-[#00ADB5] focus:bg-[rgba(40,39,45,0.99)] focus:outline-none focus:shadow-[0_12px_48px_rgba(0,173,181,0.4),0_0_0_1px_rgba(0,173,181,0.3)_inset,0_0_60px_rgba(0,173,181,0.2)] hover:border-white/30 hover:shadow-[0_10px_40px_rgba(0,0,0,0.7),0_0_0_1px_rgba(255,255,255,0.12)_inset] overflow-hidden text-ellipsis"
                                  placeholder={`Paste your ${label}`}
                                  style={{
                                    colorScheme: "dark",
                                    WebkitTextFillColor: "#EEEEEE",
                                  }}
                                />
                                <div className="flex items-center gap-2 shrink-0">
                                  <button
                                    type="button"
                                    onClick={() => toggleVisibility(name)}
                                    className="w-11 h-11 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm text-slate-300 shadow-sm transition-all duration-300 hover:border-white/20 hover:bg-white/10 hover:scale-105 active:scale-95 flex items-center justify-center"
                                    aria-label={
                                      visible ? "Hide API key" : "Show API key"
                                    }
                                  >
                                    {visible ? (
                                      <EyeOffIcon className="w-4 h-4" />
                                    ) : (
                                      <EyeIcon className="w-4 h-4" />
                                    )}
                                  </button>
                                  <button
                                    type="button"
                                    disabled={loading || !validateEndpoint}
                                    onClick={() =>
                                      handleValidateKey(name, validateEndpoint)
                                    }
                                    className="h-11 flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/5 backdrop-blur-sm px-5 text-[10px] font-mono uppercase tracking-[0.35em] text-slate-400 shadow-sm transition-all duration-300 hover:border-white/25 hover:bg-white/10 hover:text-slate-300 hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 active:scale-95"
                                  >
                                    {loading ? (
                                      <span className="animate-spin text-sm">
                                        ...
                                      </span>
                                    ) : (
                                      <span>Validate</span>
                                    )}
                                  </button>
                                </div>
                              </div>
                            </label>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                </div>
              </div>

              <div className="mt-3 flex flex-col border-t border-white/10 bg-gradient-to-t from-black/10 to-transparent pt-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs font-mono text-slate-400">
                    Your data stays encrypted within chrome.storage.local.
                  </span>
                  <button
                    type="submit"
                    disabled={!readyToSubmit}
                    className="rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-400 border border-cyan-300/20 px-6 py-2 text-[11px] font-bold uppercase tracking-[0.35em] text-slate-900 shadow-[0_4px_20px_rgba(0,173,181,0.3)] transition-all duration-300 hover:shadow-[0_6px_28px_rgba(0,173,181,0.4)] hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
                  >
                    Save Settings
                  </button>
                </div>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
};

export default Settings;
