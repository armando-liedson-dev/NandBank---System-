/** Compilação exclusiva para FastAPI /app/ui; não mexe no build original Lovable. */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  base: "/static/",
  publicDir: fileURLToPath(new URL("./public", import.meta.url)),
  build: {
    outDir: "dist-gateway",
    emptyOutDir: true,
    rollupOptions: { input: fileURLToPath(new URL("./gateway-index.html", import.meta.url)) },
    sourcemap: false,
  },
});
