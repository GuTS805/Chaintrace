// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts", "test/**/*.test.tsx"],
    environment: "node",
    // The E2E suite shares one local chain; run its cases in order.
    fileParallelism: false,
    sequence: { concurrent: false },
  },
});
