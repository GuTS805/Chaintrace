---
name: Luminous Forensic
colors:
  surface: '#fcf8ff'
  surface-dim: '#ddd8e3'
  surface-bright: '#fcf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f2fc'
  surface-container: '#f1ecf7'
  surface-container-high: '#ebe6f1'
  surface-container-highest: '#e5e1eb'
  on-surface: '#1c1b22'
  on-surface-variant: '#474553'
  inverse-surface: '#312f37'
  inverse-on-surface: '#f4eff9'
  outline: '#787584'
  outline-variant: '#c9c4d5'
  surface-tint: '#5b4cc1'
  primary: '#5343b9'
  on-primary: '#ffffff'
  primary-container: '#6c5dd3'
  on-primary-container: '#f5f0ff'
  inverse-primary: '#c7bfff'
  secondary: '#874b6b'
  on-secondary: '#ffffff'
  secondary-container: '#ffb3d8'
  on-secondary-container: '#7c4160'
  tertiary: '#7c4b00'
  on-tertiary: '#ffffff'
  tertiary-container: '#9e6100'
  on-tertiary-container: '#fff1e5'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5deff'
  primary-fixed-dim: '#c7bfff'
  on-primary-fixed: '#180065'
  on-primary-fixed-variant: '#4331a8'
  secondary-fixed: '#ffd8e8'
  secondary-fixed-dim: '#fcb0d5'
  on-secondary-fixed: '#380726'
  on-secondary-fixed-variant: '#6c3452'
  tertiary-fixed: '#ffddba'
  tertiary-fixed-dim: '#ffb866'
  on-tertiary-fixed: '#2b1700'
  on-tertiary-fixed-variant: '#673d00'
  background: '#fcf8ff'
  on-background: '#1c1b22'
  surface-variant: '#e5e1eb'
  bg-gradient-start: '#EDEBFB'
  bg-gradient-mid: '#F7F3FA'
  bg-gradient-end: '#FDF4F9'
  surface-tint-lavender: '#F4F1FE'
  surface-tint-blush: '#FDF1F6'
  text-heading: '#2B2B43'
  text-body: '#5F5F7E'
  text-muted: '#9B9BB4'
  text-mono: '#7C6FD9'
  status-success-bg: '#DFF5E9'
  status-success-text: '#1E8A5E'
  status-warning-bg: '#FDEEDC'
  status-warning-text: '#C97B1D'
  status-info-bg: '#E9E5FB'
  status-info-text: '#6C5DD3'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: DM Sans
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 28px
  body-md:
    fontFamily: DM Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: DM Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 24px
  margin: 32px
---

# Design Philosophy
Style: Soft UI / Modern Semi-Flat. Light, airy, low-contrast pastel interface with floating layered cards.
Depth model: Depth comes from large, diffused, low-opacity drop shadows — never from borders or dark dividers. Every card appears to "float" above a soft gradient background.
Mood: Calm, professional, approachable — a forensic tool that feels like a friendly SaaS dashboard, not a terminal.
No dark mode.

# Color System
Background:
- bg-gradient: linear-gradient(135deg, #EDEBFB 0%, #F7F3FA 50%, #FDF4F9 100%)
- surface-primary: #FFFFFF (All cards, panels, navbars)
- surface-tint-lavender: #F4F1FE (Alternating card tint, input fields)
- surface-tint-blush: #FDF1F6 (Alternating card tint)

Brand & Accent:
- primary: #6C5DD3 (soft indigo-violet)
- primary-hover: #5A4BC4
- primary-soft: #E9E5FB
- accent-pink: #F0A6CA

Semantic Status:
- success: Fill #DFF5E9, Text #1E8A5E
- warning: Fill #FDEEDC, Text #C97B1D
- neutral: Fill #EEEEF4, Text #6B7280
- info: Fill #E9E5FB, Text #6C5DD3

Text:
- text-heading: #2B2B43
- text-body: #5F5F7E
- text-muted: #9B9BB4
- text-mono: #7C6FD9 (Wallet addresses)

# Typography
- Headings: Poppins (500, 600, 700)
- Body / UI: DM Sans (400, 500, 700)
- Monospace: JetBrains Mono (400, 500)

# Spacing & Shape
- Base unit: 8px
- Corner radius: 24px (Main panels), 20px (Cards), 14px (Inputs), 12px (Buttons)
- Shadows: 
  - shadow-card: 0 20px 40px -12px rgba(108, 93, 211, 0.12)
  - shadow-nav: 0 8px 32px -8px rgba(43, 43, 67, 0.08)
  - shadow-button: 0 12px 24px -8px rgba(108, 93, 211, 0.45)
