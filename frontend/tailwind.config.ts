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
        bg: "#0a0e14",
        panel: "#0f1620",
        panel2: "#131c28",
        border: "#1c2530",
        text: "#c9d1d9",
        muted: "#6b7684",
        accent: "#39bae6",
        good: "#7fd962",
        warn: "#f0a35e",
        bad: "#f07178",
        vasp: "#b18cff",
      },
      fontFamily: {
        mono: [
          "var(--font-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
