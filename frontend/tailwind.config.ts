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
        // ── Surfaces ──
        surface: "#FFFFFF",
        "surface-lavender": "#F4F1FE",
        "surface-blush": "#FDF1F6",

        // ── Brand & accent ──
        primary: "#6C5DD3",
        "primary-hover": "#5A4BC4",
        "primary-soft": "#E9E5FB",
        "accent-pink": "#F0A6CA",

        // ── Text ──
        heading: "#2B2B43",
        body: "#5F5F7E",
        muted: "#9B9BB4",
        mono: "#7C6FD9",

        // ── Semantic fills ──
        "good-fill": "#DFF5E9",
        "good-text": "#1E8A5E",
        "warn-fill": "#FDEEDC",
        "warn-text": "#C97B1D",
        "neutral-fill": "#EEEEF4",
        "neutral-text": "#6B7280",
        "info-fill": "#E9E5FB",
        "info-text": "#6C5DD3",
        "bad-fill": "#FEE2E2",
        "bad-text": "#EF4444",

        // ── Borders ──
        "soft-border": "#E7E4F5",

        // ── Legacy compat aliases (keeps old references compiling) ──
        good: "#1E8A5E",
        warn: "#C97B1D",
        bad: "#EF4444",
      },
      fontFamily: {
        display: ["var(--font-poppins)", "Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["var(--font-dm-sans)", "DM Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          "var(--font-jetbrains-mono)",
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 20px 40px -12px rgba(108, 93, 211, 0.12)",
        "card-hover": "0 28px 56px -12px rgba(108, 93, 211, 0.20)",
        button: "0 12px 24px -8px rgba(108, 93, 211, 0.45)",
        nav: "0 8px 32px -8px rgba(43, 43, 67, 0.08)",
      },
      borderRadius: {
        card: "20px",
        hero: "24px",
        input: "14px",
        btn: "12px",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(108,93,211,0.35)" },
          "70%": { boxShadow: "0 0 0 6px rgba(108,93,211,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(108,93,211,0)" },
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
