import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import { viteStaticCopy } from "vite-plugin-static-copy";
import { resolve } from "node:path";

export default defineConfig({
  envDir: resolve(__dirname, ".."),
  envPrefix: ["VITE_", "CLOUDFLARE_"],
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        { src: "manifest.json", dest: "." },
        { src: "build/temp/content.css", dest: "assets" }
      ]
    })
  ],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      input: {
        content: resolve(__dirname, "src/content.tsx")
      },
      output: {
        format: "iife",
        inlineDynamicImports: true,
        entryFileNames: "scripts/content.js"
      }
    }
  }
});
