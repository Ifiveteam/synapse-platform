import path from "node:path";
import { fileURLToPath } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@synapse/shared": path.resolve(__dirname, "../shared"),
    },
  },
  server: {
    // 웹 프론트 5173 — extension dev server는 5174
    port: 5173,
    strictPort: true,
  },
});
