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
        surface: "#122334",
        "surface-lavender": "#1b3043",
        "surface-blush": "#322836",

        // ── Brand & accent — cyan and violet intelligence palette ──
        primary: "#5EE3CF",
        "primary-hover": "#9AF1E2",
        "primary-soft": "#153C3E",
        "accent-pink": "#F2A9A0",

        // ── Text ──
        heading: "#F7F5F0",
        body: "#CBD6DB",
        muted: "#A8BBC4",
        mono: "#A6E7E1",

        // ── Semantic fills ──
        "good-fill": "#183B32",
        "good-text": "#72E2AD",
        "warn-fill": "#44351E",
        "warn-text": "#F5C16C",
        "neutral-fill": "#263744",
        "neutral-text": "#BDCCD2",
        "info-fill": "#302F50",
        "info-text": "#CFC1FF",
        "bad-fill": "#452C34",
        "bad-text": "#FF9C9A",

        // ── Borders ──
        "soft-border": "rgba(166, 205, 207, 0.18)",

        // ── Legacy compat aliases (keeps old references compiling) ──
        good: "#72E2AD",
        warn: "#F5C16C",
        bad: "#FF9C9A",
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
