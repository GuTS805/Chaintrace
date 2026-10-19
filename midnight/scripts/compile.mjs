// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Compiles the Compact contract with compiler 0.31.1. Uses a native `compact`
// toolchain when available (Linux/macOS); otherwise builds and runs the pinned
// Docker image in toolchain/Dockerfile (Windows has no native compiler, and its
// built-in compact.exe is an unrelated NTFS tool).

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const COMPILER = "0.31.1";
const IMAGE = `chaintrace-compact:${COMPILER}`;
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = ["compile", `+${COMPILER}`, "contracts/private_case.compact", "managed/private_case"];

function run(cmd, cmdArgs, opts = {}) {
  console.log(`$ ${cmd} ${cmdArgs.join(" ")}`);
  const res = spawnSync(cmd, cmdArgs, { cwd: root, stdio: "inherit", ...opts });
  if (res.error) return false;
  return res.status === 0;
}

function hasNativeCompact() {
  if (process.platform === "win32") return false;
  const res = spawnSync("compact", ["compile", `+${COMPILER}`, "--version"], { encoding: "utf8" });
  return res.status === 0 && res.stdout.trim() === COMPILER;
}

if (hasNativeCompact()) {
  process.exit(run("compact", args) ? 0 : 1);
}

const env = { ...process.env, MSYS_NO_PATHCONV: "1" };
const haveImage = spawnSync("docker", ["image", "inspect", IMAGE], { stdio: "ignore" }).status === 0;
if (!haveImage && !run("docker", ["build", "-t", IMAGE, "toolchain"], { env })) {
  console.error("Could not build the Compact Docker image. Is Docker running?");
  process.exit(1);
}
const ok = run("docker", ["run", "--rm", "-v", `${root}:/work`, IMAGE, ...args.filter((a) => !a.startsWith("+"))], {
  env,
});
process.exit(ok ? 0 : 1);
