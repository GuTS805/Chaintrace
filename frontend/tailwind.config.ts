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
        surface: "#131313",
        "surface-lavender": "#1C1930",
        "surface-blush": "#1A1712",

        // ── Brand & accent — amber/gold, the single warm accent ──
        primary: "#F2A93B",
        "primary-hover": "#E0972B",
        "primary-soft": "#2E230F",
        "accent-pink": "#E0972B",

        // ── Text ──
        heading: "#F3F1EA",
        body: "#B4AFA4",
        muted: "#847F73",
        mono: "#BBA9F5",

        // ── Semantic fills ──
        "good-fill": "#12301F",
        "good-text": "#3ED18E",
        "warn-fill": "#332108",
        "warn-text": "#F2A93B",
        "neutral-fill": "#1C1C1E",
        "neutral-text": "#9A968D",
        "info-fill": "#1C1930",
        "info-text": "#BBA9F5",
        "bad-fill": "#341313",
        "bad-text": "#F16B5C",

        // ── Borders ──
        "soft-border": "rgba(243, 241, 234, 0.1)",

        // ── Legacy compat aliases (keeps old references compiling) ──
        good: "#3ED18E",
        warn: "#F2A93B",
        bad: "#F16B5C",
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
        card: "0 20px 40px -14px rgba(0, 0, 0, 0.55)",
        "card-hover": "0 28px 56px -14px rgba(0, 0, 0, 0.65)",
        button: "0 12px 24px -8px rgba(242, 169, 59, 0.35)",
        nav: "0 8px 32px -8px rgba(0, 0, 0, 0.5)",
      },
      borderRadius: {
        card: "20px",
        hero: "24px",
        input: "14px",
        btn: "12px",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(242,169,59,0.35)" },
          "70%": { boxShadow: "0 0 0 6px rgba(242,169,59,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(242,169,59,0)" },
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
