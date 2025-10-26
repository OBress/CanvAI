/* eslint-disable @typescript-eslint/no-explicit-any */
declare const chrome: any;

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface Profile {
  first_name: string;
  last_name: string;
  school: string;
  major: string;
  gpa: string;
  credits_taken: string;
}

export interface ApiKeys {
  canvas_key: string;
  gemini_key: string;
  canvas_base_url: string;
  elevenlabs_api_key: string;
  openrouter_api_key: string;
}

export interface WindowState {
  isOpen: boolean;
  isMinimized: boolean;
  position: { x: number; y: number };
  size: { width: number; height: number };
}

export interface StorageShape {
  profile: Profile;
  apiKeys: ApiKeys;
  chats: Record<string, ChatSession>;
  lastSessionId: string | null;
  windowState: WindowState;
}

const defaultProfile: Profile = {
  first_name: "",
  last_name: "",
  school: "",
  major: "",
  gpa: "",
  credits_taken: "",
};

const defaultApiKeys: ApiKeys = {
  canvas_key: "",
  gemini_key: "",
  canvas_base_url: "",
  elevenlabs_api_key: "",
  openrouter_api_key: "",
};

const defaultSession: ChatSession = {
  id: "default",
  title: "New Conversation",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  messages: [],
};

const defaultWindowState: WindowState = {
  isOpen: false,
  isMinimized: false,
  position: { x: 0, y: 96 },
  size: { width: 420, height: 540 },
};

const defaultStorage: StorageShape = {
  profile: defaultProfile,
  apiKeys: defaultApiKeys,
  chats: { [defaultSession.id]: defaultSession },
  lastSessionId: defaultSession.id,
  windowState: defaultWindowState,
};

type StorageKey = keyof StorageShape;

const memoryStore = new Map<StorageKey, StorageShape[StorageKey]>();
const hasChromeStorage =
  typeof chrome !== "undefined" &&
  chrome?.storage?.local &&
  typeof chrome.storage.local.get === "function";

const ensureDefault = async (): Promise<void> => {
  const existing = await storage.getMany([
    "profile",
    "apiKeys",
    "chats",
    "lastSessionId",
    "windowState",
  ]);

  const updates: Partial<StorageShape> = {};
  (Object.keys(defaultStorage) as StorageKey[]).forEach((key) => {
    if (!existing[key]) {
      updates[key] = defaultStorage[key];
    }
  });

  if (Object.keys(updates).length > 0) {
    await storage.setMany(updates);
  }
};

type StorageChangeCallback = (changes: Partial<StorageShape>) => void;

export const storage = {
  async get<T extends StorageKey>(key: T): Promise<StorageShape[T]> {
    if (hasChromeStorage) {
      const result = await chrome.storage.local.get([key]);
      return (result[key] ?? defaultStorage[key]) as StorageShape[T];
    }

    if (memoryStore.has(key)) {
      return memoryStore.get(key) as StorageShape[T];
    }

    const serialized = window.localStorage.getItem(`canvai-${key}`);
    if (serialized) {
      const parsed = JSON.parse(serialized) as StorageShape[T];
      memoryStore.set(key, parsed);
      return parsed;
    }

    memoryStore.set(key, defaultStorage[key]);
    return defaultStorage[key];
  },

  async getMany<T extends StorageKey>(
    keys: T[]
  ): Promise<Pick<StorageShape, T>> {
    if (hasChromeStorage) {
      const result = (await chrome.storage.local.get(keys)) as Pick<
        StorageShape,
        T
      >;
      const response = {} as Pick<StorageShape, T>;
      keys.forEach((key) => {
        response[key] = result[key] ?? defaultStorage[key];
      });
      return response;
    }

    const response = {} as Pick<StorageShape, T>;
    for (const key of keys) {
      response[key] = await this.get(key);
    }
    return response;
  },

  async set<T extends StorageKey>(
    key: T,
    value: StorageShape[T]
  ): Promise<void> {
    if (hasChromeStorage) {
      await chrome.storage.local.set({ [key]: value });
    } else {
      memoryStore.set(key, value);
      window.localStorage.setItem(`canvai-${key}`, JSON.stringify(value));
    }
  },

  async setMany(values: Partial<StorageShape>): Promise<void> {
    if (hasChromeStorage) {
      await chrome.storage.local.set(values);
      return;
    }

    Object.entries(values).forEach(([key, value]) => {
      const storageKey = key as StorageKey;
      memoryStore.set(storageKey, value as StorageShape[StorageKey]);
      window.localStorage.setItem(
        `canvai-${storageKey}`,
        JSON.stringify(value)
      );
    });
  },

  async update<T extends StorageKey>(
    key: T,
    updater: (previous: StorageShape[T]) => StorageShape[T]
  ): Promise<StorageShape[T]> {
    const previous = await this.get(key);
    const next = updater(previous);
    await this.set(key, next);
    return next;
  },

  async getAll(): Promise<StorageShape> {
    const values = await this.getMany([
      "profile",
      "apiKeys",
      "chats",
      "lastSessionId",
      "windowState",
    ]);
    return values as StorageShape;
  },

  async ensureInitialized(): Promise<void> {
    await ensureDefault();
  },

  subscribe(callback: StorageChangeCallback): () => void {
    if (hasChromeStorage) {
      const listener = (
        changes: Record<string, { oldValue?: unknown; newValue?: unknown }>,
        areaName: string
      ) => {
        if (areaName !== "local") return;
        const updates: Partial<StorageShape> = {};
        (Object.keys(changes) as StorageKey[]).forEach((key) => {
          const change = changes[key];
          if (!change) return;
          updates[key] = (change.newValue ?? undefined) as
            | StorageShape[StorageKey]
            | undefined;
        });
        callback(updates);
      };
      chrome.storage.onChanged.addListener(listener);
      return () => chrome.storage.onChanged.removeListener(listener);
    }

    return () => undefined;
  },
};

export const storageDefaults = {
  profile: defaultProfile,
  apiKeys: defaultApiKeys,
  session: defaultSession,
  window: defaultWindowState,
};
