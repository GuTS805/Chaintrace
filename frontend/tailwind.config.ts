import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  safelist: [
    { pattern: /(bg|text|border|ring)-(accent|gold|good|warn|bad|muted)/ },
  ],
  theme: {
    extend: {
      colors: {
        // "Forensic dark minimalism" — a near-black workstation body, indigo
        // as the single system-intelligence accent, and semantic color
        // reserved strictly for evidentiary meaning (confirmed / suspicious /
        // high-risk), not decoration.
        bg: "#0b0d12",
        panel: "#11141b",
        panel2: "#171b23",
        panel3: "#1d222c",
        border: "#252b36",
        borderStrong: "#323a48",
        text: "#e5e7eb",
        muted: "#94a3b8",
        dim: "#5b6472",
        accent: "#6366f1",
        gold: "#3b82f6",
        good: "#22c55e",
        warn: "#f59e0b",
        bad: "#ef4444",
      },
      fontFamily: {
        display: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          '"JetBrains Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3)",
        glow: "0 0 0 1px rgba(99,102,241,0.4), 0 0 16px rgba(99,102,241,0.2)",
        "glow-bad": "0 0 0 1px rgba(239,68,68,0.5), 0 0 16px rgba(239,68,68,0.3)",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(99,102,241,0.5)" },
          "70%": { boxShadow: "0 0 0 8px rgba(99,102,241,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(99,102,241,0)" },
        },
      },
      animation: {
        "pulse-ring": "pulse-ring 1.4s ease-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
