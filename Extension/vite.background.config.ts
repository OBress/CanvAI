import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: false,
    sourcemap: false,
    rollupOptions: {
      input: {
        background: resolve(__dirname, "src/background.ts")
      },
      output: {
        format: "iife",
        inlineDynamicImports: true,
        entryFileNames: "scripts/background.js"
      }
    }
  }
});
