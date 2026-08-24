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
        // "Premium forensic intelligence" — an almost-black surface stack,
        // indigo used sparingly for active/selected/emphasis states only,
        // and semantic color reserved strictly for evidentiary meaning
        // (confirmed / suspicious / high-risk), never decoration.
        bg: "#050505",
        panel: "#0a0a0a",
        panel2: "#111111",
        panel3: "#161616",
        border: "rgba(255,255,255,0.08)",
        borderStrong: "rgba(255,255,255,0.16)",
        text: "#f5f5f5",
        muted: "#a1a1aa",
        dim: "#71717a",
        accent: "#6366f1",
        gold: "#7c3aed",
        good: "#22c55e",
        warn: "#f59e0b",
        bad: "#ef4444",
      },
      fontFamily: {
        display: ["var(--font-geist-sans)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["var(--font-geist-sans)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          "var(--font-geist-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(0,0,0,0.5)",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(99,102,241,0.35)" },
          "70%": { boxShadow: "0 0 0 6px rgba(99,102,241,0)" },
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
