# UI design review

The review prioritized a clear investigation workflow, readable evidence, visible navigation, and predictable interaction states.

## Changes

- Replaced the animated decorative background with a violet-and-cyan workspace with animated aurora lighting, higher-contrast text, gradient glass surfaces, focus rings, and responsive spacing.
- Added persistent desktop navigation and compact mobile navigation with active-route indicators, an actionable quick-search control, and a skip link.
- Redesigned the overview hero and officer sign-in, using an explicitly labeled animated network diagram with traveling transaction particles, rotating orbital rings, and a breathing evidence core.
- Added example filters to wallet tracing; case search, status filters, counts, creation feedback, loading placeholders, and retry states to the case workspace.
- Improved wallet headers, address copying, partial-result warnings, retry behavior, graph sizing, and keyboard access to evidence highlighting.
- Improved case-detail forms, loading/error states, and asynchronous confirmation handling. Shared buttons now forward native props and refs for dialog integration.
- Removed build-time Google Fonts requests; typography uses local system font stacks so offline builds remain possible.

## Motion and color refresh

- Cyan primary actions, violet information accents, gradient headlines and buttons, and coordinated graph/brand colors.
- Animated background auroras, page entrances, button light sweeps, and glowing card hover states.
- OS reduced-motion preferences disable decorative particles and background movement; number animations also respect the preference.

## Validation

- `npm run typecheck`: passed.
- `npm run build`: passed, including route generation and type validation. The environment emitted non-blocking webpack cache snapshot warnings; the project already disables build-time linting.
- Browser animation checks: orbit rotation and transaction-particle movement confirmed; reduced-motion fallback confirmed.
- Chromium: overview, trace, cases, case detail, wallet detail, and login checked at 1440px, 390px, and 320px. No horizontal page overflow.
- Browser interactions: example filters, case search/status filters, empty-search recovery, case creation, quick-search click and keyboard shortcut, initial dialog focus, and confirmation cancellation passed. No JavaScript page errors.
- Browser investigation data used isolated API fixtures. These checks validate frontend behavior, not live-chain provider availability or backend integration.

Local review screenshots and the repeatable Python Playwright smoke script are in `.ui-review/` at the repository root, excluded from Git. Run the script against a production preview on port 3017. It uses the installed local Chromium executable.

## User reference match

Recomposed the overview to follow the supplied image: compact five-link desktop header, two-column hero, oversized cyan-to-violet headline, sample wallet chips, three feature cues, branching animated transaction preview, five horizontal capability cards, and connected workflow cards. Added a decorative constellation background and dotted globe. The three graph tabs support clicks and arrow-key navigation; illustrative values are labeled separately from actual investigation results. Analytics and Docs navigate to existing overview sections. Browser checks cover the new tabs and widths 320, 390, 768, 1024, 1280, and 1320px.
