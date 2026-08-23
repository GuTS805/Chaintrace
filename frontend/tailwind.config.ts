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
        bg: "#0b0d12",
        panel: "#12151d",
        panel2: "#191e2a",
        border: "#242c3a",
        text: "#d7dce5",
        muted: "#798494",
        accent: "#f2b750",
        good: "#57d38f",
        warn: "#e8975a",
        bad: "#ff6b7d",
        vasp: "#a68bff",
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
