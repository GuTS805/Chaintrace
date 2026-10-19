// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Based on the Vite setup of midnightntwrk/example-bboard (Apache-2.0).
import { cpSync, createReadStream, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { type Plugin, defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import wasm from "vite-plugin-wasm";

const here = path.dirname(fileURLToPath(import.meta.url));
const managed = path.resolve(here, "../managed/private_case");

/** Serves the compiled prover/verifier keys and ZKIR at /keys and /zkir, and copies them into the build. */
function zkArtifacts(): Plugin {
  return {
    name: "chaintrace-zk-artifacts",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = (req.url ?? "").split("?")[0];
        const match = /^\/(keys|zkir)\/([\w.-]+)$/.exec(url);
        if (!match) return next();
        const file = path.join(managed, match[1], match[2]);
        if (!existsSync(file)) return next();
        res.setHeader("Content-Type", "application/octet-stream");
        createReadStream(file).pipe(res);
      });
    },
    closeBundle() {
      const out = path.resolve(here, "dist");
      for (const dir of ["keys", "zkir"]) cpSync(path.join(managed, dir), path.join(out, dir), { recursive: true });
    },
  };
}

export default defineConfig({
  root: here,
  envDir: here,
  cacheDir: path.resolve(here, ".vite"),
  build: {
    outDir: path.resolve(here, "dist"),
    emptyOutDir: true,
    target: "esnext",
    // isomorphic-ws has no named WebSocket export in browsers; we pass globalThis.WebSocket explicitly.
    rolldownOptions: { checks: { importIsUndefined: false } },
    commonjsOptions: { transformMixedEsModules: true, extensions: [".js", ".cjs"], ignoreDynamicRequires: true },
  },
  plugins: [react(), wasm(), zkArtifacts()],
  optimizeDeps: {
    include: ["@midnight-ntwrk/compact-runtime"],
    exclude: [
      "@midnight-ntwrk/onchain-runtime-v3",
      "@midnight-ntwrk/onchain-runtime-v3/midnight_onchain_runtime_wasm_bg.wasm",
      "@midnight-ntwrk/onchain-runtime-v3/midnight_onchain_runtime_wasm.js",
      "@midnight-ntwrk/ledger-v8",
    ],
  },
  resolve: {
    extensions: [".mjs", ".js", ".ts", ".jsx", ".tsx", ".json", ".wasm"],
    mainFields: ["browser", "module", "main"],
  },
  server: { port: 5173, strictPort: true },
});
