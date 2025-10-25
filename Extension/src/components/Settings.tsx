import React, { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ApiKeys, Profile, storage } from "../utils/storage";

type ApiField = keyof ApiKeys;

interface SettingsProps {
  open: boolean;
  onClose: () => void;
}

interface ToastState {
  message: string;
  tone: "success" | "error";
}

const profileFields: Array<{
  name: keyof Profile;
  label: string;
}> = [
  { name: "first_name", label: "First Name" },
  { name: "last_name", label: "Last Name" },
  { name: "school", label: "School" },
  { name: "major", label: "Major" },
  { name: "gpa", label: "GPA" },
  { name: "credits_taken", label: "Credits Taken" }
];

const apiFields: Array<{
  name: ApiField;
  label: string;
  endpoint: string;
}> = [
  {
    name: "openrouter_api_key",
    label: "OpenRouter API Key",
    endpoint: "/api/validate/openrouter"
  },
  {
    name: "canvas_api_key",
    label: "Canvas API Key",
    endpoint: "/api/validate/canvas"
  }
];

const Settings: React.FC<SettingsProps> = ({ open, onClose }) => {
  const [profile, setProfile] = useState<Profile>({
    first_name: "",
    last_name: "",
    school: "",
    major: "",
    gpa: "",
    credits_taken: ""
  });
  const [apiKeys, setApiKeys] = useState<ApiKeys>({
    openrouter_api_key: "",
    canvas_api_key: ""
  });
  const [visibleFields, setVisibleFields] = useState<Record<ApiField, boolean>>({
    openrouter_api_key: false,
    canvas_api_key: false
  });
  const [toast, setToast] = useState<ToastState | null>(null);
  const [loadingField, setLoadingField] = useState<ApiField | null>(null);

  useEffect(() => {
    if (!open) return;
    void storage.getMany(["profile", "apiKeys"]).then((values) => {
      setProfile(values.profile);
      setApiKeys(values.apiKeys);
    });
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
    return (
      Object.values(profile).some((value) => value.trim().length > 0) ||
      Object.values(apiKeys).some((value) => value.trim().length > 0)
    );
  }, [profile, apiKeys]);

  const handleProfileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { name, value } = event.target;
    setProfile((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleApiKeyChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { name, value } = event.target;
    setApiKeys((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const toggleVisibility = (field: ApiField) => {
    setVisibleFields((prev) => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  const handleSave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await storage.setMany({ profile, apiKeys });
    setToast({
      message: "Settings saved securely.",
      tone: "success"
    });
  };

  const handleValidateKey = async (field: ApiField, endpoint: string) => {
    const value = apiKeys[field];
    if (!value) {
      setToast({
        message: "Please enter a key before validating.",
        tone: "error"
      });
      return;
    }

    setLoadingField(field);
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ apiKey: value })
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const result = await response.json();
      const ok =
        typeof result.valid === "boolean" ? result.valid : response.status === 200;

      setToast({
        message: ok
          ? "API key validated successfully."
          : "Validation failed. Check your key.",
        tone: ok ? "success" : "error"
      });
    } catch (error) {
      console.error(error);
      setToast({
        message: "Unable to validate right now. Try again later.",
        tone: "error"
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
        >
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ duration: 0.28, ease: "easeOut" }}
            className="relative flex h-auto w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-[rgba(40,39,45,0.65)] bg-[rgba(18,18,24,0.98)] text-slate-200 shadow-[0_35px_65px_rgba(13,12,17,0.65)]"
            style={{ maxHeight: "80vh" }}
          >
            {toast && (
              <motion.div
                initial={{ opacity: 0, y: -16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                className={`absolute left-1/2 top-6 z-10 w-[80%] max-w-xl -translate-x-1/2 rounded-full border px-5 py-3 text-center text-sm font-medium ${
                  toast.tone === "success"
                    ? "border-[rgba(0,173,181,0.45)] bg-[rgba(0,173,181,0.15)] text-[rgba(193,254,255,0.95)]"
                    : "border-[rgba(239,68,68,0.55)] bg-[rgba(239,68,68,0.18)] text-[rgba(254,226,226,0.95)]"
                }`}
              >
                {toast.message}
              </motion.div>
            )}

            <div className="flex flex-col gap-6 px-10 pb-6 pt-8 sm:pt-10">
              <div className="flex flex-wrap items-start justify-between gap-6 pr-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
                    Identity & Integrations
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-50">
                    Canvas profile that powers your AI assistant
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-full border border-[rgba(40,39,45,0.7)] px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-400 transition hover:border-[rgba(239,68,68,0.55)] hover:text-[rgba(239,68,68,0.8)]"
                >
                  Close
                </button>
              </div>
            </div>

            <form
              onSubmit={handleSave}
              className="flex flex-1 flex-col overflow-hidden px-10 pb-10"
            >
              <div className="canvai-scrollbar flex-1 overflow-y-auto pr-2">
                <div className="flex flex-col gap-8">
                  <section>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
                      Profile
                    </h3>
                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      {profileFields.map(({ name, label }) => (
                        <label
                          key={name}
                          className="group flex flex-col gap-2 rounded-3xl border border-[rgba(40,39,45,0.45)] bg-[rgba(24,23,30,0.85)] px-5 py-4 transition focus-within:border-[rgba(0,173,181,0.45)] focus-within:bg-[rgba(24,23,30,0.95)]"
                        >
                          <span className="text-[11px] uppercase tracking-[0.35em] text-slate-500">
                            {label}
                          </span>
                          <input
                            type="text"
                            name={name}
                            value={profile[name]}
                            onChange={handleProfileChange}
                            className="bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
                            placeholder={`Enter ${label.toLowerCase()}`}
                          />
                        </label>
                      ))}
                    </div>
                  </section>

                  <section>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
                      API Bridges
                    </h3>
                    <p className="mt-2 text-xs text-slate-500">
                      Keys stay in your browser via chrome.storage.local. Add
                      them once and validate to unlock full assistance.
                    </p>
                    <div className="mt-4 flex flex-col gap-4">
                      {apiFields.map(({ name, label, endpoint }) => {
                        const visible = visibleFields[name];
                        const loading = loadingField === name;
                        return (
                          <div
                            key={name}
                            className="flex flex-col gap-3 rounded-3xl border border-[rgba(40,39,45,0.45)] bg-[rgba(24,23,30,0.85)] px-5 py-5 transition focus-within:border-[rgba(0,173,181,0.45)]"
                          >
                            <label className="flex flex-col gap-2">
                              <span className="text-[11px] uppercase tracking-[0.35em] text-slate-500">
                                {label}
                              </span>
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                                <input
                                  type={visible ? "text" : "password"}
                                  name={name}
                                  value={apiKeys[name]}
                                  onChange={handleApiKeyChange}
                                  className="flex-1 rounded-full border border-[rgba(40,39,45,0.6)] bg-[rgba(20,19,26,0.9)] px-5 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-[rgba(0,173,181,0.45)] focus:ring-2 focus:ring-[rgba(0,173,181,0.35)]"
                                  placeholder={`Paste your ${label}`}
                                />
                                <div className="flex items-center gap-2">
                                  <button
                                    type="button"
                                    onClick={() => toggleVisibility(name)}
                                    className="rounded-full border border-[rgba(40,39,45,0.6)] px-3 py-2 text-[11px] uppercase tracking-[0.3em] text-slate-400 transition hover:border-[rgba(0,173,181,0.45)] hover:text-[rgba(0,173,181,0.9)]"
                                  >
                                    {visible ? "Hide" : "See"}
                                  </button>
                                  <button
                                    type="button"
                                    disabled={loading}
                                    onClick={() => handleValidateKey(name, endpoint)}
                                    className="flex items-center gap-2 rounded-full border border-[rgba(0,173,181,0.45)] px-4 py-2 text-[11px] uppercase tracking-[0.4em] text-[rgba(0,173,181,0.95)] transition hover:bg-[rgba(0,173,181,0.15)] disabled:opacity-60"
                                  >
                                    {loading ? (
                                      <span className="animate-spin text-sm">...</span>
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

              <div className="mt-6 flex flex-col gap-3 border-t border-[rgba(40,39,45,0.45)] pt-6 text-xs text-slate-500">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span>
                    Your data stays encrypted within chrome.storage.local.
                  </span>
                  <button
                    type="submit"
                    disabled={!readyToSubmit}
                    className="rounded-full bg-[rgba(0,173,181,0.9)] px-6 py-3 text-[11px] font-semibold uppercase tracking-[0.4em] text-slate-900 transition hover:bg-[rgba(0,173,181,1)] disabled:opacity-60"
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
