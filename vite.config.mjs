import { defineConfig } from "vite";
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const workspaceRoot=fileURLToPath(new URL('.',import.meta.url));
// Frozen previews may themselves live inside .local. Ignore only their own
// generated directories, never an ancestor containing the entire workspace.
export function ignoredWorkspacePath(file,root=workspaceRoot){
 const relative=path.relative(root,file);
 if(relative==='..'||relative.startsWith('..'+path.sep))return false;
 return relative.split(path.sep).some(part=>['.local','.venv','.memory-venv','examples'].includes(part));
}
export default defineConfig({
  cacheDir: process.env.ATMEM_ARCHITECT_VITE_CACHE_DIR || "node_modules/.vite",
  server: {
    host: "127.0.0.1",
    port: Number((process.env.ATMEM_ARCHITECT_PORT || process.env.ATFORMA_PORT) || 5174),
    strictPort: true,
    watch: { ignored: file=>ignoredWorkspacePath(file) },
    proxy: { "/api": { target: `http://127.0.0.1:${(process.env.ATMEM_ARCHITECT_SIDECAR_PORT || process.env.ATFORMA_SIDECAR_PORT) || 8766}`, changeOrigin: false } },
  },
  preview: { host: "127.0.0.1", port: 4174, strictPort: true },
});
