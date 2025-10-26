/* eslint-disable @typescript-eslint/no-explicit-any */
declare const chrome: any;

import { storage } from "./utils/storage";

chrome.runtime.onInstalled.addListener(() => {
  void storage.ensureInitialized();
});

chrome.runtime.onMessage.addListener(
  (
    message: { type?: string },
    _sender: unknown,
    sendResponse: (response?: unknown) => void
  ) => {
    if (message?.type === "canvai:get-storage") {
      void storage.getAll().then((data) => sendResponse({ data }));
      return true;
    }
    return false;
  }
);
