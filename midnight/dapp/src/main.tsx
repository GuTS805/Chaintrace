// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import "./globals.js";
import "./styles.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setNetworkId } from "@midnight-ntwrk/midnight-js-network-id";
import { config } from "./config.js";
import { App } from "./App.js";

setNetworkId(config.networkId as Parameters<typeof setNetworkId>[0]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
