import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  safelist: [
    { pattern: /(bg|text|border)-(accent|good|warn|bad|vasp|muted)/ },
  ],
  theme: {
    extend: {
      colors: {
        // Light "daylight forensic" palette — all foreground tones pass WCAG AA
        // on white.
        bg: "#f6f7f9",
        panel: "#ffffff",
        panel2: "#eef1f5",
        border: "#d8dee7",
        text: "#0f1720",
        muted: "#5b6673",
        accent: "#4f46e5",
        good: "#0f8a4d",
        warn: "#b45309",
        bad: "#d11f2f",
        vasp: "#6d28d9",
      },
      boxShadow: {
        panel: "0 1px 2px rgba(16,23,32,0.06), 0 1px 3px rgba(16,23,32,0.04)",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          '"IBM Plex Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      letterSpacing: {
        widest2: "0.22em",
      },
    },
  },
  plugins: [],
};

export default config;
