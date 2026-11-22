import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, renameSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const vite = join(root, "node_modules", "vite", "bin", "vite.js");
if (!existsSync(vite)) { console.error("Dependências em falta. Execute npm install primeiro."); process.exit(1); }
const command = spawnSync(process.execPath, [vite, "build", "--config", "vite.gateway.config.ts"], {
  cwd: root, stdio: "inherit",
  env: { ...process.env, VITE_API_BASE_URL: "", VITE_DEMO_MODE: "false", VITE_LOCAL_ASSETS: "true", VITE_GATEWAY_BUILD: "true" },
});
if (command.status !== 0) process.exit(command.status || 1);
const out = join(root, "dist-gateway");
const html = join(out, "gateway-index.html");
if (!existsSync(html)) throw new Error("Build não gerou gateway-index.html.");
renameSync(html, join(out, "index.html"));
const body = readFileSync(join(out, "index.html"), "utf8");
if (!body.includes("/static/assets/") || !existsSync(join(out, "images", "nandbank-lion-logo.png"))) {
  throw new Error("Build inválido: JavaScript/CSS ou logótipo não encontrados em dist-gateway.");
}
console.log("OK: frontend estático para /app/ui, recursos em /static/.");
