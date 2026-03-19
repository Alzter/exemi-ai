import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: {
    // Firefox content scripts don't provide Node globals.
    "process.env.NODE_ENV": JSON.stringify("production"),
    "process.env": "{}",
    process: JSON.stringify({ env: { NODE_ENV: "production" } }),
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    lib: {
      entry: "src/content.tsx",
      name: "ExemiContentScript",
      formats: ["iife"],
      fileName: () => "content.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});

