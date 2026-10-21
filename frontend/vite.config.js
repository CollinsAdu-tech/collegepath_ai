import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api calls to the FastAPI backend during local development so the
// frontend can call relative paths without hard-coding localhost:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
