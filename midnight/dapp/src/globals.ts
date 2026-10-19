// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Browser shims some Midnight.js dependencies expect (as in midnightntwrk/example-bboard).
import { Buffer } from "buffer";

const g = globalThis as unknown as { process?: unknown; Buffer?: unknown };
g.process ??= { env: { NODE_ENV: import.meta.env.MODE } };
g.Buffer ??= Buffer;
