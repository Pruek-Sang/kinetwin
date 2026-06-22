import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy: the React app calls /analyze-one -> forwarded to the FastAPI
// backend on :8000, so the browser code uses same-origin URLs in dev and prod.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/analyze": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
