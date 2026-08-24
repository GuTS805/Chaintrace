1. Design Philosophy
Style: Soft UI / Modern Semi-Flat. Light, airy, low-contrast pastel interface with floating layered cards.
Depth model: Depth comes from large, diffused, low-opacity drop shadows — never from borders or dark dividers. Every card appears to "float" above a soft gradient background.
Mood: Calm, professional, approachable — a forensic tool that feels like a friendly SaaS dashboard, not a terminal.
No dark mode. The current dark theme is fully replaced by the light pastel system below.
2. Color System
Background
Token	Value	Usage
bg-gradient	linear-gradient 135°, #EDEBFB → #F7F3FA → #FDF4F9	Full-page background (soft lavender → white → blush)
surface-primary	#FFFFFF	All cards, panels, navbar
surface-tint-lavender	#F4F1FE	Alternating card tint, input fields
surface-tint-blush	#FDF1F6	Alternating card tint
Brand & Accent
Token	Value	Usage
primary	#6C5DD3 (soft indigo-violet)	Primary buttons, active nav, logo accent, links
primary-hover	#5A4BC4	Button hover
primary-soft	#E9E5FB	Badge fills, icon chips, focus rings
accent-pink	#F0A6CA	Decorative gradient blobs, tertiary highlights
Semantic (badge/status) colors — pastel fills with deep text
State	Fill	Text	Used on
Success / clean	#DFF5E9	#1E8A5E	CLEAN ATTRIBUTION (BINANCE), REAL: KRAKEN DEPOSIT, REAL: BINANCE DEPOSIT
Warning	#FDEEDC	#C97B1D	PEEL CHAIN → KRAKEN
Neutral	#EEEEF4	#6B7280	INSUFFICIENT EVIDENCE
Info / violet	#E9E5FB	#6C5DD3	AMBIGUOUS SPLIT, REAL: MULTI-CHAIN
Text
Token	Value	Usage
text-heading	#2B2B43	Headings, page titles
text-body	#5F5F7E	Paragraphs, descriptions
text-muted	#9B9BB4	Helper text, placeholders, labels
text-mono	#7C6FD9	Wallet addresses, code snippets
3. Typography
Google Fonts combo:

Headings: Poppins — weights 500, 600, 700
Body / UI: DM Sans — weights 400, 500, 700
Monospace (wallet addresses, trace>, code): JetBrains Mono — weights 400, 500
Font size scale — Golden Ratio (φ = 1.618, base 16px)
Step	Size	Line height	Usage
Display	42px	1.15	Hero headline "Trace any wallet to the exchange behind it."
H1	26px	1.25	Page title "Cases"
H2	20px	1.3	Card titles ("Ransomware → exchange", "Peel chain"), sidebar stat labels' companion numbers use 26px
Body	16px	1.6	Descriptions, paragraphs
Small	12px	1.5	Helper text, badges, footer
Micro / Eyebrow	10px	1.4	Section labels ("INVESTIGATION WORKSPACE", "CASE FILES · OFFLINE SEEDED"), letter-spacing 0.12em, uppercase, weight 600
Stat numbers (3, 6, 0 in sidebar): Poppins 700, 42px, color primary.
Wallet addresses: JetBrains Mono 400, 12px, color text-mono, no truncation change — keep existing shortened format (e.g., 0xb8d31a8c…2c36edc3).
Hero headline: "exchange behind it" portion colored primary; rest text-heading.
4. Spacing System (8pt grid)
Base unit: 8px. Scale: 4 / 8 / 16 / 24 / 32 / 48 / 64 / 96.

Token	Value	Usage
space-xs	4px	Badge internal gaps, icon–label gaps
space-sm	8px	Between label and input, badge padding vertical
space-md	16px	Inside-card element spacing, grid gutters (mobile)
space-lg	24px	Card internal padding, grid gutters (desktop)
space-xl	32px	Card padding for hero/major panels, section internal top
space-2xl	48px	Between navbar and page content
space-3xl	64px	Between major sections (hero → case files)
Page container: max-width 1200px, centered, horizontal padding 32px (16px on mobile).
Card padding: 24px standard cards; 32px hero and "Open a case" panel.
Card grid gap: 24px.
5. Shape & Elevation
Corner radius
Element	Radius
Main app container / hero panel	24px
Cards, sidebar stat tiles	20px
Inputs, search bar	14px
Buttons	12px
Badges / pills	999px (full pill)
Shadows (the signature Soft UI element — large, diffused, tinted, low opacity)
Token	Value	Usage
shadow-card	0 20px 40px -12px rgba(108, 93, 211, 0.12)	All cards at rest
shadow-card-hover	0 28px 56px -12px rgba(108, 93, 211, 0.20) + translateY(-4px)	Card hover
shadow-button	0 12px 24px -8px rgba(108, 93, 211, 0.45)	Primary buttons
shadow-nav	0 8px 32px -8px rgba(43, 43, 67, 0.08)	Sticky navbar
No visible borders on cards. Inputs may use a 1px border #E7E4F5 that switches to a 2px primary-soft ring + primary border on focus.
Background decoration: 2–3 very large blurred gradient blobs (primary-soft and accent-pink at 30–40% opacity, blur ≥ 120px) positioned behind the content in corners.
6. Components
6.1 Navbar (both pages — identical)
White pill/rounded bar, shadow-nav, radius 20px, floats 16px from top with side margins (not edge-to-edge), sticky.
Height 64px, horizontal padding 24px.
Left: logo icon (small gradient chip, 32×32, radius 10px, containing the arrow glyph) + wordmark CHAIN (Poppins 700, text-heading) TRACE (Poppins 700, primary).
Center-left links: TRACE · CASES — DM Sans 500, 12px, uppercase, letter-spacing 0.08em. Active link: pill background primary-soft, text primary, padding 8px 16px. Inactive: text-muted.
Search: rounded input (radius 999px), background surface-tint-lavender, placeholder "Search anywhere", trailing ⌘K chip (white, radius 8px, subtle shadow), width 240px, height 40px.
Right: green status dot (8px, #34C77B) + Demo Investigating Officer (DM Sans 600, 12px) + I4C-DEMO-01 (JetBrains Mono, 11px, text-muted) + Logout ghost button (radius 12px, 1px border #E7E4F5, hover fill surface-tint-lavender).
6.2 Trace page — Hero panel (left, ~66% width)
White card, radius 24px, padding 32px, shadow-card.
Eyebrow: FORENSIC WALLET ATTRIBUTION (micro style, primary).
H-display: "Trace any wallet to the exchange behind it." — "exchange behind it" in primary.
Body (16px, text-body): "Attribution from on-chain heuristics and a calibrated classifier — every score traces to concrete evidence, and the system will say "insufficient evidence" rather than guess."
Trace input row: pill container (radius 14px, background surface-tint-lavender, height 56px, padding-left 16px). Prefix trace> in JetBrains Mono primary. Placeholder: 0x… or T… wallet address. Right-embedded Run button: primary fill, white text, radius 12px, padding 12px 24px, shadow-button.
Helper (12px, text-muted): "Paste any real wallet (Ethereum, Polygon, or Tron) and fetch it live from chain. or press ⌘K to jump anywhere" — "any real wallet" as primary link; ⌘K as a small keycap chip.
6.3 Stats sidebar (right, ~34% width)
Three stacked white tiles, radius 20px, padding 24px, gap 16px, shadow-card.
Each: big number (Poppins 700 42px primary) left, label (DM Sans 400 14px text-body) beside/below.
Content, in order: 3 chains traced live · 6 evidence signal types · 0 LLMs in the attribution path.
Optional: a 40×40 pastel icon chip (radius 12px, primary-soft) per tile.
6.4 Case files grid
Section header: CASE FILES · OFFLINE SEEDED (micro eyebrow, text-muted) with a thin #E7E4F5 rule to the right; margin-top 64px, margin-bottom 24px.
Grid: row 1 = 3 columns (CASE-01–03), row 2 = 3 columns (CASE-04–06), row 3 = full-width (CASE-07). Gap 24px.
Card anatomy (white, radius 20px, padding 24px, shadow-card, hover lift):
Top row: case ID (CASE-01) — JetBrains Mono 10px uppercase text-muted — with the status pill badge right-aligned (10px, weight 600, uppercase, padding 4px 12px, semantic pastel fill per §2).
Title (Poppins 600, 20px, text-heading), margin-top 16px.
Wallet address (JetBrains Mono 12px, text-mono), margin-top 8px, optionally inside a tiny pill of surface-tint-lavender (padding 4px 10px, radius 8px).
Exact card content (unchanged):
CASE-01 · Ransomware → exchange · 0xb8d31a8c…2c36edc3 · CLEAN ATTRIBUTION (BINANCE) — success
CASE-02 · Peel chain · 0x3d2a2561…77f95b3f · PEEL CHAIN → KRAKEN — warning
CASE-03 · No VASP linkage · 0x1226019c…b4766772 · INSUFFICIENT EVIDENCE — neutral
CASE-04 · Two exchanges · 0xed569095…9ef07a17 · AMBIGUOUS SPLIT — info
CASE-05 · Real wallet — Kraken · 0x216b7523…568ad09b · REAL: KRAKEN DEPOSIT — success
CASE-06 · Real wallet — Binance · 0x5b271663…6999081c · REAL: BINANCE DEPOSIT — success
CASE-07 · Real wallet — Tron (USDT) · TVYuaXdhEH…xE5oZ9yQ · REAL: MULTI-CHAIN — info (full-width card)
Footer line (12px, text-muted, margin-top 32px): "Start the API (uvicorn app.main:app) and seed data (make seed-demo) first. Manage investigations under cases." — inline code in JetBrains Mono inside surface-tint-lavender chips; "cases" as primary link.
6.5 Cases page
Eyebrow: INVESTIGATION WORKSPACE (micro, primary), then Cases (H1 26px Poppins 700), then description (16px text-body): "Group wallets, evidence, and notes under a case for reporting and disclosure." Section top margin 48px from navbar.
OPEN A CASE panel: white card, radius 24px, padding 32px, shadow-card. Label OPEN A CASE (micro eyebrow). Form row (flex, gap 16px):
Text input, flexible width, placeholder Case name, e.g. "Ransomware payout — Q1" — height 52px, radius 14px, background surface-tint-lavender, focus ring per §5.
Text input, fixed 220px, placeholder Investigator (optional) — same style.
Open case button — primary fill, white text, radius 12px, padding 14px 28px, shadow-button, hover primary-hover + slight lift.
Section header OPEN CASES (0) (micro eyebrow + thin rule), margin-top 48px.
Empty state card: white, radius 20px, padding 32px, shadow-card, centered flat 2D pastel illustration (folder/magnifier in primary-soft + accent-pink tones, ~120px) above the text (14px, text-body): "No cases yet. Open one above, then pin wallets to it from any investigation to start building a disclosure-ready record."
7. Illustration & Iconography
Icons: rounded-corner line icons, 1.5px stroke (Lucide/Phosphor style), colored primary or text-muted, often sitting in 40×40 pastel chips (radius 12px).
Illustrations: flat 2D vector only, matching the palette (soft purples, pinks, white) — no gradient-mesh 3D, no photos. Use them only in the empty state and optionally as a small spot illustration in the hero.
8. Motion
Card hover: translateY(-4px) + shadow-card-hover, 200ms ease-out.
Button hover: darken + translateY(-2px); active: translateY(0).
Page elements fade-up 12px stagger on load (60ms increments).
9. Responsive
≥1200px: layouts as specified. 768–1199px: case grid → 2 columns; hero + stats stack (stats become a 3-across row). <768px: everything single column; navbar collapses links behind a menu; container padding 16px.