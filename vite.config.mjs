import { defineConfig } from "vite";
export default defineConfig({
  cacheDir: process.env.ATMEM_ARCHITECT_VITE_CACHE_DIR || "node_modules/.vite",
  server: {
    host: "127.0.0.1",
    port: Number((process.env.ATMEM_ARCHITECT_PORT || process.env.ATFORMA_PORT) || 5174),
    strictPort: true,
    watch: { ignored: ["**/.local/**", "**/.venv/**", "**/.memory-venv/**", "**/examples/**"] },
    proxy: { "/api": { target: `http://127.0.0.1:${(process.env.ATMEM_ARCHITECT_SIDECAR_PORT || process.env.ATFORMA_SIDECAR_PORT) || 8766}`, changeOrigin: false } },
  },
  preview: { host: "127.0.0.1", port: 4174, strictPort: true },
});
