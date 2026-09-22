import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  safelist: [
    { pattern: /(bg|text|border|ring)-(primary|good|warn|bad|muted|info|neutral)/ },
  ],
  theme: {
    extend: {
      colors: {
        // ── Surfaces ── (near-black workstation body)
        surface: "#14162d",
        "surface-lavender": "#202342",
        "surface-blush": "#251d3e",

        // ── Brand & accent — cyan and violet intelligence palette ──
        primary: "#67E8F9",
        "primary-hover": "#A5F3FC",
        "primary-soft": "#153344",
        "accent-pink": "#C4B5FD",

        // ── Text ──
        heading: "#F4F3FF",
        body: "#C3C5DE",
        muted: "#A0A6C5",
        mono: "#A5D8FF",

        // ── Semantic fills ──
        "good-fill": "#12301F",
        "good-text": "#3ED18E",
        "warn-fill": "#332108",
        "warn-text": "#F2A93B",
        "neutral-fill": "#252844",
        "neutral-text": "#a7b4c6",
        "info-fill": "#2B2250",
        "info-text": "#C4B5FD",
        "bad-fill": "#341313",
        "bad-text": "#F16B5C",

        // ── Borders ──
        "soft-border": "rgba(175, 183, 255, 0.16)",

        // ── Legacy compat aliases (keeps old references compiling) ──
        good: "#3ED18E",
        warn: "#F2A93B",
        bad: "#F16B5C",
      },
      fontFamily: {
        display: ["Segoe UI", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Segoe UI", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          "Cascadia Code",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 4px 20px -8px rgba(0, 0, 0, 0.3)",
        "card-hover": "0 12px 28px -12px rgba(0, 0, 0, 0.45)",
        button: "0 12px 24px -8px rgba(103, 232, 249, 0.25)",
        nav: "0 8px 32px -8px rgba(0, 0, 0, 0.5)",
      },
      borderRadius: {
        card: "22px",
        hero: "24px",
        input: "10px",
        btn: "10px",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(103,232,249,0.35)" },
          "70%": { boxShadow: "0 0 0 6px rgba(103,232,249,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(103,232,249,0)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-ring": "pulse-ring 1.4s ease-out infinite",
        "fade-up": "fade-up 0.5s ease-out forwards",
      },
    },
  },
  plugins: [],
};

export default config;
