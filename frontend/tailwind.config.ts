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
        // "Forensic light" system — a near-black instrument body with a violet
        // trace-light accent (evidence made visible under blue-violet light,
        // the way forensic ALS reveals what's otherwise invisible) and a warm
        // gold for confirmed/revealed attribution.
        bg: "#0a0b10",
        panel: "#14161f",
        panel2: "#1c1f2c",
        panel3: "#242838",
        border: "#272a3b",
        borderStrong: "#3a3e56",
        text: "#e7e7f0",
        muted: "#8688a3",
        dim: "#585b74",
        accent: "#8b7cff",
        gold: "#e8a33d",
        good: "#35d399",
        warn: "#f2a93c",
        bad: "#ff5c72",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          '"IBM Plex Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3)",
        glow: "0 0 0 1px rgba(139,124,255,0.4), 0 0 16px rgba(139,124,255,0.25)",
        "glow-bad": "0 0 0 1px rgba(255,92,114,0.5), 0 0 16px rgba(255,92,114,0.3)",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(139,124,255,0.5)" },
          "70%": { boxShadow: "0 0 0 8px rgba(139,124,255,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(139,124,255,0)" },
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
