// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Cross-platform `KEY=VALUE command args...` for npm scripts (cmd.exe has no inline env syntax).
import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);
const env = { ...process.env };
while (args.length && /^[A-Z_][A-Z0-9_]*=/.test(args[0])) {
  const [key, ...rest] = args.shift().split("=");
  env[key] = rest.join("=");
}
const res = spawnSync(args[0], args.slice(1), { stdio: "inherit", env, shell: process.platform === "win32" });
process.exit(res.status ?? 1);
